import subprocess
import pwd
import grp
from datetime import datetime
import os
from pathlib import Path
from typing import Optional
from psycopg2.extras import RealDictCursor
import psycopg2
import requests
import json
import smtplib
from email.mime.text import MIMEText
from logger.core import get_log

logger = get_log()

class Notify:
    def __init__(self, ding_id, email) -> None:
        self.dingid = ding_id
        self.email = email
        self.url = 'http://192.168.20.217:8080/ding/msg/simple'



    def send_simple_message(self, msg, title):

        mk_message = """
# 🚀 来自十月权限管理器的通知!
___
* ***通知信息:***  {message}
***
| 名称 | 值 |
| :--- | :---: | 
| 版本类型 | {type} | 
| 版本名称 | {vname} |
| 任务名称 | {tname} |
| 实体名称 | {ename} |
***
`发送时间： {datetime_now}`
        """.format(
            message=msg['message'],
            type=msg['type'],
            vname=msg['vname'],
            tname=msg['tname'],
            ename=msg['ename'],
            datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        post_data = {
            'title': title ,
            'text': mk_message
        }
        ret = requests.post(
            url=self.url,
            params={'user_id': self.dingid},
            data=json.dumps(post_data)
        )

        ret.raise_for_status()
        return ret.json()


    def send_email(self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        receiver: str,
        subject: str,
        content: str,
        ):
        msg = MIMEText(content, "plain", "utf-8")
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = subject

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(username, password)
            server.sendmail(
                sender,
                receiver,
                msg.as_string(),
            )


class Database:
    def __init__(
        self,
        host: str = "postgres",
        port: int = 5432,
        database: str = "outsource_inner_pipe",
        user: str = "admin",
        password: str = "123456",
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.init_schema()

    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def create_user(
        self,
        name: str,
        description: Optional[str] = None,
        dingtalk_id: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        home: Optional[str] = None,
        uid: Optional[str] = None,
    ):
        sql = """
            INSERT INTO ftpuser (
                name,
                description,
                dingtalk_id,
                email,
                password,
                home,
                uid
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    sql,
                    (
                        name,
                        description,
                        dingtalk_id,
                        email,
                        password,
                        home,
                        uid
                    ),
                )
                return cursor.fetchone()


    def get_user(self, user_id: int):
        sql = """
            SELECT
                id,
                name,
                description,
                dingtalk_id,
                email,
                password,
                created_at,
                updated_at
            FROM ftpuser
            WHERE id = %s;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, (user_id,))
                return cursor.fetchone()

    def get_user_by_name(self, name: str):
        sql = """
            SELECT
                id,
                name,
                description,
                dingtalk_id,
                email,
                password,
                created_at,
                updated_at
            FROM ftpuser
            WHERE name = %s;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, (name,))
                return cursor.fetchone()

    def get_users(self):
        sql = """
            SELECT
                id,
                name,
                description,
                dingtalk_id,
                email,
                password,
                home,
                uid,
                created_at,
                updated_at
            FROM ftpuser
            ORDER BY id;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
                return cursor.fetchall()


    def init_schema(self):
        SQL = """
CREATE TABLE IF NOT EXISTS ftpuser (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    dingtalk_id TEXT,
    email TEXT,
    password TEXT NOT NULL,
    uid TEXT NOT NULL UNIQUE,
    home TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS permission_group (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    gid TEXT NOT NULL UNIQUE,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_permission_group (
    user_id BIGINT NOT NULL REFERENCES ftpuser(id) ON DELETE CASCADE,
    permission_group_id BIGINT NOT NULL REFERENCES permission_group(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, permission_group_id)
);

-- updated_at 自动更新时间函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ftpuser trigger
DROP TRIGGER IF EXISTS ftpuser_updated_at ON ftpuser;

CREATE TRIGGER ftpuser_updated_at
BEFORE UPDATE ON ftpuser
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- permission_group trigger
DROP TRIGGER IF EXISTS permission_group_updated_at ON permission_group;

CREATE TRIGGER permission_group_updated_at
BEFORE UPDATE ON permission_group
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(SQL)


    def update_user(
        self,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        dingtalk_id: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ):
        sql = """
            UPDATE ftpuser
            SET
                name = COALESCE(%s, name),
                description = COALESCE(%s, description),
                dingtalk_id = COALESCE(%s, dingtalk_id),
                email = COALESCE(%s, email),
                password = COALESCE(%s, password),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    sql,
                    (
                        name,
                        description,
                        dingtalk_id,
                        email,
                        password,
                        user_id,
                    ),
                )

                return cursor.fetchone()


    def delete_user(self, name: str):
        sql = """
            DELETE FROM ftpuser
            WHERE name = %s
            RETURNING id;
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (name,))
                result = cursor.fetchone()

                return result[0] if result else None

    def delete_group(self, group_name: str):
        sql = """
            DELETE FROM permission_group
            WHERE name = %s
            RETURNING id;
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (group_name,))
                result = cursor.fetchone()
                return result[0] if result else None

    def get_groups(self):
        sql = """
            SELECT
                id,
                name,
                description,
                gid,
                created_at,
                updated_at
            FROM permission_group
            ORDER BY id;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
                return cursor.fetchall()

    def get_group_by_name(self, name: str):
            sql = """
                SELECT
                    id,
                    name,
                    description,
                    created_at,
                    updated_at
                FROM permission_group
                WHERE name = %s;
            """
    
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql, (name,))
                    return cursor.fetchone()

    def create_groups(self, name, description, gid):
        sql = """
            INSERT INTO permission_group (
                name,
                description,
                gid
            )
            VALUES (%s, %s, %s)
            RETURNING *;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    sql,
                    (
                        name,
                        description,
                        gid,
                    ),
                )
                return cursor.fetchone()


    def add_user2group(
        self,
        user_name: str,
        group_names: list[str],
    ):
        user = self.get_user_by_name(user_name)
        if not user:
            raise ValueError(f"用户不存在: {user_name}")
        uid = user["id"]

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for group_name in group_names:
                    if group_name == user_name:
                        continue  
                    group = self.get_group_by_name(group_name)
                    if not group:
                        raise ValueError(f"权限组不存在: {group_name}")
                    gid = group["id"]
                    cursor.execute(
                        """
                        INSERT INTO user_permission_group (
                            user_id,
                            permission_group_id
                        )
                        VALUES (%s, %s)
                        ON CONFLICT (user_id, permission_group_id)
                        DO NOTHING;
                        """,
                        (uid, gid),
                    )
            conn.commit()


    def get_user_groups(self, user_name: str):
        user = self.get_user_by_name(user_name)
        if not user:
            raise ValueError(f"用户不存在: {user_name}")
        uid = user["id"]

        sql = """
            SELECT
                pg.name AS group_name,
                pg.description AS group_description
            FROM permission_group pg
            JOIN user_permission_group upg ON pg.id = upg.permission_group_id
            WHERE upg.user_id = %s;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, (uid,))
                return cursor.fetchall()


class FTPUserManager:
    db = Database()

    @classmethod
    def user_exists(cls, username):
        try:
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False

    @classmethod
    def group_exists(cls, groupname):
        try:
            grp.getgrnam(groupname)
            return True
        except KeyError:
            return False

    @classmethod
    def create_user(cls, username, password, home, ding, email, description, db=True,uid:str=''):
        if FTPUserManager.user_exists(username):
            return cls.get_user(username)[0]

        user = {}
        if db:
            cmd = [
                "useradd",
                "-s", "/bin/bash",
                "-d", '/srv/ftp', username
            ]
    
            subprocess.run(cmd, check=True)
            uid = str(pwd.getpwnam(username).pw_uid)
            user = cls.db.create_user(username,description=description,dingtalk_id=ding,email=email,password=password, home=home, uid=uid)

        else:
            if not uid:
                raise ValueError("uid is required when db=False")
            cmd = [
                "useradd",
                "-u", str(uid),
                "-s", "/bin/bash",
                "-d", '/srv/ftp', username
            ]
            subprocess.run(cmd, check=True)

        # 设置 FTP 登录密码
        subprocess.run(
            ["chpasswd"],
            input=f"{username}:{password}\n",
            text=True,
            check=True,
        )


        if home:

            logger.info(f'{username}创建用户目录{home}且赋予权限！')
            if not os.path.exists(home):
                subprocess.run(
                    ["mkdir", "-p", home],
                    check=True,
                )
            
            subprocess.run(
                ["chown", f"{username}:oip_admin", home],
                check=True,
            )
            subprocess.run(
                ["chmod", "2750", home],
                check=True,
            )
            subprocess.run(
                ["setfacl", "-m", f"g:oip_admin:rx", home],
                check=True,
            )
            subprocess.run(
                ["setfacl", "-d", "-m", f"g:oip_admin:rx", home],
                check=True,
            )

        return user
    

    @classmethod
    def delete_user(cls, username, db=True):
        if not FTPUserManager.user_exists(username):
            return
        if db:
            cls.db.delete_user(username)
        subprocess.run(
            ["userdel", "-r", username],
            check=True
        )

        subprocess.run(
            ["rm", "-rf", f'/srv/ftp/{username}'],
            check=True
        )


    @classmethod
    def create_group(cls, groupname, description, db=True, gid:str=''):
        if FTPUserManager.group_exists(groupname):
            return cls.get_group(groupname=groupname)[0]

        ret_g = {}


        if db:
            subprocess.run(
                ["groupadd", groupname],
                check=True
            )
            result = subprocess.run(
                ["getent", "group", groupname],
                capture_output=True,
                text=True,
                check=True,
            )
            gid = str(result.stdout.split(":")[2])
            ret_g = cls.db.create_groups(groupname, description, gid)
            return ret_g

        else:
            if not gid:
                raise ValueError("gid is required when db=False")
            subprocess.run(
                ["groupadd","-g", gid, groupname],
                check=True
            )


    @classmethod
    def delete_group(cls, groupname, db=True):
        if not FTPUserManager.group_exists(groupname):
            return
        if db:
            cls.db.delete_group(groupname)
        subprocess.run(
            ["groupdel", groupname],
            check=True
        )

    @classmethod
    def get_user(cls, username=None):
        if username:
            if cls.user_exists(username):
                return [cls.db.get_user_by_name(username)]

        users = []
        for user in pwd.getpwall():
            # db_user = cls.db.get_user_by_name(user.pw_name)
            # if db_user:
            users.append(user.pw_name)
        return users

    @classmethod
    def get_group(cls,groupname=None):
        if groupname:
            if cls.group_exists(groupname):
                return [cls.db.get_group_by_name(groupname)]
        
        groups = []
        for group in grp.getgrall():
            # db_group = cls.db.get_group_by_name(group.gr_name)
            # if db_group:
            groups.append(group.gr_name)

        return groups

    @classmethod
    def set_user_group(cls, username, groupnames,db=True):
        gs = cls.get_group()
        for g in groupnames:
            if g not in gs: raise ValueError(f'group {g} can not found in ftp groups, create it and try again!')
        if username not in groupnames:
            groupnames.append(username)

        if db:
            cls.db.add_user2group(username, groupnames)

        subprocess.run(
            ["usermod", "-G", ','.join(groupnames), username],
            check=True
        )

    @classmethod
    def get_user_group(cls, username):
        result = subprocess.run(
            ["id", "-Gn", username],
            capture_output=True,
            text=True,
            check=True,
        )

        groups = result.stdout.strip().split()
        return groups[1:]

    @staticmethod
    def _run(*args: str) -> None:
        subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
        )



    @classmethod
    def set_path_group(
        cls,
        path: str,
        group: str,
        chmod: str = "rx",
        recursive: bool = True,
        inherit: bool = False,
    ):
        path_obj = Path(path)

        if not path_obj.exists():
            raise RuntimeError(f"{path} does not exist!")

        if not cls.group_exists(group):
            raise RuntimeError(f"{group} does not exist!")

        # ACL permissions should only contain r/w/x
        if not chmod or any(c not in "rwx" for c in chmod):
            raise ValueError(
                f"Invalid ACL permission: {chmod!r}. "
                "Expected a combination of r, w and x."
            )

        target = str(path_obj)

        if recursive:
            cmd = ["setfacl", "-R", "-m", f"g:{group}:{chmod}", target]
        else:
            cmd = ["setfacl", "-m", f"g:{group}:{chmod}", target]

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        # Default ACL controls permissions inherited by newly created
        # files/directories under this directory.
        if inherit:
            if not path_obj.is_dir():
                raise RuntimeError(
                    f"inherit=True requires a directory: {path}"
                )

            default_cmd = [
                "setfacl",
                "-d",
                "-m",
                f"g:{group}:{chmod}",
                target,
            ]

            subprocess.run(
                default_cmd,
                capture_output=True,
                text=True,
                check=True,
            )


    @classmethod
    def delete_path_group(
        cls,
        path: str,
        group: str,
        recursive: bool = True,
        inherit: bool = True,
    ) -> None:
        path_obj = Path(path)

        if not path_obj.exists():
            raise RuntimeError(f"{path} does not exist!")

        if not cls.group_exists(group):
            raise RuntimeError(f"{group} does not exist!")

        target = str(path_obj)

        # 删除已有文件/目录上的 ACL
        if recursive:
            cls._run(
                "setfacl",
                "-R",
                "-x",
                f"g:{group}",
                target,
            )
        else:
            cls._run(
                "setfacl",
                "-x",
                f"g:{group}",
                target,
            )

        # 删除目录的 default ACL
        if inherit:
            if not path_obj.is_dir():
                raise RuntimeError(
                    f"inherit=True requires a directory: {path}"
                )

            cls._run(
                "setfacl",
                "-d",
                "-x",
                f"g:{group}",
                target,
            )

    @classmethod
    def get_path_group(
        cls,
        path: str,
    ):
        path_obj = Path(path)

        if not path_obj.exists():
            raise RuntimeError(f"{path} does not exist!")

        target = str(path_obj)

        result = subprocess.run(
            ["getfacl", target],
            capture_output=True,
            text=True,
            check=True,
        )

        acl_info = result.stdout.strip()
        return acl_info