from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets


@register('cfx')
class CfxComponent(StepComponent):
    step:str = "cfx"
    name:str = "特效解算"
    color:str = "#ef4444"
    order:int = 6
    description:str = "这是一个cfx的资产"

    def analysis_relies(self):
        pass
    
    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
