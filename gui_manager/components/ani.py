from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets


@register('ani')
class AniComponent(StepComponent):
    step:str = "ani"
    name:str = "动画"
    color:str = "#f59e0b"
    order:int = 5
    description:str = "这是一个ani的资产"

    def analysis_relies(self):
        pass
    
    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
