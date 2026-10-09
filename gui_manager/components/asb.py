from components.core import FieldSpec, StepComponent, register
from PySide6 import QtWidgets
from dataclasses import dataclass, field
from pathlib import Path
from utils.shotgun import FastSg


@register("asb")
@dataclass
class AsbComponent(StepComponent):
    step: str = "asb"
    name: str = "场景"
    color: str = "#16a34a"
    description: str = "这是一个asb的资产"
    order: int = 5

    # def analysis_relies(self):
    #     self.rely_steps = ["mod"]
    #     self.rely_assets = [self.entity]
    #
    #     sg = FastSg().client
    #     filters = [
    #         ['code', 'is', self.entity],
    #         ['project', 'name_is', self.project],
    #     ]
    #     fields = ['assets']
    #     orders = [
    #         {'field_name': 'id', 'direction': 'desc'},
    #     ]
    #     sg_asset = sg.find_one('Asset', filters, fields, order=orders)
    #
    #     # 更新依赖资产
    #     sub_assets = sg_asset.get('assets', [])
    #     for sub_asset in sub_assets:
    #         sub_asset_name = sub_asset.get('name', '')
    #         if sub_asset_name:
    #             self.rely_assets.append(sub_asset_name)

    def analysis_relies(self):
        self.rely_steps = ["mod"]
        self.rely_assets = [self.entity]

        sg = FastSg().client
        filters = [
            ['code', 'is', self.entity],
            ['project', 'name_is', self.project],
        ]
        fields = ['assets']
        orders = [
            {'field_name': 'id', 'direction': 'desc'},
        ]
        sg_asset = sg.find_one('Asset', filters, fields, order=orders)

        # 收集所有可达子资产
        sub_assets = sg_asset.get('assets', [])

        # 用队列遍历所有子资产，找到没有子资产的末端资产
        queue = []
        for sub_asset in sub_assets:
            sub_asset_name = sub_asset.get('name', '')
            if sub_asset_name:
                queue.append(sub_asset_name)

        visited = set(self.rely_assets)

        while queue:
            asset_name = queue.pop(0)

            # 如果已经处理过，就跳过
            if asset_name in visited:
                continue

            visited.add(asset_name)

            # 查询当前资产是否还有子资产
            child_filters = [
                ['code', 'is', asset_name],
                ['project', 'name_is', self.project],
            ]
            child_fields = ['assets']
            child_asset = sg.find_one('Asset', child_filters, child_fields)

            child_list = child_asset.get('assets', []) if child_asset else []

            if child_list:
                # 还有子资产，继续入队
                for child in child_list:
                    child_name = child.get('name', '')
                    if child_name and child_name not in visited:
                        queue.append(child_name)
            else:
                # 没有子资产，说明是末端资产
                self.rely_assets.append(asset_name)

    def analysis_transfer_folders(self):
        print('asb analysis_transfer_folders')
        steps = ["mod", "rig", "tex"]

        mapping = {
            "mod": "model",
            "rig": "rigging",
            "tex": "texture",
            "fur": "hair",
        }

        # 收集场景子资产
        for rely_asset in self.rely_assets:
            if rely_asset == self.entity:
                continue

            for step in steps:
                sg = FastSg().client
                sg_task = mapping[step]
                filters = [
                    ['entity', 'name_is', rely_asset],
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
                ftp_step_dir = f"/oct/{self.project}/{self.entity_type}/{rely_asset}/{step}"

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

                usda_file_name = rely_asset + '.{}'.format(step) + '.usda'
                loc_usda_file = str(Path(loc_step_dir) / usda_file_name)
                ftp_usda_file = ftp_step_dir + '/' + usda_file_name
                print("loc_usda_file: {}".format(loc_usda_file))
                print("ftp_usda_file: {}".format(ftp_usda_file))
                if Path(loc_usda_file).exists():
                    self.transfer_folders[loc_usda_file] = ftp_usda_file

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
