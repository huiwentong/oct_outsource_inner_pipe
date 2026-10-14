"""collector 第三个区域中的“资产+环节”补充资料行控件。"""

from __future__ import annotations

from typing import Any

from dataclasses import fields
from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QMessageBox
)

from components.core import FieldSpec, StepComponent
from ui.widgets import PopupStyledComboBox


def _component_text(component: StepComponent) -> str:
    """组件信息转成多行文本，上传清单按 FTP 路径排序、一项一行。"""
    lines = []
    for f in fields(component):
        v = getattr(component, f.name)
        if isinstance(v, QFrame):
            continue
        if isinstance(v, dict):
            lines.append(f"{f.name}: 共 {len(v)} 项")
            for src, dst in sorted(v.items(), key=lambda kv: kv[1]):
                lines += [f"  {dst}", f"      ← {src}"]
        elif isinstance(v, list):
            lines.append(f"{f.name}: {', '.join(map(str, v)) or '（空）'}")
        else:
            lines.append(f"{f.name}: {v}")
    return "\n".join(lines)


def _tree_key(dst: str) -> tuple[list[str], str]:
    """FTP 路径 → (分组层级, 叶子名称).

    /oct/{项目}/{类型}/{实体}/{环节}/{剩余} → ([类型, 实体, 环节], 剩余)
    /oct/{项目}/{类型}/{实体}/{文件}         → ([类型, 实体], 文件), 如 default_path.json
    其他不符合约定的路径归到 "其他".
    """
    parts = dst.replace("\\", "/").strip("/").split("/")
    if len(parts) >= 6 and parts[0] == "oct":
        return parts[2:5], "/".join(parts[5:])
    if len(parts) == 5 and parts[0] == "oct":
        return parts[2:4], parts[4]
    return ["其他"], dst


def _build_model(transfer_folders: dict[str, str]) -> QStandardItemModel:
    """按 类型 → 实体 → 环节 → 文件 建三列的树: 名称 / FTP 路径 / 本地来源."""
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["名称", "FTP 路径", "本地来源"])
    groups: dict[tuple[str, ...], QStandardItem] = {}
    counts: dict[tuple[str, ...], int] = {}
    # core 里手动选的额外文件和旧版 default_path.json 用 str(Path(...)) 拼 FTP 路径, Windows 下是 \, 统一成 /
    # (上传时 FtpClient 也会做同样的替换)
    items = sorted(((src, dst.replace("\\", "/")) for src, dst in transfer_folders.items()), key=lambda kv: kv[1])
    for src, dst in items:
        levels, leaf = _tree_key(dst)
        project_root = "/".join(dst.split("/")[:3])  # /oct/{项目}
        parent = model.invisibleRootItem()
        for i in range(len(levels)):
            key = tuple(levels[: i + 1])
            if key not in groups:
                groups[key] = QStandardItem(levels[i])
                ftp_dir = "" if levels == ["其他"] else f"{project_root}/{'/'.join(key)}"
                parent.appendRow([groups[key], QStandardItem(ftp_dir), QStandardItem()])
            counts[key] = counts.get(key, 0) + 1
            parent = groups[key]
        # ponytail: 目录只显示一个节点、不展开, 避免打开弹窗时扫描大目录
        is_dir = Path(src).is_dir()
        name = QStandardItem(leaf + ("/" if is_dir else ""))
        name.setToolTip("整个目录递归上传" if is_dir else "文件")
        ftp = QStandardItem(dst)
        ftp.setToolTip(dst)
        source = QStandardItem(src)
        source.setToolTip(src)
        parent.appendRow([name, ftp, source])
    for key, item in groups.items():  # 分组后面标出条目数
        item.setText(f"{item.text()}  ({counts[key]})")
    return model


