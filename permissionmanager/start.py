import os
import pwd
import subprocess
from pathlib import Path
import psycopg2
from permissionmanager.core.user_manager import Database, FTPUserManager


def user_exists(username: str) -> bool:
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False


def create_ftp_user(
    username: str,
    password: str,
    home: str = "/srv/ftp",
):
    if not user_exists(username):
        subprocess.run(
            [
                "useradd",
                "-m",
                "-d", home,
                "-s", "/bin/bash",
                username,
            ],
            check=True,
        )

        # 设置密码
        subprocess.run(
            ["chpasswd"],
            input=f"{username}:{password}\n",
            text=True,
            check=True,
        )

    # 创建 FTP 目录
    ftp_dir = Path(home)
    ftp_dir.mkdir(parents=True, exist_ok=True)

    # chown -R username:username /srv/ftp
    subprocess.run(
        [
            "chown",
            "-R",
            f"{username}:{username}",
            str(ftp_dir),
        ],
        check=True,
    )

    # chmod -R u+rwX /srv/ftp
    subprocess.run(
        [
            "chmod",
            "-R",
            "u+rwX",
            str(ftp_dir),
        ],
        check=True,
    )


def prepare_vsftpd_log():
    log_dir = Path("/var/log/vsftpd")
    log_file = log_dir / "vsftpd.log"

    # mkdir -p /var/log/vsftpd
    log_dir.mkdir(parents=True, exist_ok=True)

    # touch /var/log/vsftpd/vsftpd.log
    log_file.touch(exist_ok=True)

    # chmod 666 /var/log/vsftpd/vsftpd.log
    os.chmod(log_file, 0o666)



def fill_by_db():
    db = Database()
    users = db.get_users()
    for user in users:
        print(f'create user {user["name"]}')
        FTPUserManager.create_user(
            username=user['name'],
            password=user['password'],
            home=user['home'],
            ding=user['dingtalk_id'],
            email=user['email'],
            description=user['description'],
            db=False
        )
    groups = db.get_groups()
    for group in groups:
        print(f'create group {group["name"]}')
        FTPUserManager.create_group(
            groupname=group['name'],
            description=group['description'],
            db=False
        )


def start():
    create_ftp_user(
        username="oip_admin",
        password="123456",
    )
    prepare_vsftpd_log()
    fill_by_db()