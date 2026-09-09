from components.core import FieldSpec, StepComponent, register
from PySide6 import QtWidgets
from dataclasses import dataclass, field

@register("mod")
@dataclass
class ModComponent(StepComponent):
    step:str = "mod"
    name:str = "模型"
    color:str = "#3b82f6"
    description:str = "这是一个mod的资产"
    order:int = 1


    def analysis_relies(self):
        self.rely_steps = ["mod"]
        self.rely_assets = [self.entity]

    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
        h_lay = QtWidgets.QHBoxLayout(self.custom_frame)

        label = QtWidgets.QLabel("这是一个演示的额外UI控件")
        h_lay.addWidget(label)
        checkbox = QtWidgets.QCheckBox("演示checkbox")
        h_lay.addWidget(checkbox)
        edit = QtWidgets.QLineEdit()
        edit.setPlaceholderText("演示输入框")
        h_lay.addWidget(edit)

        



