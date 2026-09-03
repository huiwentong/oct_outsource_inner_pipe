"""collector GUI 主窗口。"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from components.core import StepComponent, get_component, step_options
from ui.collector.mock_data import (
    PROJECTS,
    get_project_entities_mock,
    get_vendor_names_mock,
    project_name,
)
from ui.collector.task_row import TaskRow
from ui.widgets import PopupStyledComboBox
from ui.window_utils import keep_window_on_screen

STEPS_HINT = "每个资产/实体至少选择一个环节，数据才会进入下方补充资料区"


def _hint_label(text: str, danger: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName("danger" if danger else "muted")
    label.setWordWrap(True)
    return label


class CollectorWindow(QMainWindow):
    """制片资产抓包工具主窗口。"""

    def __init__(self):
        super().__init__()
        self.project_id: Optional[str] = None
        self._step_boxes: dict[str, QCheckBox] = {}
        self._rows: list[TaskRow] = []
        self._rows_maximized = False
        self._placed_once = False

        self.setWindowTitle("Collector · 制片资产抓包工具")
        self.resize(1160, 820)
        self.setMinimumSize(980, 700)

        self._build_ui()
        self._update_state()

    # ---------- UI 构建 ----------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        # 品牌标题
        title = QLabel("Collector")
        title.setObjectName("appTitle")
        sub = QLabel("制片资产数据抓包 · 把制作环节文件自动发送给外包方")
        sub.setObjectName("appSub")
        head_box = QHBoxLayout()
        head_box.addWidget(title)
        head_box.addWidget(sub)
        head_box.addStretch(1)
        root.addLayout(head_box)

        # 项目选择（必须最先完成）
        root.addWidget(self._build_project_card())

        # 主体区域（选择项目后才会显示三个区域）
        self._stack = QStackedWidget()

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_hint = QLabel("请先在上方选择抓包项目（MK2 / MKO）")
        empty_hint.setObjectName("emptyState")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_hint)
        empty_layout.addStretch(1)

        self._stack.addWidget(empty_page)
        self._stack.addWidget(self._build_regions_page())
        root.addWidget(self._stack, 1)

        # 底部汇总与开始按钮
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.summary_label = _hint_label("尚未选择内容")
        self.start_btn = QPushButton("开始抓包")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start_collect)
        bottom.addWidget(self.summary_label, 1)
        bottom.addWidget(self.start_btn)
        root.addLayout(bottom)

        self.setCentralWidget(central)

    def _build_project_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("选择项目 *")
        t.setObjectName("cardTitle")
        s = _hint_label("开始前需先确定这批数据属于哪个项目")
        left.addWidget(t)
        left.addWidget(s)
        layout.addLayout(left)
        layout.addStretch(1)

        self._project_buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for proj in PROJECTS:
            pid = proj["id"]
            btn = QPushButton(proj["name"])
            btn.setObjectName("projectToggle")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=pid: self._on_project_chosen(p))
            group.addButton(btn)
            self._project_buttons[pid] = btn
            layout.addWidget(btn)

        return card

    def _build_regions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._region1_card = self._build_region1_card()
        self._region2_card = self._build_region2_card()
        self._region3_card = self._build_region3_card()
        layout.addWidget(self._region1_card)
        layout.addWidget(self._region2_card)
        layout.addWidget(self._region3_card, 1)
        return page

    def _build_region1_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        header = QHBoxLayout()
        t = QLabel("① 选择实体 / 资产（可多选）")
        t.setObjectName("cardTitle")
        header.addWidget(t)
        header.addWidget(_hint_label("勾选需要抓包的数据，支持搜索"))
        header.addStretch(1)
        outer.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        # 左侧：实体列表（全选/清空固定在标题行，避免被列表高度挤压）
        entity_panel = QVBoxLayout()
        entity_panel.setSpacing(6)

        entity_head = QHBoxLayout()
        entity_head.setSpacing(8)
        filter_label = _hint_label("实体 / 资产")
        sel_all = QPushButton("全选")
        sel_all.setObjectName("ghost")
        sel_all.setCursor(Qt.PointingHandCursor)
        sel_all.clicked.connect(lambda: self._set_all_entities(True))
        clear_all = QPushButton("清空")
        clear_all.setObjectName("ghost")
        clear_all.setCursor(Qt.PointingHandCursor)
        clear_all.clicked.connect(lambda: self._set_all_entities(False))
        entity_head.addWidget(filter_label)
        entity_head.addStretch(1)
        entity_head.addWidget(sel_all)
        entity_head.addWidget(clear_all)
        entity_panel.addLayout(entity_head)

        self.entity_filter = QLineEdit()
        self.entity_filter.setPlaceholderText("输入关键字快速筛选…")
        self.entity_filter.textChanged.connect(self._on_filter_changed)
        entity_panel.addWidget(self.entity_filter)

        self.entity_list = QListWidget()
        self.entity_list.setMinimumHeight(120)
        self.entity_list.setMaximumHeight(340)
        self.entity_list.itemChanged.connect(self._on_entity_item_changed)
        entity_panel.addWidget(self.entity_list, 1)

        columns.addLayout(entity_panel, 3)

        # 右侧：环节多选
        step_panel = QVBoxLayout()
        step_panel.setSpacing(6)
        step_title_row = QHBoxLayout()
        step_title = QLabel("环节 *")
        step_title.setObjectName("cardTitle")
        step_title_row.addWidget(step_title)
        step_title_row.addWidget(_hint_label("必选", danger=True))
        step_title_row.addStretch(1)
        step_panel.addLayout(step_title_row)
        step_panel.addWidget(_hint_label(STEPS_HINT))

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        for i, (step, name, color) in enumerate(step_options()):
            row, col = divmod(i, 2)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")
            cb = QCheckBox(name)
            cb.setToolTip(f"环节标识: {step}")
            cb.toggled.connect(self._on_step_toggled)
            self._step_boxes[step] = cb
            cell = QHBoxLayout()
            cell.setSpacing(4)
            cell.addWidget(dot)
            cell.addWidget(cb)
            cell.addStretch(1)
            grid.addLayout(cell, row, col)
        step_panel.addLayout(grid)
        step_panel.addStretch(1)

        step_quick = QHBoxLayout()
        step_on = QPushButton("全选环节")
        step_on.setObjectName("ghost")
        step_on.setCursor(Qt.PointingHandCursor)
        step_on.clicked.connect(lambda: self._set_all_steps(True))
        step_off = QPushButton("清空环节")
        step_off.setObjectName("ghost")
        step_off.setCursor(Qt.PointingHandCursor)
        step_off.clicked.connect(lambda: self._set_all_steps(False))
        step_quick.addWidget(step_on)
        step_quick.addWidget(step_off)
        step_quick.addStretch(1)
        step_panel.addLayout(step_quick)

        columns.addLayout(step_panel, 2)
        outer.addLayout(columns, 1)
        return card

    def _build_region2_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(8)

        header = QHBoxLayout()
        t = QLabel("② 选择接收数据的外包方")
        t.setObjectName("cardTitle")
        header.addWidget(t)
        header.addWidget(_hint_label("支持输入后自动补全"))
        header.addStretch(1)
        outer.addLayout(header)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.vendor_combo = PopupStyledComboBox()
        self.vendor_combo.setEditable(True)
        self.vendor_combo.addItems(get_vendor_names_mock())
        self.vendor_combo.setInsertPolicy(PopupStyledComboBox.NoInsert)
        self.vendor_combo.setCurrentIndex(-1)
        self.vendor_combo.setPlaceholderText("选择或输入外包方名称…")
        self.vendor_combo.setMinimumWidth(360)
        completer = QCompleter(self.vendor_combo.model(), self)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.vendor_combo.setCompleter(completer)
        self.vendor_combo.lineEdit().textChanged.connect(self._update_state)

        tip = _hint_label("确定后系统会把抓包数据放到该外包方可访问的 FTP 路径")
        row.addWidget(self.vendor_combo)
        row.addWidget(tip, 1)
        outer.addLayout(row)
        return card

    def _build_region3_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(8)

        header = QHBoxLayout()
        t = QLabel("③ 补充资料（自动生成）")
        t.setObjectName("cardTitle")
        header.addWidget(t)
        header.addStretch(1)
        self.rows_count_label = _hint_label("0 项")
        self.rows_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.rows_count_label)

        self.rows_max_btn = QPushButton("展开大视图")
        self.rows_max_btn.setObjectName("ghost")
        self.rows_max_btn.setCursor(Qt.PointingHandCursor)
        self.rows_max_btn.setCheckable(True)
        self.rows_max_btn.setToolTip("展开后，补充资料区域将占满整个面板")
        self.rows_max_btn.toggled.connect(self._on_rows_max_toggled)
        header.addWidget(self.rows_max_btn)
        outer.addLayout(header)

        self.rows_scroll = QScrollArea()
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setMinimumHeight(120)
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(2, 2, 8, 2)
        self.rows_layout.setSpacing(8)
        self.rows_layout.addStretch(1)
        self.rows_scroll.setWidget(self.rows_container)
        outer.addWidget(self.rows_scroll, 1)
        return card

    # ---------- 窗口首次显示定位 ----------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._placed_once:
            self._placed_once = True
            # 等原生窗口创建完成后再校正：确保带边框并完整落在当前屏幕内
            QTimer.singleShot(0, lambda: keep_window_on_screen(self))

    # ---------- 数据与交互 ----------

    def _on_project_chosen(self, project_id: str) -> None:
        self.project_id = project_id
        self._load_entities()
        self._set_all_steps(False)
        self._stack.setCurrentIndex(1)
        self._update_state()

    def _load_entities(self) -> None:
        self._set_all_entities(False, emit=False)
        self.entity_list.clear()
        for name in get_project_entities_mock(self.project_id or ""):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.entity_list.addItem(item)
        self._refresh_region3()

    def _set_all_entities(self, checked: bool, emit: bool = True) -> None:
        self.entity_list.blockSignals(True)
        for i in range(self.entity_list.count()):
            item = self.entity_list.item(i)
            if not self.entity_list.isRowHidden(i):
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.entity_list.blockSignals(False)
        if emit:
            self._refresh_region3()

    def _set_all_steps(self, checked: bool) -> None:
        for cb in self._step_boxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._refresh_region3()

    def _on_filter_changed(self, text: str) -> None:
        text = text.strip().lower()
        for i in range(self.entity_list.count()):
            item = self.entity_list.item(i)
            hide = bool(text) and text not in item.text().lower()
            self.entity_list.setRowHidden(i, hide)

    def _on_entity_item_changed(self, _item: QListWidgetItem) -> None:
        self._refresh_region3()

    def _on_step_toggled(self, _checked: bool) -> None:
        self._refresh_region3()

    def _checked_entities(self) -> list[str]:
        checked = []
        for i in range(self.entity_list.count()):
            item = self.entity_list.item(i)
            if not self.entity_list.isRowHidden(i) and item.checkState() == Qt.Checked:
                checked.append(item.text())
        return checked

    def _checked_steps(self) -> list[str]:
        return [step for step, cb in self._step_boxes.items() if cb.isChecked()]

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.frame.setParent(None)
            row.frame.deleteLater()
        self._rows = []

        while self.rows_layout.count() > 1:  # 最后一个是 stretch
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_rows_hint(self, message: str) -> None:
        self._clear_rows()
        label = QLabel(message)
        label.setObjectName("emptyState")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        self.rows_layout.insertWidget(0, label)

    def _on_rows_max_toggled(self, checked: bool) -> None:
        """展开/收起补充资料区域：展开时占满整个面板。"""
        self._rows_maximized = checked
        # 展开时隐藏 ① 选择实体 与 ② 选择外包方，把空间全部让给补充资料
        self._region1_card.setVisible(not checked)
        self._region2_card.setVisible(not checked)
        self.rows_max_btn.setText("收起还原" if checked else "展开大视图")
        self.rows_max_btn.setToolTip(
            "收起后回到与 ① ② 区域并排显示的状态"
            if checked
            else "展开后，补充资料区域将占满整个面板"
        )

    def _refresh_region3(self) -> None:
        self._clear_rows()

        entities = self._checked_entities()
        steps = self._checked_steps()

        if not entities:
            self._show_rows_hint("还没有选择实体/资产：请在 ① 中勾选需要抓包的数据")
            self._update_state()
            return
        if not steps:
            self._show_rows_hint(f"还没有选择环节：{STEPS_HINT}")
            self._update_state()
            return

        for entity in entities:
            for step in steps:
                component: StepComponent = get_component(step)
                row = TaskRow(self.project_id or "", entity, component)
                self._rows.append(row)
                self.rows_layout.addWidget(row.frame)

        self._update_state()

    def _update_state(self) -> None:
        entities = self._checked_entities()
        steps = self._checked_steps()
        vendor = self.vendor_combo.currentText().strip() if self.project_id else ""

        valid_project = self.project_id is not None
        has_vendor = bool(vendor)
        has_rows = len(self._rows) > 0

        if not valid_project:
            self.summary_label.setText("尚未选择项目")
            self.rows_count_label.setText("0 项")
        elif not entities:
            self.summary_label.setText("请选择实体/资产")
            self.rows_count_label.setText("0 项")
        elif not steps:
            self.summary_label.setText("环节是必选的，请先勾选至少一个环节")
            self.rows_count_label.setText("0 项")
        elif not has_vendor:
            self.summary_label.setText(
                f"已选择 {len(entities)} 个实体 × {len(steps)} 个环节，共 {len(self._rows)} 项抓包任务 —— 请选择外包方"
            )
            self.rows_count_label.setText(f"{len(self._rows)} 项")
        else:
            self.summary_label.setText(
                f"{project_name(self.project_id)} · {vendor} · "
                f"{len(entities)} 个实体 × {len(steps)} 个环节，共 {len(self._rows)} 项抓包任务"
            )
            self.rows_count_label.setText(f"{len(self._rows)} 项")

        self.rows_count_label.setVisible(valid_project and (bool(entities) or bool(steps)))
        self.start_btn.setEnabled(valid_project and bool(entities) and bool(steps) and has_vendor and has_rows)

    # ---------- 开始抓包 ----------

    def _start_collect(self) -> None:
        vendor = self.vendor_combo.currentText().strip()
        project_name_zh = project_name(self.project_id or "")
        print("=" * 66)
        print(f"[开始抓包] 项目: {project_name_zh} | 外包方: {vendor}")
        print(f"[开始抓包] 共 {len(self._rows)} 项任务:")
        for row in self._rows:
            payload = row.make_payload(self.project_id or "", vendor)
            # 调用对应环节组件的能力（当前是 mock 打印）
            row.component.collect(payload)
        print("=" * 66)

        QMessageBox.information(
            self,
            "开始抓包",
            f"已模拟执行 {len(self._rows)} 项抓包任务。\n"
            "详细输出请查看终端。\n（真实抓包与上传逻辑待后续补充）",
        )
