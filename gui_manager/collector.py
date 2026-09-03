"""collector 启动入口: python collector.py"""

from PySide6.QtWidgets import QApplication

from ui.collector import CollectorWindow
from ui.style import apply_style


def main() -> None:
    app = QApplication([])
    apply_style(app)

    window = CollectorWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
