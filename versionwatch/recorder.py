"""把合并后的事件写入 PostgreSQL，并维护版本号（file_state.version）。"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

import psycopg

from versionwatch.config import Settings
from versionwatch.db import fetch_state, insert_history, upsert_state
from versionwatch.events import EventType, FileEvent

logger = logging.getLogger(__name__)


def event_id_for(ev: FileEvent) -> str:
    """稳定去重 ID：同一来源、路径、时刻、size/checksum 视为同一次变更。"""
    payload = (
        f"{ev.source.value}:{ev.rel_path}:{ev.observed_at}:{ev.size}:{ev.checksum}:{ev.event_type.value}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"versionwatch://{payload}"))


def resolve_version(prev: dict[str, Any] | None) -> tuple[str, int, int | None, bool]:
    """根据当前状态计算 (event_type, version, previous_version, overwritten)。"""
    if prev is None:
        return ("created", 1, None, False)
    if prev["is_deleted"]:
        # 删除后重新创建：版本号继续累加，便于审计
        return ("created", prev["version"] + 1, prev["version"], False)
    return ("modified", prev["version"] + 1, prev["version"], True)


class Recorder:
    """单连接写入器：失败自动重连。"""

    def __init__(self, settings: Settings, conn_factory: Callable[[], Any]) -> None:
        self.settings = settings
        self.conn_factory = conn_factory
        self._conn: Any = None

    async def _ensure_conn(self) -> Any:
        if self._conn is None or self._conn.closed:
            self._conn = await self.conn_factory()
        return self._conn

    async def _reset_conn(self) -> None:
        if self._conn is not None:
            try:
                await self._conn.close()
            except Exception:
                pass
            self._conn = None

    async def close(self) -> None:
        await self._reset_conn()

    async def record(self, ev: FileEvent) -> None:
        conn = await self._ensure_conn()
        try:
            if ev.event_type == EventType.DELETED:
                await self._record_deleted(conn, ev)
            else:
                await self._record_upsert(conn, ev)
            await conn.commit()
        except psycopg.OperationalError:
            await self._reset_conn()
            raise
        except Exception:
            await conn.rollback()
            raise

    async def _record_deleted(self, conn: Any, ev: FileEvent) -> None:
        prev = await fetch_state(conn, ev.rel_path)
        prev_version = prev["version"] if prev else 1
        inserted = await insert_history(
            conn,
            ev,
            event_type="deleted",
            version=prev_version,
            previous_version=prev_version,
            overwritten=False,
            event_id=event_id_for(ev),
        )
        await upsert_state(conn, ev.rel_path, None, None, None, prev_version, is_deleted=True)
        if inserted:
            logger.info(
                "删除已记录 v%03d: %s (actor=%s)", prev_version, ev.rel_path, ev.actor or "-"
            )

    async def _record_upsert(self, conn: Any, ev: FileEvent) -> None:
        prev = await fetch_state(conn, ev.rel_path)
        if prev is not None and not prev["is_deleted"]:
            # 内容没有实质变化则跳过（多来源去重）
            same_content = (
                (ev.checksum is not None and prev["checksum"] == ev.checksum)
                or (
                    ev.checksum is None
                    and ev.size is not None
                    and prev["file_size"] == ev.size
                    and prev["mtime"] == ev.mtime
                )
            )
            if same_content:
                return

        event_type, version, previous_version, overwritten = resolve_version(prev)
        ev.details["version_label"] = f"v{version:03d}"
        inserted = await insert_history(
            conn,
            ev,
            event_type=event_type,
            version=version,
            previous_version=previous_version,
            overwritten=overwritten,
            event_id=event_id_for(ev),
        )
        await upsert_state(
            conn,
            ev.rel_path,
            ev.size,
            ev.mtime,
            ev.checksum,
            version,
            is_deleted=False,
        )
        if inserted:
            action = "覆盖" if overwritten else "新建"
            logger.info(
                "%s已记录 v%03d: %s size=%s actor=%s",
                action,
                version,
                ev.rel_path,
                ev.size,
                ev.actor or "-",
            )