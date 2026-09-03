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
)

from components.core import FieldSpec, StepComponent
from ui.widgets import PopupStyledComboBox


def _control_from_spec(spec: FieldSpec, default: Any) -> QWidget:
    """根据字段定义生成输入控件，并把默认值填进去。"""
    if spec.kind == "combo":
        combo = PopupStyledComboBox()
        combo.addItems(spec.options or [])
        text = str(default) if default not in (None, "") else ""
        if text:
            idx = combo.findText(text)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.insertItem(0, text)
                combo.setCurrentIndex(0)
        return combo

    if spec.kind == "check":
        checkbox = QCheckBox(spec.label)
        checkbox.setChecked(bool(default))
        return checkbox

    line = QLineEdit()
    line.setText(str(default) if default is not None else "")
    line.setPlaceholderText(spec.placeholder or "")
    return line


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
        component: StepComponent,
        parent: QWidget | None = None,
    ):
        self.project = project
        self.entity = entity
        self.component = component

        self._specs = component.fields
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
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background:{component.color}; color:white;"
            "border-radius:9px; padding:2px 10px; font-size:12px;"
        )

        path_label = QLabel(f"上传至 {component.default_ftp_path(project, entity)}")
        path_label.setObjectName("rowPath")

        top.addWidget(entity_label)
        top.addWidget(badge)
        top.addSpacing(4)
        top.addWidget(path_label, 1)
        outer.addLayout(top)

        # 第二行：环节对应的补充资料控件
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        defaults = component.mock_defaults(entity, project)
        for spec in self._specs:
            value = defaults.get(spec.key, spec.default)
            widget = _control_from_spec(spec, value)
            self._widgets[spec.key] = widget

            if spec.kind == "check":
                bottom.addWidget(widget)
            else:
                label = QLabel(spec.label)
                if spec.help:
                    label.setToolTip(spec.help)
                bottom.addWidget(label)
                bottom.addWidget(widget, 1)
            if spec.help:
                widget.setToolTip(spec.help)

        outer.addLayout(bottom)

    def read_values(self) -> dict[str, Any]:
        """读取本行补充资料控件的值。"""
        return {spec.key: _read_widget(self._widgets[spec.key], spec) for spec in self._specs}

    def make_payload(self, project: str, vendor: str) -> dict[str, Any]:
        """组装一条开始抓包时需要的完整数据。"""
        return {
            "project": project,
            "vendor": vendor,
            "entity": self.entity,
            "step": self.component.step,
            "step_name": self.component.name,
            "ftp_path": self.component.default_ftp_path(project, self.entity),
            "data": self.read_values(),
        }
