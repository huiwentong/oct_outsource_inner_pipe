"""usermanager 启动入口: python usermanager.py"""

from PySide6.QtWidgets import QApplication

from ui.style import apply_style
from ui.usermanager import UserManagerWindow


def main() -> None:
    app = QApplication([])
    apply_style(app)

    window = UserManagerWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