def _show_component(parent: QWidget | None, component: StepComponent) -> None:
    """抓包信息弹窗: 顶部概要, 下方按 类型 → 实体 → 环节 → 文件 的树, 可搜索、可复制完整清单."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"{component.entity} · {component.name} 抓包信息")
    dialog.resize(1100, 680)

    summary = QLabel(
        f"<b>{component.project} / {component.entity_type} / {component.entity} · {component.step}</b>"
        f"　上传清单共 {len(component.transfer_folders)} 项<br>"
        f"依赖实体: {', '.join(component.rely_assets) or '(空)'}<br>"
        f"依赖环节: {', '.join(component.rely_steps) or '(空)'}"
    )
    summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    summary.setWordWrap(True)

    search = QLineEdit()
    search.setPlaceholderText("搜索文件名、FTP 路径或本地路径, 如 dasheng / .usda / /oct/mk2/shot")
    search.setClearButtonEnabled(True)

    proxy = QSortFilterProxyModel(dialog)
    proxy.setSourceModel(_build_model(component.transfer_folders))
    proxy.setRecursiveFilteringEnabled(True)  # 子节点命中时保留上级
    proxy.setFilterKeyColumn(-1)  # 三列都搜
    proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    tree = QTreeView()
    tree.setModel(proxy)
    tree.setUniformRowHeights(True)
    tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
    # 隔行变色, 颜色沿用 ui/style.py 列表的配色
    tree.setAlternatingRowColors(True)
    tree.setStyleSheet(
        "QTreeView { background: #ffffff; alternate-background-color: #eef2f7; }"
        "QTreeView::item:hover { background: #e2e8f0; }"
        "QTreeView::item:selected { background: #dbeafe; color: #1d4ed8; }"
    )
    tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    tree.header().resizeSection(0, 300)
    tree.header().resizeSection(1, 460)
    tree.expandToDepth(0)  # 默认只展开类型, 列出实体; 实体下的内容点击再展开

    def on_search(text: str) -> None:
        proxy.setFilterFixedString(text.strip())
        tree.expandAll() if text.strip() else tree.expandToDepth(0)

    search.textChanged.connect(on_search)

    copy_btn = QPushButton("复制清单")
    copy_btn.setToolTip("复制为纯文本, 方便发给别人")
    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(_component_text(component)))

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
    buttons.addButton(copy_btn, QDialogButtonBox.ButtonRole.ActionRole)
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(summary)
    layout.addWidget(search)
    layout.addWidget(tree, 1)
    layout.addWidget(buttons)
    dialog.exec()



def _read_widget(widget: QWidget, spec: FieldSpec) -> Any:
    if spec.kind == "check":
        return widget.isChecked()
    if spec.kind == "combo":
        return widget.currentText()
    return widget.text().strip()


class TaskRow:
    """一行“实体 + 环节 + 该环节补充资料控件”。"""

    def __init__(
        self,
        project: str,
        entity: str,
        entity_type: str,
        component: StepComponent,
        step: str,
        parent: QWidget | None = None,
    ):
        self.project = project
        self.entity = entity
        self.entity_type = entity_type
        self.component = component
        self.step=step

        self._widgets: dict[str, QWidget] = {}

        self.frame = QFrame(parent)
        self.frame.setObjectName("rowCard")

        outer = QVBoxLayout(self.frame)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        # 第一行：实体 + 环节徽章 + 上传路径
        top = QHBoxLayout()
        top.setSpacing(8)

        entity_label = QLabel(entity)
        entity_label.setObjectName("rowEntity")

        badge = QLabel(component.name)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background:{component.color}; color:white;"
            "border-radius:9px; padding:2px 10px; font-size:12px;"
        )
        

        path_label = QLabel(f"上传至 {component.ftp_tar}")
        path_label.setObjectName("rowPath")

        check_button = QPushButton('点击检查')
        check_button.clicked.connect(lambda: _show_component(parent, component))

        top.addWidget(entity_label)
        top.addWidget(badge)
        top.addSpacing(4)
        top.addWidget(path_label, 1)
        top.addWidget(check_button)
        outer.addLayout(top)

        # 第二行：环节对应的补充资料控件
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        b_bottom = QHBoxLayout()
        b_bottom.setSpacing(8)
        if not component.auto_build_frame:
            raise RuntimeError('can not build auto frame!')
        bottom.addWidget(component.auto_build_frame)
        if component.custom_frame:
            b_bottom.addWidget(component.custom_frame)
            

        outer.addLayout(bottom)
        outer.addLayout(b_bottom)

    # def read_values(self) -> dict[str, Any]:
    #     """读取本行补充资料控件的值。"""
    #     return {spec.key: _read_widget(self._widgets[spec.key], spec) for spec in self._specs}

    # def make_payload(self, project: str, vendor: str) -> dict[str, Any]:
    #     """组装一条开始抓包时需要的完整数据。"""
    #     return {
    #         "project": project,
    #         "vendor": vendor,
    #         "entity": self.entity,
    #         "step": self.component.step,
    #         "step_name": self.component.name,
    #         "ftp_path": self.component.default_ftp_path(project, self.entity, self.entity_type),
    #         "data": self.read_values(),
        # }
