"""定时 hash 校验：对比 file_state，发现绕过 ftp/watchdog 的静默变更。"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from versionwatch.config import Settings
from versionwatch.db import (
    load_all_states,
    set_scan_finish,
    set_scan_start,
    update_state_mtime,
)
from versionwatch.events import EventSource, EventType, FileEvent
from versionwatch.hashing import hash_file

logger = logging.getLogger(__name__)


class HashScanner:
    def __init__(
        self,
        settings: Settings,
        conn_factory: Callable[[], Any],
        emit: Callable[[FileEvent], None],
    ) -> None:
        self.settings = settings
        self.conn_factory = conn_factory
        self.emit = emit
        self._exclude = [re.compile(p) for p in settings.exclude_patterns]

    def _excluded(self, rel: str) -> bool:
        return any(p.search(rel) for p in self._exclude)

    async def run(self) -> None:
        if not self.settings.hash_scan_enabled:
            logger.info("定时 hash 校验已禁用")
            return
        cycle = 0
        while True:
            try:
                cycle += 1
                await self.scan_once(cycle)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("hash 扫描失败")
            await asyncio.sleep(self.settings.hash_scan_interval)

    async def scan_once(self, cycle: int) -> None:
        full = (cycle % self.settings.full_hash_cycles) == 0
        logger.info("hash 扫描开始 (cycle=%d, full_hash=%s)", cycle, full)
        conn = await self.conn_factory()
        try:
            await set_scan_start(conn, "hash")
            states = await load_all_states(conn)
            seen: set[str] = set()
            changed = 0
            now = datetime.now(timezone.utc).timestamp()

            for rel, st in await asyncio.to_thread(self._walk):
                seen.add(rel)
                prev = states.get(rel)
                if (
                    prev
                    and not prev["is_deleted"]
                    and not full
                    and prev["file_size"] == st.st_size
                    and prev["mtime"] == st.st_mtime
                    and prev["checksum"]
                ):
                    continue  # stat 无变化，跳过
                if st.st_mtime > now - self.settings.hash_scan_grace_seconds:
                    continue  # 最近仍在写入，留给下轮
                digest = await asyncio.to_thread(
                    hash_file,
                    os.path.join(self.settings.root_dir, rel),
                    self.settings.hash_algo,
                    self.settings.chunk_size,
                    self.settings.hash_scan_max_bytes,
                )
                if prev and not prev["is_deleted"]:
                    if digest == prev["checksum"] and prev["file_size"] == st.st_size:
                        # 仅 mtime 变化（touch）：静默更新状态，不产生历史事件
                        await update_state_mtime(conn, rel, st.st_mtime)
                        continue
                    ev_type = EventType.MODIFIED
                else:
                    ev_type = EventType.CREATED
                ev = FileEvent(
                    source=EventSource.HASH_SCAN,
                    event_type=ev_type,
                    rel_path=rel,
                    host_path=(self.settings.root_dir / rel).as_posix(),
                    size=st.st_size,
                    mtime=st.st_mtime,
                    checksum=digest,
                    details={"scan_cycle": cycle, "full_hash": full},
                )
                self.emit(ev)
                changed += 1

            for rel, prev in states.items():
                if rel in seen or prev["is_deleted"]:
                    continue
                self.emit(
                    FileEvent(
                        source=EventSource.HASH_SCAN,
                        event_type=EventType.DELETED,
                        rel_path=rel,
                        host_path=(self.settings.root_dir / rel).as_posix(),
                        details={"scan_cycle": cycle, "full_hash": full},
                    )
                )
                changed += 1

            await set_scan_finish(conn, "hash", len(seen), changed, {"cycle": cycle, "full_hash": full})
            await conn.commit()
        finally:
            await conn.close()
        logger.info("hash 扫描结束: seen=%d changed=%d", len(seen), changed)

    def _walk(self) -> list[tuple[str, os.stat_result]]:
        """遍历监控目录，返回 (rel_path, stat)。跳过符号链接与目录。"""
        results: list[tuple[str, os.stat_result]] = []
        root = self.settings.root_dir
        for dirpath, dirnames, filenames in os.walk(root):
            kept: list[str] = []
            for d in dirnames:
                rel_d = os.path.relpath(os.path.join(dirpath, d), root).replace(os.sep, "/")
                if not self._excluded(rel_d):
                    kept.append(d)
            dirnames[:] = kept
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if self._excluded(rel):
                    continue
                try:
                    if os.path.islink(full):
                        continue
                    st = os.stat(full)
                except OSError:
                    continue
                results.append((rel, st))
        return results