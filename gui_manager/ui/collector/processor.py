"""collector 抓包执行进度弹窗（processor widget）, 以及开始抓包前的确认框。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


def confirm_collect(parent, project: str, vendor: str, components: list) -> bool:
    """开始抓包前确认外包方、任务和将授权的组, 返回是否继续。"""
    tasks: dict[tuple[str, str], list[str]] = {}
    assets, steps = set(), set()
    for c in components:
        tasks.setdefault((c.entity, c.entity_type), []).append(c.name)
        assets.update(c.rely_assets)
        steps.update(c.rely_steps)

    lines = [f"项目: {project}", "", f"任务 ({len(components)} 项):"]
    lines += [f"  {entity} ({etype}): {'、'.join(names)}" for (entity, etype), names in tasks.items()]
    lines += [
        "",
        f"本次将授权的组 ({1 + len(assets) + len(steps)} 个):",
        f"  项目: {project}",
        f"  实体 ({len(assets)}): {', '.join(sorted(assets))}",
        f"  环节 ({len(steps)}): {', '.join(sorted(steps))}",
    ]

    dialog = QDialog(parent)
    dialog.setWindowTitle("确认开始抓包")
    dialog.resize(720, 520)

    vendor_label = QLabel(f"外包方 (FTP 账号): <span style='font-size:20px;color:#b91c1c;'><b>{vendor}</b></span>")
    hint = QLabel("外包方会被加入下面列出的组, 获得对应目录的读取权限; 组只增不减, 选错外包方需要手动撤销。请确认无误再开始。")
    hint.setObjectName("muted")
    hint.setWordWrap(True)

    detail = QPlainTextEdit("\n".join(lines))
    detail.setReadOnly(True)

    buttons = QDialogButtonBox()
    ok_btn = buttons.addButton("确认开始抓包", QDialogButtonBox.ButtonRole.AcceptRole)
    cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
    ok_btn.setObjectName("primary")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    # 回车默认取消, 避免误触直接开始. 按钮盒显示时会把第一个 AcceptRole 且 autoDefault 的按钮设为默认,
    # 所以要先关掉确认按钮的 autoDefault, 否则 setDefault(cancel) 会被覆盖
    ok_btn.setAutoDefault(False)
    cancel_btn.setDefault(True)

    layout = QVBoxLayout(dialog)
    layout.addWidget(vendor_label)
    layout.addWidget(hint)
    layout.addWidget(detail, 1)
    layout.addWidget(buttons)
    return dialog.exec() == QDialog.DialogCode.Accepted


class Processor(QDialog):
    """实时显示抓包进度的弹窗: 任务进度、文件进度、过程日志。

    全部任务结束后由外部调用 mark_finished(), 窗口保留以便查看日志, 由用户手动关闭。
    """

    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self._finished = False

        self.setWindowTitle("抓包进度")
        self.setModal(True)
        self.resize(860, 560)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self.title = QLabel("正在执行抓包任务")
        self.title.setObjectName("appTitle")

        self.task_label = QLabel("准备中…")
        self.task_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("任务 %v / %m 项")
        self.progress_bar.setTextVisible(True)

        # 路径可能很长: 标签不参与宽度计算, 超出时省略中间部分, 完整路径放在悬停提示里
        self.file_label = QLabel()
        self.file_label.setObjectName("muted")
        self.file_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._file_text = "正在统计文件数…"

        self.file_bar = QProgressBar()
        self.file_bar.setRange(0, 0)  # 统计完文件数之前显示为忙碌状态
        self.file_bar.setFormat("文件 %v / %m")
        self.file_bar.setTextVisible(True)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.log_view.setMaximumBlockCount(5000)  # 只保留最近 5000 行, 避免大场景占用过多内存

        self.hint = QLabel("请耐心等待所有任务执行完成，期间请不要关闭窗口。")
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(self.title)
        layout.addWidget(self.task_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.file_label)
        layout.addWidget(self.file_bar)
        layout.addWidget(self.log_view, 1)
        layout.addWidget(self.hint)
        layout.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignRight)

    @Slot(int, int, str)
    def set_progress(self, index: int, total: int, message: str) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(index)
        self.task_label.setText(f"({index}/{total}) {message}")

    @Slot(int, int, str)
    def set_file_progress(self, index: int, total: int, remote_path: str) -> None:
        self.file_bar.setMaximum(total)
        self.file_bar.setValue(index)
        self._file_text = remote_path or f"共 {total} 个文件"
        self._elide_file_label()

    def _elide_file_label(self) -> None:
        metrics = self.file_label.fontMetrics()
        self.file_label.setText(metrics.elidedText(self._file_text, Qt.TextElideMode.ElideMiddle, self.file_label.width()))
        self.file_label.setToolTip(self._file_text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide_file_label()  # 拖动窗口宽度后按新宽度重新省略

    @Slot(str)
    def append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def mark_finished(self, ok: bool = True) -> None:
        """结束后不自动关闭, 保留日志供查看。"""
        self._finished = True
        self.title.setText("抓包完成" if ok else "抓包失败")
        self.hint.setText("可以在上方查看完整过程日志，确认无误后关闭窗口。")
        self.close_btn.setEnabled(True)
        self.close_btn.setFocus()
        # 不在这里改窗口标志: 对已显示的窗口改标志会重建窗口, 导致空白并把随后的提示框压在下面

    def reject(self) -> None:
        # 抓包过程中不允许通过 Esc / 关闭按钮提前关闭弹窗
        if self._finished:
            super().reject()

    def closeEvent(self, event) -> None:
        if not self._finished:
            event.ignore()
            return
        super().closeEvent(event)
