from __future__ import annotations

from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from utils.config import server_config
from utils.paths import to_ftp

cfg = server_config()


def classify_changes(checksums: dict[str, str], history: list[dict], events: list[dict]) -> dict[str, dict]:
    """按外包方上次拿到的指纹, 判断这次发的每个 entity 是新增 / 有更新 / 未变.

    Args:
        checksums: 这次发出去的 {FTP 相对路径 oct/...: 指纹}
        history: 外包方以前的发货单 [{create_time, transformer_files(I 盘路径, 可能是目录)}]
        events: 这次文件在 file_events 里的 UPLOAD 记录 [{rel_path, checksum, observed_at}]

    Returns:
        {entity: {"status": "新增"|"有更新"|"未变", "added": [路径], "updated": [路径]}}
    """
    key = lambda p: p.replace("\\", "/").lstrip("/").lower()  # 比路径时忽略大小写和前导 /

    # 从历史发货单 (collection_history) 整理出: 每个发过的路径 (文件或目录) 最近一次发给外包方的时间，例:
    # {"oct/mk2/asset/dasheng/rig": 10-01 ...,          # 发过整个目录
    #  "oct/mk2/asset/dasheng/rig/a.ma": 10-15 ...}     # 单独发过这个文件
    sent = {}
    for row in history:
        for f in row["transformer_files"]:
            p = to_ftp(f)
            if p and (key(p) not in sent or sent[key(p)] < row["create_time"]):
                sent[key(p)] = row["create_time"]

    def last_sent(path):
        """文件自身或任一上级目录被发过, 都算收到过; 取最近一次."""
        parts = key(path).split("/")
        times = [sent[k] for k in ("/".join(parts[:i]) for i in range(1, len(parts) + 1)) if k in sent]
        return max(times, default=None)

    # 从上传记录 (file_events) 整理出: 每个文件按时间排好的上传指纹, 用来查外包方当时拿到的版本
    # {FTP 相对路径: [file_events 行, 按 observed_at 从早到晚]}, 例:
    # {"oct/mk2/asset/dasheng/rig/a.ma": [{"checksum": "aa11..", "observed_at": 10-01 ...},
    #                                     {"checksum": "bb22..", "observed_at": 10-10 ...}]}
    uploads: dict[str, list] = {}
    for e in sorted(events, key=lambda e: e["observed_at"]):
        uploads.setdefault(e["rel_path"], []).append(e)

    result, counts = {}, {}
    for path, cs in checksums.items():
        parts = path.split("/")
        # oct/项目/类型/entity/环节/...; default_path.json 这类实体层文件不参与
        # MG picker 也不参与: 本地在 W:/projects/lib, 发货单只存本地路径, 反推不出 FTP 路径, 否则每次都误报新增
        if len(parts) < 6 or parts[4:6] == ["rig", "mg_picker"]:
            continue
        entity = parts[3]
        # 这个 entity 的结果, 同一 entity 的多个文件共用一个字典累加; status 等循环完再统一算
        c = result.setdefault(entity, {"status": "未变", "added": [], "updated": []})
        counts[entity] = counts.get(entity, 0) + 1  # 参与判断的文件数, 用来判断是否"全部新增"
        t = last_sent(path)  # 外包方最近一次收到这个文件 (或其上级目录) 的时间
        if t is None:  # 从没收到过 -> 新增
            c["added"].append(path)
            continue
        # t 之前这个文件的历次上传指纹, 最后一个就是外包方当时拿到的版本
        had = [e["checksum"] for e in uploads.get(path, []) if e["observed_at"] <= t]
        if not had or had[-1] != cs:  # 和这次的指纹不同 -> 有更新; 查不到当时的记录也算有更新, 宁可多报
            c["updated"].append(path)

    for entity, c in result.items():
        if len(c["added"]) == counts[entity]:
            c["status"] = "新增"
        elif c["added"] or c["updated"]:
            c["status"] = "有更新"
    return result


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
            conn.commit()

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

    def get_user_contact(self, name):
            """获取外包方用户登录名列表，用于下拉菜单自动补全。"""
            sql = "SELECT * FROM ftpuser"
            params: tuple = ()
            if name:
                sql += " WHERE name = %s"
                params = (name,)
            sql += " ORDER BY name;"
            ret = self.fetch_one(sql, params)
            if ret:
                return ret

    def get_user_by_name(self, name: str) -> Optional[dict[str, Any]]:
        sql = "SELECT * FROM ftpuser WHERE name = %s;"
        return self.fetch_one(sql, (name,))

    def get_file_status(self, rel_path: str) -> Optional[dict[str, Any]]:
        sql = """
        SELECT * FROM file_state
        WHERE rel_path = %s 
        ORDER BY updated_at DESC LIMIT 1;
        """
        return self.fetch_one(sql, (rel_path,))

    def vendor_entity_changes(self, vendor: str, checksums: dict[str, str], before) -> dict[str, dict]:
        """这次发给外包方的 entity 里哪些新增、哪些有更新, 规则见 classify_changes.

        Args:
            vendor: 外包方登录名
            checksums: 这次发出去的 {FTP 相对路径 oct/...: 指纹}
            before: 本次开始抓包的数据库时刻, 只看它之前的发货单
        """
        history = self.fetch_all(
            "SELECT create_time, transformer_files FROM collection_history "
            "WHERE vendorname = %s AND create_time < %s;",
            (vendor, before),
        )
        # 一次取回全部文件的上传记录, 不要每个文件查一次
        events = self.fetch_all(
            "SELECT rel_path, checksum, observed_at FROM file_events "
            "WHERE details->>'verb' = 'UPLOAD' AND rel_path = ANY(%s);",
            (list(checksums),),
        )
        return classify_changes(checksums, history, events)

    def add_collection_history(self,
            username, 
            vendorname, 
            asset, 
            assettype, 
            step, 
            description, 
            transformer_files, 
            rely_groups
        ):

        sql = """
        INSERT INTO collection_history (
            username,
            vendorname,
            asset,
            asset_type,
            step,
            description,
            transformer_files,
            rely_groups
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        );
        """

        self.execute(
            sql,
            (
                username,
                vendorname,
                asset,
                assettype,
                step,
                description,
                transformer_files,
                rely_groups,
            )
        )



if __name__ == "__main__":
    db = Database()
    status = db.get_file_status("oct/tdtest/asset/tao_a/tex/tao_a.tex.texture/usd/comdp.usd")
    cs = status.get('checksum') if status else None
    print(cs)