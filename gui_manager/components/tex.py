from components.core import FieldSpec, StepComponent, register
from dataclasses import dataclass, field
from PySide6 import QtWidgets
from pathlib import Path
from utils.shotgun import FastSg


@register('tex')
@dataclass
class TexComponent(StepComponent):
    step: str = "tex"
    name: str = "材质"
    color: str = "#8b5cf6"
    description: str = "这是一个tex的资产"
    order: int = 2

    def analysis_relies(self):
        self.rely_steps = ["mod"]
        self.rely_assets = [self.entity]

    def analysis_transfer_folders(self):
        mapping = {
            "mod": "model",
            "rig": "rigging",
            "tex": "texture",
        }
        steps = self.rely_steps
        if self.step not in steps:
            steps.append(self.step)
        for step in steps:
            sg = FastSg().client
            sg_task = mapping[step]
            filters = [
                ['entity', 'name_is', self.entity],
                ['project', 'name_is', self.project],
                ['sg_task', 'name_is', sg_task],
            ]
            fields = ['sg_path_to_geometry']
            orders = [
                {'field_name': 'id', 'direction': 'desc'},
            ]
            sg_version = sg.find_one('Version', filters, fields, order=orders)
            if not sg_version:
                continue
            path_to_geometry = sg_version['sg_path_to_geometry']
            loc_step_dir = str(Path(path_to_geometry).parent.parent)
            ftp_step_dir = f"/oct/{self.project}/{self.entity_type}/{self.entity}/{step}"

            v_name = str(Path(path_to_geometry).parent.name)
            loc_v_dir = str(Path(loc_step_dir) / v_name)
            ftp_v_dir = ftp_step_dir + '/' + v_name
            if Path(loc_v_dir).exists():
                self.transfer_folders[loc_v_dir] = ftp_v_dir

            non_v_name = v_name[0:-len('.' + v_name.split('.')[-1])]
            loc_non_v_dir = str(Path(loc_step_dir) / non_v_name)
            ftp_non_v_dir = ftp_step_dir + '/' + non_v_name
            if Path(loc_non_v_dir).exists():
                self.transfer_folders[loc_non_v_dir] = ftp_non_v_dir

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
