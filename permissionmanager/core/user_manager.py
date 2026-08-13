import subprocess
import pwd
import grp
from datetime import datetime
import os
from typing import Optional
from psycopg2.extras import RealDictCursor
import psycopg2
import requests
import json
import smtplib
from email.mime.text import MIMEText
from logger.core import get_log



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
    ):
        sql = """
            INSERT INTO ftpuser (
                name,
                description,
                dingtalk_id,
                email,
                password,
                home
            )
            VALUES (%s, %s, %s, %s, %s, %s)
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
                        home
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
                created_at,
                updated_at
            FROM ftpuser
            ORDER BY id;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
                return cursor.fetchall()


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

    def create_groups(self, name, description):
        sql = """
            INSERT INTO permission_group (
                name,
                description
            )
            VALUES (%s, %s)
            RETURNING *;
        """

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    sql,
                    (
                        name,
                        description,
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
        uid = user[0]["id"]

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for group_name in group_names:
                    group = self.get_group_by_name(group_name)
                    if not group:
                        raise ValueError(f"权限组不存在: {group_name}")
                    gid = group[0]["id"]
                    cursor.execute(
                        """
                        INSERT INTO user_permission_group (
                            uid,
                            gid
                        )
                        VALUES (%s, %s)
                        ON CONFLICT (uid, gid)
                        DO NOTHING;
                        """,
                        (uid, gid),
                    )
            conn.commit()



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
    def create_user(cls, username, password, home, ding, email, description, db=True):
        if FTPUserManager.user_exists(username):
            return cls.get_user(username)[0]

        user = {}
        if db:
            user = cls.db.create_user(username,description=description,dingtalk_id=ding,email=email,password=password, home=home)

        cmd = [
            "useradd",
            "-m",
            "-s", "/bin/bash",
        ]

        if home:
            cmd.extend(["-d", home])

        cmd.append(username)

        # 创建 Linux 用户
        subprocess.run(cmd, check=True)

        # 设置 FTP 登录密码
        subprocess.run(
            ["chpasswd"],
            input=f"{username}:{password}\n",
            text=True,
            check=True,
        )
        if home:
            subprocess.run(
                ["chown", f"{username}:oip_admin", home],
                check=True,
            )

            subprocess.run(
                ["chmod", "750", home],
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


    @classmethod
    def create_group(cls, groupname, description, db=True):
        if FTPUserManager.group_exists(groupname):
            return cls.get_group(groupname=groupname)[0]

        ret_g = {}
        if db:
            ret_g = cls.db.create_groups(groupname, description)
        subprocess.run(
            ["groupadd", groupname],
            check=True
        )
        if ret_g:
            return ret_g

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
            users.append(user)
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
            groups.append(group)

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