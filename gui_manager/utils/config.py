from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# server_config.yml 固定在 gui_manager 目录下（与 utils/config.py 同级目录的父级）
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "server_config.yml"


def get_config(path: str | Path | None = None) -> dict[str, Any]:
    """读取服务器基础配置 server_config.yml。

    后续如需支持环境变量覆盖，可以在此处追加 merge 逻辑。
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    return config


# 模块级缓存配置，避免每次调用都重新读取文件
_config: dict[str, Any] | None = None


def server_config() -> dict[str, Any]:
    global _config
    if _config is None:
        _config = get_config()
    return _config


def permissionmanager_base_url() -> str:
    """permissionmanager 服务的基础地址。"""
    cfg = server_config()
    host = cfg.get("server_ip", "127.0.0.1")
    port = cfg.get("permissionmanager_port", 8000)
    return f"http://{host}:{port}"
