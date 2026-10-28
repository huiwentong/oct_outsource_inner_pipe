"""collector 后台抓包 Worker：把长耗时的 start_collection 放到子线程执行。"""

from __future__ import annotations

import getpass
import io
import sys
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from components.core import StepComponent
from utils.db import Database
from utils.ftp import FtpClient
import traceback


class _LogStream(io.TextIOBase):
    """把 print 输出按行转发给 emit, 同时照常写到原来的终端。"""

    def __init__(self, emit, original):
        self._emit, self._original, self._buf = emit, original, ""

    def write(self, s: str) -> int:
        if self._original:
            self._original.write(s)
        self._buf += s
        *lines, self._buf = self._buf.split("\n")
        for line in lines:
            if line.strip():
                self._emit(line)
        return len(s)

    def flush(self) -> None:
        if self._original:
            self._original.flush()


@contextmanager
def _watch_uploads(on_start, on_done):
    """抓包期间包一层 FtpClient.upload_file: 开始处理时回调 on_start, 上传或跳过完成后回调 on_done。"""
    # ponytail: 临时替换类方法, 抓包期间全局生效; 只有本 worker 会上传, 结束即还原
    original = FtpClient.upload_file

    def wrapped(self, local_path, remote_path):
        on_start(str(remote_path))
        result = original(self, local_path, remote_path)  # 抛异常时不计入完成数
        on_done(str(remote_path))
        return result

    FtpClient.upload_file = wrapped
    try:
        yield
    finally:
        FtpClient.upload_file = original


def _count_files(components: list[StepComponent]) -> int:
    """统计要处理的文件总数, 清单里的目录会递归上传, 按目录内文件数计。"""
    total = 0
    for component in components:
        for src in component.transfer_folders:
            path = Path(src)
            total += sum(1 for f in path.rglob("*") if f.is_file()) if path.is_dir() else 1
    return total


class CollectWorker(QObject):
    """在子线程里顺序执行每项 component.start_collection 并写入抓包记录。"""

    progress = Signal(int, int, str)       # (当前第几项, 总项数, 当前任务描述)
    file_progress = Signal(int, int, str)  # (已完成文件数, 文件总数, "正在处理/已完成: FTP 路径")
    log = Signal(str)                      # 抓包过程中 print 的每一行
    completed = Signal(dict)               # 全部任务结束后的结果

    def __init__(
        self,
        components: list[StepComponent],
        vendor: str,
        db: Optional[Database] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._components = list(components)
        self._vendor = vendor
        self._db = db or Database()
        self._username = getpass.getuser()

    @Slot()
    def run(self) -> None:
        # 抓包期间 print 的内容同时显示在进度窗口里
        with redirect_stdout(_LogStream(self.log.emit, sys.stdout)):
            result = self._run()
            if result["error"]:
                print(result["error"])
        self.completed.emit(result)

    def _run(self) -> dict:
        total = len(self._components)
        done = 0
        error = ""
        files_total = files_done = 0

        def on_start(remote_path: str) -> None:  # 只更新当前文件, 不计数
            self.file_progress.emit(files_done, max(files_total, files_done), f"正在处理: {remote_path}")

        def on_done(remote_path: str) -> None:  # 上传成功或相同跳过后才计数
            nonlocal files_done
            files_done += 1
            self.file_progress.emit(files_done, max(files_total, files_done), f"已完成: {remote_path}")

        try:
            print("正在统计文件数…")
            files_total = _count_files(self._components)
            self.file_progress.emit(0, files_total, "")
            print(f"共 {total} 项任务, {files_total} 个文件")
            with _watch_uploads(on_start, on_done):
                for index, component in enumerate(self._components, start=1):
                    message = f"{component.entity} · {component.name}"
                    self.progress.emit(index, total, message)
                    print(f"===== ({index}/{total}) {message} =====")
                    try:
                        component.start_collection(self._vendor)
                        self._db.add_collection_history(
                            username=self._username,
                            vendorname=self._vendor,
                            asset=component.entity,
                            assettype=component.entity_type,
                            step=component.step,
                            description=component.description,
                            transformer_files=list(component.transfer_folders.keys()),
                            rely_groups=component.rely_assets + component.rely_steps + [component.project],
                        )
                    except Exception as exc:
                        error = f"第 {index}/{total} 项失败（{message}）：{exc} "+traceback.format_exc()
                        break
                    done += 1
        except Exception as exc:
            error = f"执行过程中发生错误：{exc} "+traceback.format_exc()

        return {"ok": not error, "done": done, "total": total, "error": error}
