"""collector 后台抓包 Worker：把长耗时的 start_collection 放到子线程执行。"""

from __future__ import annotations

import getpass
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from components.core import StepComponent
from utils.db import Database
import traceback


class CollectWorker(QObject):
    """在子线程里顺序执行每项 component.start_collection 并写入抓包记录。"""

    progress = Signal(int, int, str)  # (当前第几项, 总项数, 当前任务描述)
    completed = Signal(dict)          # 全部任务结束后的结果

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
        total = len(self._components)
        done = 0
        error = ""

        try:
            for index, component in enumerate(self._components, start=1):
                message = f"{component.entity} · {component.name}"
                self.progress.emit(index, total, message)
                try:
                    component.start_collection(self._vendor)
                    self._db.add_collection_history(
                        username=self._username,
                        vendorname=self._vendor,
                        asset=component.entity,
                        assettype=component.entity_type,
                        step=component.step,
                        description=component.description,
                        transformer_files=component.transfer_folders,
                        rely_groups=component.rely_assets + component.rely_steps,
                    )
                except Exception as exc:
                    error = f"第 {index}/{total} 项失败（{message}）：{exc} "+traceback.format_exc()
                    break
                done += 1
        except Exception as exc:
            error = f"执行过程中发生错误：{exc}"

        self.completed.emit(
            {
                "ok": not error,
                "done": done,
                "total": total,
                "error": error,
            }
        )
