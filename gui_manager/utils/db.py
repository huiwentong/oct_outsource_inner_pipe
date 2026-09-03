from __future__ import annotations

from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from utils.config import server_config

cfg = server_config()


class Database:
    """访问 outsource_inner_pipe 数据库的通用封装。

    供 collector / usermanager 两个 GUI 复用（查询外包方用户、写入记录等）。
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or cfg.get("server_ip", "127.0.0.1")
        self.port = port or int(cfg.get("db_port", 5432))
        self.database = database or cfg.get("db_name", "outsource_inner_pipe")
        self.user = user or cfg.get("db_user", "admin")
        self.password = password or cfg.get("db_password", "")

    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)

    # ---------- 外包方用户相关常用查询 ----------

    def get_all_user(self):
        """获取 ftpuser 表中的全部外包方用户。"""
        return self.fetch_all("SELECT * FROM ftpuser ORDER BY id;")

    def get_user_names(self, keyword: Optional[str] = None) -> list[str]:
        """获取外包方用户登录名列表，用于下拉菜单自动补全。"""
        sql = "SELECT name FROM ftpuser"
        params: tuple = ()
        if keyword:
            sql += " WHERE name ILIKE %s"
            params = (f"%{keyword}%",)
        sql += " ORDER BY name;"
        rows = self.fetch_all(sql, params)
        return [row["name"] for row in rows]

    def get_user_by_name(self, name: str) -> Optional[dict[str, Any]]:
        sql = "SELECT * FROM ftpuser WHERE name = %s;"
        return self.fetch_one(sql, (name,))
