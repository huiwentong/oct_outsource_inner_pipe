"""两个 GUI 共用的现代化 QSS 样式。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

STYLESHEET = """
QMainWindow {
    background: #eef2f7;
}
QWidget {
    color: #1e293b;
    font-size: 13px;
}
QLabel {
    background: transparent;
}

/* 卡片 */
QFrame#card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}
QFrame#rowCard {
    background: #f8fafc;
    border: 1px solid #e6ebf3;
    border-radius: 10px;
}
QLabel#cardTitle {
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
    background: transparent;
}
QLabel#cardSub {
    font-size: 12px;
    color: #94a3b8;
    background: transparent;
}
QLabel#muted {
    color: #64748b;
    font-size: 12px;
    background: transparent;
}
QLabel#danger {
    color: #e11d48;
    font-size: 12px;
    background: transparent;
}
QLabel#rowEntity {
    font-weight: 600;
    color: #0f172a;
    font-size: 13px;
    background: transparent;
}
QLabel#rowPath {
    color: #94a3b8;
    font-size: 12px;
    background: transparent;
}
QLabel#appTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    background: transparent;
}
QLabel#appSub {
    font-size: 12px;
    color: #64748b;
    background: transparent;
}
QLabel#emptyState {
    font-size: 14px;
    color: #94a3b8;
    background: transparent;
}

/* 通用按钮 */
QPushButton {
    background: #e2e8f0;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
    color: #334155;
}
QPushButton:hover { background: #cbd5e1; }
QPushButton:pressed { background: #94a3b8; }
QPushButton:disabled { background: #f1f5f9; color: #a8b3c4; }

QPushButton#primary {
    background: #3b82f6;
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 28px;
    border-radius: 10px;
}
QPushButton#primary:hover { background: #2f6fe0; }
QPushButton#primary:pressed { background: #2a62c8; }
QPushButton#primary:disabled { background: #c7dcfb; color: #eef5ff; }

QPushButton#danger {
    background: #ef4444;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 8px;
}
QPushButton#danger:hover { background: #dc2626; }
QPushButton#danger:pressed { background: #b91c1c; }
QPushButton#danger:disabled { background: #fecaca; color: #fee2e2; }

QPushButton#ghost {
    background: transparent;
    border: 1px solid #dbe2ec;
    color: #475569;
}
QPushButton#ghost:hover { background: #f1f5f9; border-color: #c3cede; }

QPushButton#projectToggle {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 22px;
    color: #475569;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#projectToggle:hover { border-color: #3b82f6; color: #3b82f6; }
QPushButton#projectToggle:checked {
    background: #3b82f6;
    border-color: #3b82f6;
    color: #ffffff;
}

/* 输入控件 */
QLineEdit, QComboBox, QTextEdit, QSpinBox {
    background: #f8fafc;
    border: 1px solid #dbe2ec;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: #bfdbfe;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus {
    border-color: #3b82f6;
    background: #ffffff;
}
QLineEdit:disabled, QComboBox:disabled { background: #f1f5f9; color: #a8b3c4; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    margin-right: 8px;
}

/* 下拉弹层（与主体浅色风格统一，避免默认黑底） */
QComboBox QFrame {
    background-color: #ffffff;
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #dbe2ec;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #dbeafe;
    selection-color: #1d4ed8;
}
QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 2px 8px;
    color: #1e293b;
    background: transparent;
}
QComboBox QAbstractItemView::item:hover {
    background: #f1f5f9;
    color: #1e293b;
}
QComboBox QAbstractItemView::item:selected {
    background: #dbeafe;
    color: #1d4ed8;
}

/* 列表 */
QListWidget {
    background: #f8fafc;
    border: 1px solid #dbe2ec;
    border-radius: 10px;
    padding: 4px;
    outline: none;
}
QListWidget::item { padding: 5px 6px; border-radius: 6px; }
QListWidget::item:hover { background: #eef2f7; }
QListWidget::item:selected { background: #dbeafe; color: #1d4ed8; }

/* 滚动区域 */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }

QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QToolTip {
    background: #0f172a;
    color: #f8fafc;
    border: none;
    padding: 6px 8px;
    border-radius: 6px;
}
"""


def apply_style(app: QApplication) -> None:
    app.setStyle("Fusion")

    # 强制浅色调色板：QSS 覆盖不到的部件（如下拉弹层外框、阴影区域等）
    # 会读取系统调色板，系统为深色模式时这些区域会变成难看的黑框。
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#ffffff"))
    palette.setColor(QPalette.WindowText, QColor("#1e293b"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f8fafc"))
    palette.setColor(QPalette.Text, QColor("#1e293b"))
    palette.setColor(QPalette.Button, QColor("#e2e8f0"))
    palette.setColor(QPalette.ButtonText, QColor("#1e293b"))
    palette.setColor(QPalette.Light, QColor("#f8fafc"))
    palette.setColor(QPalette.Midlight, QColor("#e2e8f0"))
    palette.setColor(QPalette.Mid, QColor("#cbd5e1"))
    palette.setColor(QPalette.Dark, QColor("#94a3b8"))
    palette.setColor(QPalette.Shadow, QColor("#64748b"))
    palette.setColor(QPalette.Highlight, QColor("#3b82f6"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor("#0f172a"))
    palette.setColor(QPalette.ToolTipText, QColor("#f8fafc"))
    palette.setColor(QPalette.PlaceholderText, QColor("#94a3b8"))
    app.setPalette(palette)

    app.setStyleSheet(STYLESHEET)
