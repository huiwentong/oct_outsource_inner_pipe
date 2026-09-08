"""collector 第三个区域中的“资产+环节”补充资料行控件。"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QMessageBox
)

from components.core import FieldSpec, StepComponent, inspect_component
from ui.widgets import PopupStyledComboBox



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
        parent: QWidget | None = None,
    ):
        self.project = project
        self.entity = entity
        self.entity_type = entity_type
        self.component = component

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
        check_button.clicked.connect(lambda: QMessageBox.information(parent, 'component信息', inspect_component(component)))

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
