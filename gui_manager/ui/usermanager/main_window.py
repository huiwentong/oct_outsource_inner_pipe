"""usermanager GUI 主窗口。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.usermanager import services
from ui.window_utils import keep_window_on_screen

# (字段key, 显示名, 是否必填, 输入提示, 详细说明)
FIELD_SPECS: list[tuple[str, str, bool, str, str]] = [
    (
        "name",
        "用户名 name",
        True,
        "例如：starlight_cg",
        "外包方登录名：用于登录 FTP 与系统，创建后不可修改。",
    ),
    (
        "description",
        "描述 description",
        True,
        "例如：星火数码 / 负责模型环节",
        "用途说明：方便区分该外包方，可填写公司全称、合作业务等。",
    ),
    (
        "ding_id",
        "钉钉 ID ding_id",
        True,
        "请输入钉钉用户 ID",
        "用途：创建后系统通过钉钉给该外包方发送通知消息。",
    ),
    (
        "email",
        "邮箱 email",
        True,
        "name@company.com",
        "用途：用于接收账号密码、系统通知等重要信息。",
    ),
    (
        "password",
        "密码 password",
        False,
        "留空则系统自动生成随机密码",
        "选填：如果不填写此信息，系统会随机生成 password。",
    ),
]


class UserManagerWindow(QMainWindow):
    """外包方用户管理工具主窗口。"""

    def __init__(self):
        super().__init__()
        self._perm_checked = False
        self._executing = False
        self._placed_once = False
        self._inputs: dict[str, QLineEdit] = {}

        self.setWindowTitle("UserManager · 外包方用户管理")
        self.resize(860, 780)
        self.setMinimumSize(720, 660)

        self._build_ui()
        self._refresh_state()

    # ---------- UI ----------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("UserManager")
        title.setObjectName("appTitle")
        sub = QLabel("外包方用户管理 · 在数据库与 FTP 中新增外包方账号并设置权限")
        sub.setObjectName("appSub")
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(title)
        head.addWidget(sub)
        root.addLayout(head)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        intro = QLabel(
            "填写以下信息后点击「执行创建」，系统会在数据库 / FTP 中新增外包方账号。\n"
            "带 * 为必填项；密码不填时由系统自动生成。"
        )
        intro.setWordWrap(True)
        card_layout.addWidget(intro)

        for key, label, required, placeholder, help_text in FIELD_SPECS:
            card_layout.addWidget(self._build_field(key, label, required, placeholder, help_text))

        self.status_label = QLabel("")
        self.status_label.setObjectName("danger")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)

        reset_btn = QPushButton("重置")
        reset_btn.setObjectName("ghost")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_form)

        self.execute_btn = QPushButton("执行创建")
        self.execute_btn.setObjectName("primary")
        self.execute_btn.setCursor(Qt.PointingHandCursor)
        self.execute_btn.clicked.connect(self._on_execute_clicked)

        buttons.addWidget(reset_btn)
        buttons.addWidget(self.execute_btn)
        card_layout.addLayout(buttons)

        root.addWidget(card)
        root.addStretch(1)
        self.setCentralWidget(central)

    def _build_field(
        self,
        key: str,
        label: str,
        required: bool,
        placeholder: str,
        help_text: str,
    ) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        name_label = QLabel(label + (" *" if required else ""))
        name_label.setObjectName("cardTitle")
        if not required:
            name_label.setStyleSheet("color:#475569;")
        layout.addWidget(name_label)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setClearButtonEnabled(True)
        if key == "password":
            edit.setEchoMode(QLineEdit.Password)
        edit.textChanged.connect(self._refresh_state)
        self._inputs[key] = edit
        layout.addWidget(edit)

        help_label = QLabel(help_text)
        help_label.setObjectName("muted")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        return wrap

    # ---------- 状态与校验 ----------

    def _errors(self) -> list[str]:
        errors = []
        required_keys = {spec[0] for spec in FIELD_SPECS if spec[2]}
        for key in sorted(required_keys):
            value = self._inputs[key].text().strip()
            if not value:
                errors.append(f"请填写必填项：{key}")
        email = self._inputs["email"].text().strip()
        if email and "@" not in email:
            errors.append("邮箱格式不正确，请检查 email")
        return errors

    def _refresh_state(self) -> None:
        if self._executing:
            return

        errors = self._errors()
        self.status_label.setText(errors[0] if errors else "")
        # 执行按钮：必填信息齐全且无格式错误时可用
        self.execute_btn.setEnabled(not errors)

    def _reset_form(self) -> None:
        for edit in self._inputs.values():
            edit.clear()
        self.status_label.setText("")
        self._refresh_state()
        self._inputs["name"].setFocus()

    # ---------- 权限校验（打开后自动执行） ----------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._placed_once:
            self._placed_once = True
            # 确保窗口带边框并完整落在当前屏幕内
            QTimer.singleShot(0, lambda: keep_window_on_screen(self))
        if not self._perm_checked:
            self._perm_checked = True
            QTimer.singleShot(0, self._check_permission)

    def _check_permission(self) -> None:
        if not services.check_permission():
            QMessageBox.warning(
                self,
                "无权限",
                "当前使用者没有运行本工具的权限，工具即将自动关闭。",
            )
            self.close()
            QTimer.singleShot(0, QApplication.instance().quit)

    # ---------- 执行创建 ----------

    def _gather_data(self) -> dict:
        data = {
            key: edit.text().strip()
            for key, edit in self._inputs.items()
        }
        if not data.get("password"):
            data["password"] = None
        return data

    def _on_execute_clicked(self) -> None:
        errors = self._errors()
        if errors:
            self.status_label.setText(errors[0])
            QMessageBox.warning(self, "信息不完整", errors[0])
            return

        data = self._gather_data()
        self._executing = True
        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("正在执行…")
        self.status_label.setText("正在创建外包方用户，请稍候…")

        # mock：模拟数据库 / FTP 的执行与反馈耗时
        QTimer.singleShot(900, lambda: self._finish_execute(data))

    def _finish_execute(self, data: dict) -> None:
        try:
            ok, message, result = services.create_vendor_user(data)
        except Exception as exc:  # 真实逻辑中连接错误等
            ok, message, result = False, f"执行出错：{exc}", {}

        self._executing = False
        self.execute_btn.setText("执行创建")

        if ok:
            self.status_label.setText("")
            QMessageBox.information(
                self,
                "创建成功",
                f"外包方用户「{result.get('username', '')}」已创建成功。\n"
                f"{message}",
            )
            self._reset_form()
            # 预留：创建成功后的后续动作（发送通知、开通权限等）
            services.continue_after_success(result)
        else:
            # 失败：保留当前输入状态，方便修改后重试
            self.status_label.setText(message)
            QMessageBox.critical(self, "创建失败", message)
            self._refresh_state()
