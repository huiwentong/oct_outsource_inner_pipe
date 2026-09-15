import requests
from typing import Optional, Any

def _request(method: str, path: str, **kwargs) -> Any:
    """向 permissionmanager 服务发起请求，失败时抛异常。"""
    url = f"http://vsftpd:8000{path}"
    resp = requests.request(method, url, timeout=30, **kwargs)
    resp.raise_for_status()
    if not resp.content:
        return None
    return resp.json()


def get_users(user_name: Optional[str] = None) -> list[dict[str, Any]]:
    params = {"user_name": user_name} if user_name else {}
    ret = _request("GET", "/get_user", params=params)
    return (ret or {}).get("users") or []