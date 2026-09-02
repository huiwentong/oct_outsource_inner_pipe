"""vsftpd 日志解析与 tail。

解析 vsftpd.log（xferlog 摘要行）格式，例如：:

    Tue Jun  1 10:00:05 2026 [pid 1234] [ftpuser] OK UPLOAD: Client "192.168.1.10", "/oct/.../a.ma", 123456 bytes, 123.45Kbyte/sec
    Tue Jun  1 10:00:06 2026 [pid 1234] [ftpuser] OK DELETE: Client "192.168.1.10", "/oct/.../a.ma"
    Tue Jun  1 10:00:07 2026 [pid 1234] [ftpuser] OK RENAME: Client "192.168.1.10", from "/a.ma" to "/b.ma"

对应的 vsftpd 配置开关：``xferlog_enable=YES``、``xferlog_file=<本模块的 VW_FTP_LOG>``。
"""

from __future__ import annotations

import asyncio
import json
import signal
import logging
import traceback
from typing import Optional
import os
import re
from datetime import datetime, timedelta, timezone
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from io import TextIOWrapper, BufferedReader
from logger.core import watch_logger
from versionwatch.config import Settings
from versionwatch.hashing import hash_file
from versionwatch.events import EventSource, EventType, FileEvent, normalize_rel_path

logger = watch_logger

# 可选星期前缀 + 完整时间戳 + pid + 可选用户名 + 状态 + 动词 + Client
SUMMARY_RE = re.compile(
    r"^(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?"
    r"(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<year>\d{4})\s+"
    r"\[pid\s+(?P<pid>\d+)\](?:\s+\[(?P<user>[^\]]+)\])?\s+"
    r"(?P<status>OK|FAL|FAIL|ERROR)\s+(?P<verb>[A-Z_]+):\s+"
    r'Client\s+"(?P<client>[^"]+)"(?P<rest>.*)$'
)

UPLOAD_RE = re.compile(r',\s+"(?P<path>[^"]+)",\s+(?P<size>\d+)\s+bytes')
SIMPLE_PATH_RE = re.compile(r',\s+"(?P<path>[^"]+)"')
RENAME_RE = re.compile(r',\s+"(?P<src>[^"]+)\s+(?P<dst>[^"]+)"')

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# 摘要行中可能出现的动词；只关心会改变文件的
_CHANGE_VERBS = {"UPLOAD", "DELETE", "RENAME", "MKDIR", "RMDIR"}

_MAX_READ_PER_TICK = 4 * 1024 * 1024


def _get_tz(name: str="Asia/Shanghai") -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except Exception:
        logger.warning("未知时区 %s，回退 UTC", name)
        return timezone.utc


def parse_ftp_line(raw: str, root: Path, tz: ZoneInfo | timezone) -> FileEvent | None:
    """解析一行 vsftpd 摘要日志，无法识别或非变更类操作返回 None。"""
    m = SUMMARY_RE.match(raw)
    if not m:
        return None
    if m.group("status") != "OK":
        return None
    verb = m.group("verb")
    if verb not in _CHANGE_VERBS:
        return None
    rest = m.group("rest")

    rel_path: str | None = None
    event_type: EventType | None = None
    size: int | None = None
    move_src: str | None = None

    if verb == "UPLOAD":
        um = UPLOAD_RE.search(rest)
        if not um:
            return None
        rel_path = normalize_rel_path(um.group("path"))
        size = int(um.group("size"))
        # 具体是 created 还是 overwrite 由 recorder 根据历史状态判定
        event_type = EventType.MODIFIED
    elif verb == "DELETE":
        dm = SIMPLE_PATH_RE.search(rest)
        if not dm:
            return None
        rel_path = normalize_rel_path(dm.group("path"))
        event_type = EventType.DELETED
    elif verb == "RENAME":
        rm = RENAME_RE.search(rest)
        if not rm:
            return None
        rel_path = normalize_rel_path(rm.group("dst"))
        move_src = normalize_rel_path(rm.group("src"))
        event_type = EventType.MOVED
    elif verb == "MKDIR":
            mm = SIMPLE_PATH_RE.search(rest)
            if not mm:
                return None
            rel_path = normalize_rel_path(mm.group("path"))
            event_type = EventType.CREATED
    elif verb == "RMDIR":
            rm = SIMPLE_PATH_RE.search(rest)
            if not rm:
                return None
            rel_path = normalize_rel_path(rm.group("path"))
            event_type = EventType.DELETED

    assert rel_path is not None and event_type is not None

    mon = _MONTHS.get(m.group("mon"))
    if mon is None:
        return None

    day = int(m.group("day"))
    hh, mm, ss = (int(x) for x in m.group("time").split(":"))
    year = int(m.group("year"))
    local_dt = datetime(year, mon, day, hh, mm, ss, tzinfo=tz)
    now_local = datetime.now(tz)
    # 防呆：日志时间比当前时间超前超过 24h（通常是跨年/时区问题），回退一年
    if local_dt > now_local + timedelta(hours=24):
        local_dt = local_dt.replace(year=local_dt.year - 1)

    timestamp: float = local_dt.timestamp()
    return FileEvent(
        event_type=event_type,
        rel_path=rel_path,
        size=size,
        client_name=m.group("user"),
        client_ip=m.group("client"),
        checksum=hash_file(f'{root}/{rel_path}'),
        actor='auto',
        session_pid=int(m.group("pid")),
        move_src=move_src,
        observed_at=local_dt.timestamp(),
        mtime=timestamp,
        details={
            "raw": raw.strip(),
            "verb": verb,
            "status": m.group("status"),
        },
    )


