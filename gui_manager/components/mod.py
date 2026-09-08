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
        self.frame = QtWidgets.QFrame()

        



