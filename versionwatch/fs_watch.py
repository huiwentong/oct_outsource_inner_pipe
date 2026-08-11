"""基于 watchdog(inotify) 的目录事件监听。"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from versionwatch.config import Settings
from versionwatch.events import EventSource, EventType, FileEvent, normalize_rel_path

logger = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    """把 watchdog 事件转换为 FileEvent 并投递到 asyncio 队列。"""

    def __init__(
        self,
        root: Path,
        queue: asyncio.Queue,
        exclude: list[re.Pattern[str]],
    ) -> None:
        self._root = root
        self._queue = queue
        self._exclude = exclude
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def _excluded(self, rel: str) -> bool:
        return any(p.search(rel) for p in self._exclude)

    def _push(self, event_type: EventType, path: str, move_src: str | None = None) -> None:
        rel = normalize_rel_path(os.path.relpath(path, self._root))
        if self._excluded(rel):
            return
        ev = FileEvent(
            source=EventSource.WATCHDOG,
            event_type=event_type,
            rel_path=rel,
            host_path=Path(path).as_posix(),
            move_src=move_src,
        )
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, ev)

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        self._push(EventType.CREATED, event.src_path)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        self._push(EventType.MODIFIED, event.src_path)

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        self._push(EventType.DELETED, event.src_path)

    def on_moved(self, event) -> None:
        if event.is_directory:
            return
        rel_src = normalize_rel_path(os.path.relpath(event.src_path, self._root))
        if self._excluded(rel_src):
            return
        ev = FileEvent(
            source=EventSource.WATCHDOG,
            event_type=EventType.MOVED,
            rel_path=normalize_rel_path(os.path.relpath(event.dest_path, self._root)),
            host_path=Path(event.dest_path).as_posix(),
            move_src=rel_src,
        )
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, ev)


class FsWatcher:
    """watchdog Observer 的轻量封装。"""

    def __init__(self, settings: Settings, queue: asyncio.Queue) -> None:
        self._settings = settings
        self._exclude = [re.compile(p) for p in settings.exclude_patterns]
        self._observer = Observer(timeout=1.0)
        self._handler = _Handler(settings.root_dir, queue, self._exclude)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._handler.bind_loop(loop)
        self._observer.schedule(self._handler, str(self._settings.root_dir), recursive=True)
        self._observer.start()
        logger.info("watchdog 监听启动: %s", self._settings.root_dir)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=10)
        logger.info("watchdog 监听停止")