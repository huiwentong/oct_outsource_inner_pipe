from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets


@register('rig')
@dataclass
class RigComponent(StepComponent):
    step:str = "rig"
    name:str = "绑定"
    color:str = "#0ea5e9"
    description:str = "这是一个rig的资产"
    order:int = 3

    def analysis_relies(self):
        pass
    
    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()