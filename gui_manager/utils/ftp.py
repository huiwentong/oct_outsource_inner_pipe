from __future__ import annotations

from pathlib import Path
from typing import Optional

from ftplib import FTP, error_perm

from utils.config import server_config


def _split_remote_dir(remote_dir: str) -> list[str]:
    """把远程路径拆成逐级目录列表，便于逐层创建。"""
    parts = remote_dir.replace("\\", "/").split("/")
    return [p for p in parts if p]


class FtpClient:
    """读取 server_config.yml 连接 FTP 的通用封装。

    用法::

        with FtpClient() as ftp:
            upload_dir(ftp, Path(r"D:/project/asset"), "/oct/mk2/asset")

    后续需要更多操作（下载、删除、重命名等）时直接扩展此类即可。
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        cfg = server_config()
        self.host = host or cfg.get("server_ip", "127.0.0.1")
        self.port = port or int(cfg.get("ftp_port", 21))
        self.user = user or cfg.get("ftp_user", "")
        self.password = password or cfg.get("ftp_pass", "")

    def connect(self) -> FTP:
        ftp = FTP()
        ftp.connect(self.host, self.port, timeout=30)
        ftp.login(self.user, self.password)
        return ftp

    def __enter__(self) -> FTP:
        self._ftp = self.connect()
        return self._ftp

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            self._ftp.quit()
        except Exception:
            self._ftp.close()

    @staticmethod
    def ensure_remote_dir(ftp: FTP, remote_dir: str) -> None:
        """逐级创建远程目录（目录已存在时不报错）。"""
        current = ""
        for part in _split_remote_dir(remote_dir):
            current = f"{current}/{part}"
            try:
                ftp.mkd(current)
            except error_perm:
                pass  # 目录已存在

    def upload_file(self, ftp: FTP, local_path: Path, remote_path: str) -> None:
        with Path(local_path).open("rb") as fh:
            ftp.storbinary(f"STOR {remote_path}", fh)

    def upload_dir(self, ftp: FTP, local_dir: Path, remote_dir: str) -> None:
        """递归上传本地目录到远程目录。"""
        self.ensure_remote_dir(ftp, remote_dir)
        local_dir = Path(local_dir)

        for path in local_dir.iterdir():
            remote_path = f"{remote_dir}/{path.name}"

            if path.is_file():
                print(f"上传: {path} -> {remote_path}")
                self.upload_file(ftp, path, remote_path)

            elif path.is_dir():
                self.upload_dir(ftp, path, remote_path)


if __name__ == "__main__":
    print("FTP 上传工具。请在自己的代码中调用 FtpClient，例如：")
    print("    from utils.ftp import FtpClient")
    print("    with FtpClient() as ftp:")
    print("        ftp.upload_dir(ftp, Path(r'D:/data'), '/oct/mk2/asset')")
