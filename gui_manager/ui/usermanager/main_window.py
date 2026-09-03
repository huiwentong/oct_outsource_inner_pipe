"""usermanager GUI 主窗口。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
        self._loading_users = False
        self._deleting_user = False
        self._inputs: dict[str, QLineEdit] = {}

        self.setWindowTitle("UserManager · 外包方用户管理")
        self.resize(880, 880)
        self.setMinimumSize(720, 600)

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
        sub = QLabel("外包方用户管理 · 在数据库与 FTP 中新增 / 删除外包方账号")
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

        # 两个功能面板放进滚动区，小屏幕时下方面板不会被挤出屏幕
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(14)
        content_layout.addWidget(card)
        content_layout.addWidget(self._build_delete_card())
        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)
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

    # ---------- 删除人员面板 ----------

    def _build_delete_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("② 删除外包方人员")
        title.setObjectName("cardTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.refresh_users_btn = QPushButton("刷新")
        self.refresh_users_btn.setObjectName("ghost")
        self.refresh_users_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_users_btn.clicked.connect(self._load_users)
        header.addWidget(self.refresh_users_btn)
        layout.addLayout(header)

        tip = QLabel(
            "选择需要删除的外包方人员；删除后其数据库账号与 FTP 访问权限将一并移除。"
        )
        tip.setObjectName("muted")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.delete_status = QLabel("")
        self.delete_status.setObjectName("danger")
        self.delete_status.setWordWrap(True)
        layout.addWidget(self.delete_status)

        self.user_list = QListWidget()
        self.user_list.setMinimumHeight(160)
        self.user_list.itemSelectionChanged.connect(self._on_user_selection_changed)
        layout.addWidget(self.user_list, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.user_count_label = QLabel("共 0 人")
        self.user_count_label.setObjectName("muted")
        self.delete_btn = QPushButton("删除选中人员")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.delete_btn.setEnabled(False)
        footer.addWidget(self.user_count_label)
        footer.addStretch(1)
        footer.addWidget(self.delete_btn)
        layout.addLayout(footer)
        return card

    def _load_users(self) -> None:
        """获取所有外包方人员并刷新列表（数据源见 services.fetch_all_users）。"""
        if self._loading_users or self._deleting_user:
            return
        self._loading_users = True
        self.user_list.setEnabled(False)
        self.refresh_users_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.delete_status.setText("正在获取人员列表…")
        # 与创建流程一致：先给等待反馈，再执行真实请求
        QTimer.singleShot(900, self._finish_load_users)

    def _finish_load_users(self) -> None:
        self._loading_users = False
        self.user_list.clear()

        try:
            users = services.fetch_all_users()
        except Exception as exc:
            self.delete_status.setText(f"获取人员列表失败：{exc}")
            self.user_count_label.setText("共 0 人")
            self.user_list.setEnabled(True)
            self.refresh_users_btn.setEnabled(True)
            return

        for user in users:
            if not isinstance(user, dict):
                continue
            name = str(user.get("name") or "").strip()
            if not name:
                continue
            email = str(user.get("email") or "").strip()
            item = QListWidgetItem(f"{name}　—　{email}" if email else name)
            item.setData(Qt.UserRole, user)
            # 纯选择列表：去掉默认的勾选/拖拽标志，避免出现多余空复选框
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            details = [str(user.get("description") or "").strip()]
            if email:
                details.append(f"邮箱：{email}")
            if user.get("dingtalk_id"):
                details.append(f"钉钉 ID：{user['dingtalk_id']}")
            details = [line for line in details if line]
            item.setToolTip("\n".join(details) or name)
            self.user_list.addItem(item)

        count = self.user_list.count()
        self.user_count_label.setText(f"共 {count} 人")
        self.delete_status.setText("" if count else "暂无人员数据，请点击「刷新」重试")
        self.user_list.setEnabled(True)
        self.refresh_users_btn.setEnabled(True)
        self.delete_btn.setEnabled(count > 0 and self.user_list.currentItem() is not None)

    def _on_user_selection_changed(self) -> None:
        self.delete_btn.setEnabled(
            not self._deleting_user
            and self.user_list.currentItem() is not None
        )

    def _on_delete_clicked(self) -> None:
        item = self.user_list.currentItem()
        if item is None:
            return
        user = item.data(Qt.UserRole) or {}
        name = str(user.get("name") or "")

        ret = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除外包方用户「{name}」吗？\n"
            "删除后其数据库账号与 FTP 访问权限将一并移除，此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        self._deleting_user = True
        self.delete_btn.setEnabled(False)
        self.refresh_users_btn.setEnabled(False)
        self.user_list.setEnabled(False)
        self.delete_status.setText(f"正在删除「{name}」…")
        QTimer.singleShot(900, lambda: self._finish_delete(user))

    def _finish_delete(self, user: dict) -> None:
        name = str(user.get("name") or "")
        ok, message = services.delete_vendor_user(name)
        self._deleting_user = False

        if ok:
            self.delete_status.setText("")
            QMessageBox.information(self, "删除成功", message)
            self._load_users()
        else:
            self.delete_status.setText(message)
            QMessageBox.critical(self, "删除失败", message)
            self.user_list.setEnabled(True)
            self.refresh_users_btn.setEnabled(True)
            self.delete_btn.setEnabled(self.user_list.currentItem() is not None)

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
            return

        # 通过权限校验后才加载删除面板的人员列表
        QTimer.singleShot(0, self._load_users)

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
            # 刷新删除面板列表，让新用户立即可见
            self._load_users()
        else:
            # 失败：保留当前输入状态，方便修改后重试
            self.status_label.setText(message)
            QMessageBox.critical(self, "创建失败", message)
            self._refresh_state()
