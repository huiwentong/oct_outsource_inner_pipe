"""gui_manager 共用控件。"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox

# 下拉弹层容器样式：容器是独立的顶层窗口，全局 QSS 的
# “QComboBox QFrame” 匹配不到它，因此需要在弹出时直接套用。
_POPUP_STYLE = """
QFrame {
    background-color: #ffffff;
    border: 1px solid #dbe2ec;
    border-radius: 8px;
}
"""


class PopupStyledComboBox(QComboBox):
    """弹出列表带浅色边框/背景的 QComboBox，避免系统深色模式下出现黑框。"""

    def showPopup(self) -> None:
        super().showPopup()
        popup = self.view().window()
        if popup is not self and not popup.property("_popup_styled"):
            popup.setStyleSheet(_POPUP_STYLE)
            popup.setProperty("_popup_styled", True)
            popup.update()
