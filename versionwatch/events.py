"""统一事件模型：把 ftp_log / watchdog / hash_scan 三类来源归一化为 FileEvent。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventSource(str, Enum):
    FTP_LOG = "ftp_log"
    WATCHDOG = "watchdog"
    HASH_SCAN = "hash_scan"


class EventType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass(slots=True)
class FileEvent:
    """一次文件变更的统一表示。

    ``rel_path`` 是相对监控根的路径（统一使用 "/" 分隔、无前导 "/"），
    ``host_path`` 是监控进程视角下的绝对路径。
    """

    event_type: EventType\
    
    rel_path: str
    move_src: str | None = None  # MOVED 事件的源相对路径

    size: int | None = None
    checksum: str | None = None
    actor: str | None = None

    client_ip: str | None = None
    session_pid: int | None = None
    client_name: str | None = None

    details: dict[str, Any] = field(default_factory=dict)
    mtime: float | None = None
    observed_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        return (
            f"{self.event_type.value} {self.rel_path} "
            f"size={self.size} actor={self.actor or '-'} checksum={self.checksum or '-'}"
        )


def normalize_rel_path(path: str) -> str:
    """把任意路径规整为相对根目录、使用 "/" 分隔、无前导 "/" 的形式。"""
    p = path.replace("\\", "/").strip()
    while p.startswith("/"):
        p = p[1:]
    return p