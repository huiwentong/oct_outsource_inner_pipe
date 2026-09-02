"""事件流水线：去抖 + 多来源合并 + 派发到 recorder。"""

from __future__ import annotations

import asyncio
import logging
import os
import stat as stat_mod
import time
from dataclasses import dataclass, field
from typing import Any
import json
from versionwatch.config import Settings
from dataclasses import asdict
from versionwatch.recorder import Recorder
from versionwatch.events import EventSource, EventType, FileEvent
from versionwatch.hashing import hash_file
from logger.core import watch_logger
import requests
import httpx


logger = watch_logger


def event_to_dict(ev: FileEvent) -> dict:
    return {
        "event_type": ev.event_type.value,
        "rel_path": ev.rel_path,
        "move_src": ev.move_src,
        "size": ev.size,
        "checksum": ev.checksum,
        "actor": ev.actor,
        "client_ip": ev.client_ip,
        "session_pid": ev.session_pid,
        "client_name": ev.client_name,
        "details": ev.details,
        "mtime": ev.mtime,
        "observed_at": ev.observed_at,
    }

@dataclass
class _PendingGroup:
    """同一路径在合并窗口内的所有来源事件。"""

    key: str
    events: list[FileEvent] = field(default_factory=list)
    last_seen: float = field(default_factory=time.monotonic)

    def add(self, ev: FileEvent) -> None:
        self.events.append(ev)
        self.last_seen = time.monotonic()

    def is_due(self, debounce: float, now: float) -> bool:
        return now - self.last_seen >= debounce


