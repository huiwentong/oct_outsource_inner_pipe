"""PostgreSQL 访问层：历史表 + 当前状态表 + 扫描状态表。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from versionwatch.config import Settings
from versionwatch.events import FileEvent

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS file_history (
    id               BIGSERIAL PRIMARY KEY,
    event_id         UUID NOT NULL UNIQUE,
    source           TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    rel_path         TEXT NOT NULL,
    abs_path         TEXT,
    file_size        BIGINT,
    mtime            TIMESTAMPTZ,
    checksum         TEXT,
    actor            TEXT,
    client_ip        TEXT,
    session_pid      INTEGER,
    version          INTEGER NOT NULL,
    previous_version INTEGER,
    overwritten      BOOLEAN NOT NULL DEFAULT FALSE,
    details          JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_at      TIMESTAMPTZ NOT NULL,
    recorded_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_file_history_rel_path    ON file_history (rel_path);
CREATE INDEX IF NOT EXISTS idx_file_history_observed_at ON file_history (observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_history_rel_version ON file_history (rel_path, version);

CREATE TABLE IF NOT EXISTS file_state (
    rel_path   TEXT PRIMARY KEY,
    file_size  BIGINT,
    mtime      DOUBLE PRECISION,
    checksum   TEXT,
    version    INTEGER NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scan_state (
    scan_type     TEXT PRIMARY KEY,
    last_start    TIMESTAMPTZ,
    last_finish   TIMESTAMPTZ,
    files_seen    BIGINT DEFAULT 0,
    files_changed BIGINT DEFAULT 0,
    details       JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""


async def open_connection(settings: Settings) -> psycopg.AsyncConnection[Any]:
    return await psycopg.AsyncConnection.connect(settings.database_url, row_factory=dict_row)


async def connect_with_retry(settings: Settings) -> psycopg.AsyncConnection[Any]:
    last_error: Exception | None = None
    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            conn = await open_connection(settings)
            logger.info("数据库连接成功 (attempt %d)", attempt)
            return conn
        except psycopg.OperationalError as exc:
            last_error = exc
            logger.warning(
                "数据库连接失败 (attempt %d/%d): %s", attempt, settings.db_connect_retries, exc
            )
            if attempt < settings.db_connect_retries:
                await asyncio.sleep(settings.db_connect_delay)
    assert last_error is not None
    raise last_error


async def init_schema(conn: psycopg.AsyncConnection[Any]) -> None:
    async with conn.cursor() as cur:
        await cur.execute(SCHEMA_SQL)
    await conn.commit()


async def fetch_state(conn: psycopg.AsyncConnection[Any], rel_path: str) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM file_state WHERE rel_path = %s", (rel_path,))
    return await cur.fetchone()


async def load_all_states(conn: psycopg.AsyncConnection[Any]) -> dict[str, dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM file_state")
    rows = await cur.fetchall()
    return {row["rel_path"]: row for row in rows}


async def upsert_state(
    conn: psycopg.AsyncConnection[Any],
    rel_path: str,
    file_size: int | None,
    mtime: float | None,
    checksum: str | None,
    version: int,
    is_deleted: bool = False,
) -> None:
    await conn.execute(
        """
        INSERT INTO file_state (rel_path, file_size, mtime, checksum, version, is_deleted, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (rel_path) DO UPDATE SET
            file_size = EXCLUDED.file_size,
            mtime = EXCLUDED.mtime,
            checksum = EXCLUDED.checksum,
            version = EXCLUDED.version,
            is_deleted = EXCLUDED.is_deleted,
            updated_at = now()
        """,
        (rel_path, file_size, mtime, checksum, version, is_deleted),
    )


async def update_state_mtime(
    conn: psycopg.AsyncConnection[Any], rel_path: str, mtime: float
) -> None:
    await conn.execute(
        "UPDATE file_state SET mtime = %s, updated_at = now() WHERE rel_path = %s",
        (mtime, rel_path),
    )


async def insert_history(
    conn: psycopg.AsyncConnection[Any],
    event: FileEvent,
    *,
    event_type: str,
    version: int,
    previous_version: int | None,
    overwritten: bool,
    event_id: str,
) -> bool:
    """写入历史行；event_id 冲突时忽略（幂等）。返回是否真正插入。"""
    observed = datetime.fromtimestamp(event.observed_at, tz=timezone.utc)
    mtime = datetime.fromtimestamp(event.mtime, tz=timezone.utc) if event.mtime else None
    cur = await conn.execute(
        """
        INSERT INTO file_history (
            event_id, source, event_type, rel_path, abs_path, file_size, mtime, checksum,
            actor, client_ip, session_pid, version, previous_version, overwritten, details, observed_at
        ) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (event_id) DO NOTHING
        """,
        (
            event_id,
            event.source.value,
            event_type,
            event.rel_path,
            event.host_path,
            event.size,
            mtime,
            event.checksum,
            event.actor,
            event.client_ip,
            event.session_pid,
            version,
            previous_version,
            overwritten,
            json.dumps(event.details, ensure_ascii=False),
            observed,
        ),
    )
    return cur.rowcount == 1


async def set_scan_start(conn: psycopg.AsyncConnection[Any], scan_type: str) -> None:
    await conn.execute(
        """
        INSERT INTO scan_state (scan_type, last_start)
        VALUES (%s, now())
        ON CONFLICT (scan_type) DO UPDATE SET last_start = now()
        """,
        (scan_type,),
    )


async def set_scan_finish(
    conn: psycopg.AsyncConnection[Any],
    scan_type: str,
    files_seen: int,
    files_changed: int,
    details: dict[str, Any],
) -> None:
    await conn.execute(
        """
        INSERT INTO scan_state (scan_type, last_finish, files_seen, files_changed, details)
        VALUES (%s, now(), %s, %s, %s::jsonb)
        ON CONFLICT (scan_type) DO UPDATE SET
            last_finish = now(),
            files_seen = EXCLUDED.files_seen,
            files_changed = EXCLUDED.files_changed,
            details = EXCLUDED.details
        """,
        (scan_type, files_seen, files_changed, json.dumps(details, ensure_ascii=False)),
    )