from ftplib import FTP
from pathlib import Path


def upload_dir(ftp: FTP, local_dir: Path, remote_dir: str):
    # 创建远程目录
    try:
        ftp.mkd(remote_dir)
    except Exception:
        # 目录可能已经存在
        pass

    for path in local_dir.iterdir():
        remote_path = f"{remote_dir}/{path.name}"

        if path.is_file():
            print(f"上传: {path} -> {remote_path}")

            with path.open("rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)

        elif path.is_dir():
            upload_dir(ftp, path, remote_path)


ftp = FTP("192.168.1.100")
ftp.login("oip_admin", "123456")

upload_dir(
    ftp,
    Path(r"D:\project\asset"),
    "/oct/mk2/asset",
)

ftp.quit()