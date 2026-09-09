from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets


@register('lay')
@dataclass
class LayComponent(StepComponent):
    step:str = "lay"
    name:str = "Layout"
    color:str = "#14b8a6"
    description:str = "这是一个lay的资产"
    order:int = 4


    def analysis_relies(self):
        pass
    
    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
