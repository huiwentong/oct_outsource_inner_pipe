"""usermanager 的 mock 服务层。

TODO(后续补充): 以下为演示用的 mock 逻辑，
     后续把 *check_permission* / *create_vendor_user* 替换为真实
     的权限校验与数据库 / FTP / 权限服务调用。
"""

from __future__ import annotations

from typing import Any
import getpass
from utils.permissionmanager import (
    create_user,
    delete_user as pm_delete_user,
    get_all_user as pm_get_all_user,
)
from utils.config import server_config
import traceback

# mock 开关：当前默认拥有权限。改为 False 可演示“无权限自动关闭”。
MOCK_HAVE_PERMISSION = True


def check_permission() -> bool:
    """校验当前使用者是否有权运行本工具。

    TODO(后续补充): 替换为真实逻辑，例如：
     1. 读取当前系统用户名 / 域名 / IP 等信息；
     2. 调用权限服务接口，判断是否有权限。
    """
    print(getpass.getuser())
    if getpass.getuser() not in ['huiwentong', 'fengan']:
        return False

    return MOCK_HAVE_PERMISSION


def create_vendor_user(data: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """在数据库 / FTP 中新增外包方用户，返回 (是否成功, 提示信息, 返回数据)。

    TODO(后续补充): 替换为真实逻辑：写入数据库并创建 FTP 账号 /
     权限组、发送通知等。
    """
    username = data.get("name", "")
    password = data.get("password", None)

    # mock：模拟等待服务器执行反馈
    print(f"[mock] 正在创建外包方用户: {username} ...")
    print(f"[mock] description={data.get('description')!r} "
          f"ding_id={data.get('ding_id')!r} email={data.get('email')!r}")

    try:
        ret = create_user(
            name=username,
            description=data.get('description'),
            ding_id=data.get('ding_id'),
            email=data.get('email'),
            password=data.get('password')
        )

        if ret.get('message') == 'User created succussfuly':
            password = ret.get('userpswd')
            uid = ret.get('userid')
        else:
            return False, "创建失败！", ret
            
        c = server_config()
        return True, "创建成功", {
            "username": username,
            "user_id": uid,
            "password": password,
            "frp_address": c['server_ip'],
            "frp_port": c['ftp_port'],
            "frp_home": f"/srv/ftp/{username}",
        }
    except:
        traceback.print_exc()
        return False, "创建失败！", {'traceback': traceback.format_exc()}


def fetch_all_users() -> list[dict[str, Any]]:
    """获取所有外包方人员，供删除面板展示。

    数据源：utils.permissionmanager.get_all_user()（GET /get_user）。
    """
    ret = pm_get_all_user()
    if not isinstance(ret, dict):
        return []
    return ret.get("users") or []


def delete_vendor_user(name: str) -> tuple[bool, str]:
    """删除指定外包方用户。

    数据源：utils.permissionmanager.delete_user()（DELETE /users/{name}）。
    """
    try:
        pm_delete_user(name)
        return True, f"外包方用户「{name}」已删除"
    except Exception as exc:
        return False, f"删除失败：{exc}"


def continue_after_success(user: dict[str, Any]) -> None:
    """执行成功后的后续动作（预留）。

    TODO(后续补充): 例如给外包方发送账号 / 密码通知、开通目录权限等。
    """
    print(f"[mock] 创建成功后的后续动作已触发: {user.get('username')}")
