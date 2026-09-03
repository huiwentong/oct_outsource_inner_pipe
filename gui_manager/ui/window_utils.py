"""主窗口显示时的屏幕适配工具。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget

_MARGIN = 24  # 窗口与屏幕边缘保留的间距


def _best_screen(widget: QWidget) -> QScreen:
    """选择与窗口当前区域交集最大的屏幕，避免落到已断开/虚拟屏上。"""
    screens = QGuiApplication.screens()
    if not screens:
        raise RuntimeError("没有可用屏幕")
    if len(screens) == 1:
        return screens[0]

    frame = widget.frameGeometry()
    best, best_area = screens[0], -1
    for screen in screens:
        inter = screen.availableGeometry().intersected(frame)
        area = inter.width() * inter.height()
        if area > best_area:
            best, best_area = screen, area
    return best


def keep_window_on_screen(widget: QWidget) -> None:
    """把窗口限制在当前屏幕可见区域内并居中显示。

    在 showEvent 中首次显示时调用，处理窗口被系统放到屏幕外
    （例如上次显示在已断开的显示器）导致的“找不到 / 无边框”现象。
    """
    try:
        screen = _best_screen(widget)
    except RuntimeError:
        return

    avail: QRect = screen.availableGeometry()

    # 窗口大于可用区域时先缩小，保证标题栏和边框一定在屏幕内
    max_width = avail.width() - _MARGIN * 2
    max_height = avail.height() - _MARGIN * 2

    # 小屏幕 / 高缩放下，最小尺寸也可能超出屏幕，需要一并放宽
    min_width, min_height = widget.minimumWidth(), widget.minimumHeight()
    if min_width > max_width or min_height > max_height:
        widget.setMinimumSize(
            min(min_width, max_width),
            min(min_height, max_height),
        )

    if widget.width() > max_width or widget.height() > max_height:
        widget.resize(
            min(widget.width(), max_width),
            min(widget.height(), max_height),
        )

    frame = widget.frameGeometry()
    x = avail.left() + max((avail.width() - frame.width()) // 2, 0)
    y = avail.top() + max((avail.height() - frame.height()) // 2, 0)
    # 极端情况下仍保证窗口完全可见
    x = max(avail.left(), min(x, avail.right() - frame.width()))
    y = max(avail.top(), min(y, avail.bottom() - frame.height()))
    widget.move(QPoint(x, y))