class Pipeline:

    def __init__(self, settings: Settings, queue: asyncio.Queue, recorder: Recorder) -> None:
        self.settings = settings
        self.queue = queue
        self.recorder = recorder
        self._groups: dict[str, _PendingGroup] = {}
        self._stop = asyncio.Event()
        self.client = httpx.AsyncClient(
            base_url="http://vsftpd:8000"
        )
        self.init_from_queue_json()

    def stop(self) -> None:
        
        self._stop.set()

    async def run(self) -> None:
        logger.info("事件流水线 pipline启动")
        while not self._stop.is_set():
            try:
                ev = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                ev = None
            if ev is not None:
                logger.info(
                    "pipeline 捕获到事件 %s，队列剩余 %d",
                    ev.summary(),
                    self.queue.qsize(),
                )
                await self._process_event(ev)

        # 退出前把剩余未处理事件强制保存
        await self.client.aclose()
        await self._flush_all()





    async def _flush_all(self) -> None:
        # 1. 把队列里剩余的事件全部记录一下
        events: list[FileEvent] = []
        while True:
            try:
                ev = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                events.append(ev)
            finally:
                self.queue.task_done()

        if events:
            with open(self.settings.queue_file, "w", encoding="utf-8") as f:
                json.dump(
                    [event_to_dict(ev) for ev in events],
                    f,
                    indent=4,
                    ensure_ascii=False,
                )


    def init_from_queue_json(self):
         if os.path.exists(self.settings.queue_file):
            with open(self.settings.queue_file, 'r') as f:
                 events_raw = json.load(f)
            for e_parm in events_raw:
                e = FileEvent(
                    event_type=EventType(e_parm['event_type']),
                    rel_path=e_parm['rel_path'],
                    move_src=e_parm.get('move_src'),
                    size=e_parm.get('size'),
                    checksum=e_parm.get('checksum'),
                    actor=e_parm.get('actor'),
                    client_ip=e_parm.get('client_ip'),
                    session_pid=e_parm.get('session_pid'),
                    client_name=e_parm.get('client_name'),
                    details=e_parm.get('details', {}),
                    mtime=e_parm.get('mtime'),
                    observed_at=e_parm.get('observed_at'),
                )
                self.queue.put_nowait(e)
            os.unlink(self.settings.queue_file)




    async def _process_event(self, ev: FileEvent) -> None:
        await self.recorder.record(ev)


        if ev.rel_path.startswith("/oct"):

            if ev.event_type == EventType.CREATED and len(ev.rel_path.split('/')) in (5,6):
                query = await self.client.post(
                    "/get_path_group",
                    params={'_path': str(self.settings.root_dir/ev.rel_path)}
                )
                query.raise_for_status()
                groups = query.json()['acl']
                g_list = [g for g in groups if g.startswith('group')]
                if len(g_list) >= 2:
                    return
                    

                group = ev.rel_path.split('/')[-1]
                response = await self.client.post(
                    "/create_group",
                    json={
                        'name': group,
                        'description': 'auto create',
                    }
                )
                response.raise_for_status()
                logger.info(response.json())



                if len(ev.rel_path.split('/')) == 5:
                    response = await self.client.post(
                        "/set_path_group",
                        json={
                            'path': str(self.settings.root_dir/ev.rel_path),
                            'group': group,
                            'rescursive': False,
                            'inherit': False,
                        }
                    )
                    response.raise_for_status()
                    logger.info(response.json())
                elif len(ev.rel_path.split('/')) == 6:
                    response = await self.client.post(
                        "/set_path_group",
                        json={
                            'path': str(self.settings.root_dir/ev.rel_path),
                            'group': group,
                            'rescursive': True,
                            'inherit': True,
                        }
                    )
                    response.raise_for_status()
                    logger.info(response.json())

        else:
            pass





    # def _ingest(self, ev: FileEvent) -> None:
    #     group = self._groups.get(ev.rel_path)
    #     if group is None:
    #         group = _PendingGroup(ev.rel_path)
    #         self._groups[ev.rel_path] = group
    #     group.add(ev)

    # async def _flush_due(self) -> None:
    #     now = time.monotonic()
    #     due = [g for g in self._groups.values() if g.is_due(self.settings.debounce_seconds, now)]
    #     for group in due:
    #         self._groups.pop(group.key, None)
    #         await self._process(group)


    # async def _process(self, group: _PendingGroup) -> None:
    #     try:
    #         for ev in self._merge(group):
    #             await self._finalize(ev)
    #             await self.recorder.record(ev)
    #     except Exception:
    #         logger.exception("处理事件分组失败: %s", group.key)

    # # ---- 合并规则 ----

    # def _merge(self, group: _PendingGroup) -> list[FileEvent]:
    #     """窗口内同一路径的多来源事件合并成一个（MOVED 拆成两个）事件。"""
    #     evs = group.events
    #     if any(e.event_type == EventType.MOVED for e in evs):
    #         return self._merge_moved(evs)
    #     if any(e.event_type == EventType.DELETED for e in evs):
    #         return [self._base(evs, EventType.DELETED)]
    #     return [self._base(evs, EventType.MODIFIED)]

    # def _merge_moved(self, evs: list[FileEvent]) -> list[FileEvent]:
    #     moved = next(e for e in evs if e.event_type == EventType.MOVED)
    #     dest = self._base(evs, EventType.MODIFIED, rel_path=moved.rel_path, host_path=moved.host_path)
    #     dest.move_src = moved.move_src
    #     src = self._base(
    #         evs,
    #         EventType.DELETED,
    #         rel_path=moved.move_src,
    #         host_path=(self.settings.root_dir / moved.move_src).as_posix(),
    #     )
    #     src.details["move_dest"] = moved.rel_path
    #     return [src, dest]

    # def _base(
    #     self,
    #     evs: list[FileEvent],
    #     event_type: EventType,
    #     rel_path: str | None = None,
    #     host_path: str | None = None,
    # ) -> FileEvent:
    #     ftp = next((e for e in evs if e.source == EventSource.FTP_LOG), None)
    #     latest = evs[-1]
    #     base = ftp if ftp is not None else latest
    #     ev = FileEvent(
    #         source=base.source,
    #         event_type=event_type,
    #         rel_path=rel_path if rel_path is not None else base.rel_path,
    #         host_path=host_path if host_path is not None else base.host_path,
    #         actor=ftp.actor if ftp is not None else None,
    #         client_ip=ftp.client_ip if ftp is not None else None,
    #         session_pid=ftp.session_pid if ftp is not None else None,
    #         observed_at=min(e.observed_at for e in evs),
    #         details={
    #             "sources": sorted({e.source.value for e in evs}),
    #             "raw_events": [
    #                 {
    #                     "source": e.source.value,
    #                     "event_type": e.event_type.value,
    #                     "size": e.size,
    #                     "actor": e.actor,
    #                     "client_ip": e.client_ip,
    #                     "observed_at": e.observed_at,
    #                 }
    #                 for e in evs
    #             ],
    #         },
    #     )
    #     # 任一来源已给出 checksum 则沿用（例如 hash_scan）
    #     for e in evs:
    #         if e.checksum:
    #             ev.checksum = e.checksum
    #             break
    #     return ev

    # async def _finalize(self, ev: FileEvent) -> None:
        # """落库前补充最新 stat 信息；文件已不存在则转为 deleted。"""
        # if ev.event_type == EventType.DELETED:
        #     return
        # try:
        #     st = os.stat(ev.rel_path, follow_symlinks=False)
        # except OSError:
        #     ev.event_type = EventType.DELETED
        #     return
        # if not stat_mod.S_ISREG(st.st_mode):
        #     ev.event_type = EventType.DELETED
        #     return
        # ev.size = st.st_size
        # ev.mtime = st.st_mtime
        # if ev.checksum is None and self.settings.hash_on_event:
        #     max_bytes = self.settings.hash_on_event_max_bytes
        #     if max_bytes == 0 or ev.size <= max_bytes:
        #         ev.checksum = await asyncio.to_thread(
        #             hash_file,
        #             ev.rel_path,
        #             self.settings.hash_algo,
        #             self.settings.chunk_size,
        #             0,
        #         )