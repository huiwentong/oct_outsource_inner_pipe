from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets


@register('tex')
@dataclass
class TexComponent(StepComponent):
    step:str = "tex"
    name:str = "材质"
    color:str = "#8b5cf6"
    description:str = "这是一个lay的资产"
    order:int = 2

    
    def analysis_relies(self):
        pass
    
    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
