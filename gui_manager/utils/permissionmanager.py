from __future__ import annotations

from typing import Any, Optional

import requests

from utils.config import permissionmanager_base_url, server_config


def _request(method: str, path: str, **kwargs) -> Any:
    """向 permissionmanager 服务发起请求，失败时抛异常。"""
    url = f"{permissionmanager_base_url()}{path}"
    resp = requests.request(method, url, timeout=30, **kwargs)
    resp.raise_for_status()
    if not resp.content:
        return None
    return resp.json()


def get_users(user_name: Optional[str] = None) -> list[dict[str, Any]]:
    params = {"user_name": user_name} if user_name else {}
    ret = _request("GET", "/get_user", params=params)
    return (ret or {}).get("users") or []


def create_user(
    name: str,
    description: str,
    ding_id: str,
    email: str,
    password: Optional[str] = None,
) -> dict[str, Any]:
    """新增外包方用户（账号 / FTP 目录 / 通知信息）。"""
    return _request(
        "POST",
        "/create_user",
        json={
            "name": name,
            "description": description,
            "ding_id": ding_id,
            "email": email,
            "password": password,
        },
    )

def delete_user(name: str) -> Any:
    """删除外包方用户（账号 / FTP 目录 / 权限一并移除）。"""
    return _request("DELETE", f"/users/{name}")


def get_all_user() -> dict[str, Any]:
    """获取所有外包方用户，返回 /get_user 的完整响应：{"users": [...]}。"""
    return _request("GET", "/get_user")

def add_group2vendor(vender: str, groups: list[str]) -> dict[str, Any]:
    """把外包方用户 vender 追加到一组权限 group 中。"""
    return _request(
        "POST",
        "/add_u2g",
        json={"uname": vender, "gnames": groups},
    )


def get_user_groups(uname: str) -> list[str]:
    ret = _request("GET", "/user_groups", params={"uname": uname})
    return (ret or {}).get("usergroups") or []


if __name__ == "__main__":
    print(server_config())