class FtpLogTailer:
    def __init__(self, settings: Settings, queue: Optional[asyncio.Queue]=None) -> None:
        self.settings = settings
        self._fh: BufferedReader | None = None  # typing: BinaryIO
        self._inode: int | None = None
        self._offset = 0
        self._queue = queue
        self._state_path = settings.log_state_file
        self._tz = _get_tz()
        self.stop_event = asyncio.Event()
        self._load_state()

    def _load_state(self) -> None:
        try:
            data = json.loads(self.settings.log_state_file.read_text(encoding="utf-8"))
            self._inode = int(data.get("inode") or 0)
            self._offset = int(data.get("offset") or 0)
        except Exception:
            self._inode = None
            self._offset = 0

    def _save_state(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps({"inode": self._inode, "offset": self._offset}), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("保存日志 tail 状态失败: %s", exc)


    def delete_state(self) -> None:
        try:
            self._state_path.unlink()
            logger.info("删除日志 tail 状态成功")
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("删除日志 tail 状态失败: %s", exc)


    def close(self) -> None:
        self._save_state()
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def stop(self) -> None:
        self.stop_event.set()
        self.close()

    async def run(self, emit) -> None:
        while self.stop_event.is_set() is False:
            try:
                await self._tick(emit)
            except FileNotFoundError:
                # 日志文件被轮转删除/尚未创建：复位，等待下个 tick
                logger.warning("FTP 日志文件不存在，等待创建...")
                logger.error(traceback.format_exc())
                if self._fh is not None:
                    self._fh.close()
                    self._fh = None
                self._inode = None
                self._offset = 0
            except Exception:
                logger.exception("FTP 日志 tail 出错")
            await asyncio.sleep(self.settings.log_poll_interval)

    def _open_if_needed(self) -> os.stat_result:
        st = os.stat(self.settings.ftp_log)
        if self._fh is not None and st.st_ino == self._inode:
            return st
        if self._fh is not None:
            self._fh.close()
        prev_inode = self._inode
        self._fh = open(self.settings.ftp_log, "rb")
        self._inode = st.st_ino
        if prev_inode is not None and prev_inode != st.st_ino:
            self._offset = 0  # 轮转：新文件从头读
        # elif self._offset == 0:
        #     # 全新启动：跳过历史日志
        #     self._fh.seek(0, os.SEEK_END)
        else:
            self._fh.seek(self._offset)
        self._offset = self._fh.tell()
        return st

    async def _tick(self, emit) -> None:
        st = self._open_if_needed()
        if not self._fh:
            logger.error("FTP 日志文件句柄不存在，无法读取")
            raise RuntimeError('can not find self._fh!!')
        size = st.st_size
        # logger.info("FTP 日志文件大小: %d, 当前偏移: %d", size, self._offset)
        if self._offset > size:
            # 文件被截断（copytruncate）或轮转后变小：从头读
            self._fh.seek(0)
            self._offset = 0
        to_read = min(size - self._offset, _MAX_READ_PER_TICK)
        if to_read <= 0:
            return
        self._fh.seek(self._offset)
        data = self._fh.read(to_read)
        self._offset = self._fh.tell()
        text = data.decode("utf-8", errors="replace")
        for raw_line in text.splitlines():
            ev = parse_ftp_line(raw_line, self.settings.root_dir, self._tz)
            if ev is not None:
                emit(ev)
        self._save_state()


def test_emit(fe: FileEvent):
    logger.info(f'emit {fe.summary()}')


async def test_run():
    settings = Settings(
        root_dir=Path('/var/lib/docker/volumes/outsource-pip_ftpdata/_data'),
        ftp_log=Path('/var/lib/docker/volumes/outsource-pip_ftplogs/_data/vsftpd.log'),
        database_url='postgres',
        log_state_file=Path(__file__).parent.parent / "ftp_log.state",
    )
    flt = FtpLogTailer(settings=settings)

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _request_stop(signame: str) -> None:
        logger.info("收到 %s, 正在优雅退出...", signame)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop, sig.name)
        except (NotImplementedError, RuntimeError):
            pass
    
    asyncio.create_task(flt.run(test_emit), name="ftp-log-tailer")

    try:
        await stop.wait()
    finally:
        flt.stop()




if __name__ == '__main__':
    asyncio.run(test_run())
    # fe = parse_ftp_line('Mon Aug 24 10:37:03 2026 [pid 239] [hongli] OK UPLOAD: Client "192.168.16.156", "/hongli/public (1).key", 1711 bytes, 1680.98Kbyte/sec',Path('/var/lib/docker/volumes/outsource-pip_ftpdata/_data'),_get_tz())
    # if fe:
    #     logger.info(fe.summary())