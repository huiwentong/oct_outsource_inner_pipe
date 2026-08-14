import os
import pwd
import subprocess
from pathlib import Path
import psycopg2
from permissionmanager.core.user_manager import Database, FTPUserManager
from logger.core import get_log
import traceback

logger = get_log("permissionmanager")

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
    groups = db.get_groups()
    for group in groups:
        logger.info(f'create group {group["name"]}')
        FTPUserManager.create_group(
            groupname=group['name'],
            description=group['description'],
            db=False
        )


    for user in users:
        logger.info(f'create user {user["name"]}')
        FTPUserManager.create_user(
            username=user['name'],
            password=user['password'],
            home=user['home'],
            ding=user['dingtalk_id'],
            email=user['email'],
            description=user['description'],
            db=False
        )
        
        user_groups = db.get_user_groups(user['name'])
        g_names = [g['group_name'] for g in user_groups]
        FTPUserManager.set_user_group(
            username=user['name'],
            groupnames=g_names,
            db=False
        )

        all_groups = [g['name'] for g in db.get_groups()]
        FTPUserManager.set_user_group(
            username='oip_admin',
            groupnames=all_groups,
            db=False
        )
    

def refresh_file_acs():
    if not os.path.exists('/srv/ftp/oct'):
        return
    
    subprocess.run(
        [
            'setfacl',
            '-m',
            'd:u::rwx,d:g::rwx,d:o::--x',
            '/srv/ftp/oct'
        ],
        check=True,
    )
    base = Path("/srv/ftp/oct")

    for root, dirs, files in os.walk(base):
        path = Path(root)
        parts = path.relative_to(base).parts

        if len(parts) == 1:
            project = parts[0]
            if not FTPUserManager.group_exists(project):
                FTPUserManager.create_group(project, 'auto create')
            subprocess.run(
                [
                    'setfacl',
                    '-m',
                    f'g:{project}:r-x',
                    str(path)
                ],
                check=True,
            )
        elif len(parts) == 2:
            type_ = parts[1]
            project = parts[0]
            if not FTPUserManager.group_exists(project):
                FTPUserManager.create_group(project, 'auto create')
            subprocess.run(
                [
                    'setfacl',
                    '-m',
                    f'g:{project}:r-x',
                    str(path)
                ],
                check=True,
            )
        elif len(parts) == 3:
            entity = parts[2]
            if not FTPUserManager.group_exists(entity):
                FTPUserManager.create_group(entity, 'auto create')
            subprocess.run(
                [
                    'setfacl',
                    '-m',
                    f'g:{entity}:r-x',
                    str(path)
                ],
                check=True,
            )
        elif len(parts) == 4:
            step = parts[3]
            if not FTPUserManager.group_exists(step):
                FTPUserManager.create_group(step, 'auto create')
            subprocess.run(
                [
                    'setfacl',
                    '-m',
                    f'g:{step}:r-x',
                    str(path)
                ],
                check=True,
            )
            subprocess.run(
                [
                    'setfacl',
                    '-d',
                    '-m',
                    f'g:{step}:r-x',
                    str(path)
                ],
                check=True,
            )
        else:
            continue



def start():
    create_ftp_user(
        username="oip_admin",
        password="123456",
    )
    prepare_vsftpd_log()
    logger.info("Starting sync ftp users and groups...")
    try:
        fill_by_db()
        refresh_file_acs()
    except Exception as e:
        logger.error(traceback)
        raise RuntimeError(e)