"""collector 抓包执行进度弹窗（processor widget）。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)


class Processor(QDialog):
    """实时显示抓包进度的弹窗，全部任务结束后由外部调用 mark_finished() 关闭。"""

    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self._finished = False

        self.setWindowTitle("抓包进度")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        title = QLabel("正在执行抓包任务")
        title.setObjectName("appTitle")

        self.task_label = QLabel("准备中…")
        self.task_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v / %m 项")
        self.progress_bar.setTextVisible(True)

        hint = QLabel("请耐心等待所有任务执行完成，期间请不要关闭窗口。")
        hint.setObjectName("muted")
        hint.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self.task_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(hint)

    @Slot(int, int, str)
    def set_progress(self, index: int, total: int, message: str) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(index)
        self.task_label.setText(f"({index}/{total}) {message}")

    def mark_finished(self) -> None:
        self._finished = True
        self.accept()

    def reject(self) -> None:
        # 抓包过程中不允许通过 Esc / 关闭按钮提前关闭弹窗
        if self._finished:
            super().reject()

    def closeEvent(self, event) -> None:
        if not self._finished:
            event.ignore()
            return
        super().closeEvent(event)
