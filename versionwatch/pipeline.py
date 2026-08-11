"""事件流水线：去抖 + 多来源合并 + 派发到 recorder。"""

from __future__ import annotations

import asyncio
import logging
import os
import stat as stat_mod
import time
from dataclasses import dataclass, field
from typing import Any

from versionwatch.config import Settings
from versionwatch.events import EventSource, EventType, FileEvent
from versionwatch.hashing import hash_file

logger = logging.getLogger(__name__)


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
    """从原始事件队列读取事件，去抖合并后交给 recorder 落库。"""

    def __init__(self, settings: Settings, queue: asyncio.Queue, recorder: Any) -> None:
        self.settings = settings
        self.queue = queue
        self.recorder = recorder
        self._groups: dict[str, _PendingGroup] = {}
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        logger.info("事件流水线启动")
        while not self._stop.is_set():
            try:
                ev = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                ev = None
            if ev is not None:
                self._ingest(ev)
            await self._flush_due()
        # 退出前把剩余分组强制刷完
        await self._flush_all()

    def _ingest(self, ev: FileEvent) -> None:
        group = self._groups.get(ev.rel_path)
        if group is None:
            group = _PendingGroup(ev.rel_path)
            self._groups[ev.rel_path] = group
        group.add(ev)

    async def _flush_due(self) -> None:
        now = time.monotonic()
        due = [g for g in self._groups.values() if g.is_due(self.settings.debounce_seconds, now)]
        for group in due:
            self._groups.pop(group.key, None)
            await self._process(group)

    async def _flush_all(self) -> None:
        groups = list(self._groups.values())
        self._groups.clear()
        for group in groups:
            await self._process(group)

    async def _process(self, group: _PendingGroup) -> None:
        try:
            for ev in self._merge(group):
                await self._finalize(ev)
                await self.recorder.record(ev)
        except Exception:
            logger.exception("处理事件分组失败: %s", group.key)

    # ---- 合并规则 ----

    def _merge(self, group: _PendingGroup) -> list[FileEvent]:
        """窗口内同一路径的多来源事件合并成一个（MOVED 拆成两个）事件。"""
        evs = group.events
        if any(e.event_type == EventType.MOVED for e in evs):
            return self._merge_moved(evs)
        if any(e.event_type == EventType.DELETED for e in evs):
            return [self._base(evs, EventType.DELETED)]
        return [self._base(evs, EventType.MODIFIED)]

    def _merge_moved(self, evs: list[FileEvent]) -> list[FileEvent]:
        moved = next(e for e in evs if e.event_type == EventType.MOVED)
        dest = self._base(evs, EventType.MODIFIED, rel_path=moved.rel_path, host_path=moved.host_path)
        dest.move_src = moved.move_src
        src = self._base(
            evs,
            EventType.DELETED,
            rel_path=moved.move_src,
            host_path=(self.settings.root_dir / moved.move_src).as_posix(),
        )
        src.details["move_dest"] = moved.rel_path
        return [src, dest]

    def _base(
        self,
        evs: list[FileEvent],
        event_type: EventType,
        rel_path: str | None = None,
        host_path: str | None = None,
    ) -> FileEvent:
        ftp = next((e for e in evs if e.source == EventSource.FTP_LOG), None)
        latest = evs[-1]
        base = ftp if ftp is not None else latest
        ev = FileEvent(
            source=base.source,
            event_type=event_type,
            rel_path=rel_path if rel_path is not None else base.rel_path,
            host_path=host_path if host_path is not None else base.host_path,
            actor=ftp.actor if ftp is not None else None,
            client_ip=ftp.client_ip if ftp is not None else None,
            session_pid=ftp.session_pid if ftp is not None else None,
            observed_at=min(e.observed_at for e in evs),
            details={
                "sources": sorted({e.source.value for e in evs}),
                "raw_events": [
                    {
                        "source": e.source.value,
                        "event_type": e.event_type.value,
                        "size": e.size,
                        "actor": e.actor,
                        "client_ip": e.client_ip,
                        "observed_at": e.observed_at,
                    }
                    for e in evs
                ],
            },
        )
        # 任一来源已给出 checksum 则沿用（例如 hash_scan）
        for e in evs:
            if e.checksum:
                ev.checksum = e.checksum
                break
        return ev

    async def _finalize(self, ev: FileEvent) -> None:
        """落库前补充最新 stat 信息；文件已不存在则转为 deleted。"""
        if ev.event_type == EventType.DELETED:
            return
        try:
            st = os.stat(ev.host_path, follow_symlinks=False)
        except OSError:
            ev.event_type = EventType.DELETED
            return
        if not stat_mod.S_ISREG(st.st_mode):
            ev.event_type = EventType.DELETED
            return
        ev.size = st.st_size
        ev.mtime = st.st_mtime
        if ev.checksum is None and self.settings.hash_on_event:
            max_bytes = self.settings.hash_on_event_max_bytes
            if max_bytes == 0 or ev.size <= max_bytes:
                ev.checksum = await asyncio.to_thread(
                    hash_file,
                    ev.host_path,
                    self.settings.hash_algo,
                    self.settings.chunk_size,
                    0,
                )