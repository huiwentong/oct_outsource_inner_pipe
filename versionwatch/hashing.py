"""文件 hash 工具。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def hash_file(
    path: str | Path,
    algo: str = "blake2b",
    chunk_size: int = 1 << 20,
    max_bytes: int = 0,
) -> str | None:
    """计算文件摘要；``max_bytes > 0`` 且文件超过该大小时返回 None（跳过）。"""
    size = os.path.getsize(path)
    if max_bytes and size > max_bytes:
        return None

    if os.path.islink(path):
        # 跳过符号链接，避免循环引用
        return None
    if not os.path.isfile(path):
        # 跳过非普通文件（目录、FIFO、socket 等）
        return None
    
    digest = hashlib.new(algo)
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()