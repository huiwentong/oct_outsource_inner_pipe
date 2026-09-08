from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets




@register('efx')
@dataclass
class EfxComponent(StepComponent):
    step:str = "efx"
    name:str = "特效"
    color:str = "#ec4899"
    description:str = "这是一个efx的资产"
    order:int = 7

    def analysis_relies(self):
        pass
    
    def analysis_transfer_folders(self):
        pass
    

    def extra_ui(self):
        self.frame = QtWidgets.QFrame()
