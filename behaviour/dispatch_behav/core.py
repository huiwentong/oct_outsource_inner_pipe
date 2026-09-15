from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sys
from abc import abstractmethod, ABC
from behaviour.utils.queueevent import Event
from behaviour import logger
from pathlib import Path
from behaviour.utils.shotgun_method import check_shotgun_entitys
import shutil


class StepComponent(ABC):

    def __init__(self, event:Event) -> None:
        self.event = event
        self.logger = logger
        
        
    
    def process(self):
        error = self.check_manifest_file()
        if error:
            self.logger.error(error)
            raise RuntimeError(error)
        error = self.check_extra()
        if error:
            self.logger.error(error)
            raise RuntimeError(error)
        error = self.check_shotgun()
        if error:
            self.logger.error(error)
            raise RuntimeError(error)
        
        self.copy_to_w()
        self.publish_to_ddline()


    def check_manifest_file(self):
        with Path('/srv/frp/' + self.event.manifest_file).open('r') as f:
            data:dict = json.load(f)

        wrong_message = ''

        try:
            preview = data['previews']
            upload_file = data['upload_files']
            publish_options = data['publish_options']
            entity_name = data['entity_name']
            asset_type = data['type']
            task_name = data['task_name']
            task_step = data['task_step']
            project = data['project']
            comment = data['comment']
        except Exception:
            self.logger.error('manifest.json文件缺少属性')
            wrong_message = f'manifest.json文件缺少属性: {str(list(data.keys()))}'
            return wrong_message
        
        manifest_name = Path(self.event.manifest_file).stem.split('_')[0]

        if manifest_name != task_name:
            self.logger.error(f'manifest文件名与内容的任务名不符合！{manifest_name} -> {task_name}')
            wrong_message = f'manifest文件名与内容的任务名不符合！{manifest_name} -> {task_name}'
            return wrong_message

        wrong_message = check_shotgun_entitys(project, entity_name, asset_type, task_name, task_step)
        


        for file in preview + upload_file:
            root = Path(self.event.manifest_file).parent
            path_file:Path = root / file
            if not path_file.exists():
                wrong_message += f'文件{str(path_file)}不存在\n'

        if wrong_message:
            self.logger.error(wrong_message)
            return wrong_message



        if not comment:
            self.logger.error('没有找到备注！')
            return '没有找到备注！'



    @abstractmethod
    def check_extra(self) -> str:
        return ''



    def check_shotgun(self):
        error_msg = ''
        return error_msg


    def copy_to_w(self):
        dst_folder = Path(self.event.dst_path) / self.event.version
        source_folder = Path(self.event.manifest_file).parent
        if not source_folder.exists():
            raise FileNotFoundError(f"源路径不存在: {source_folder}")

        if not source_folder.is_dir():
            raise NotADirectoryError(f"源路径不是目录: {source_folder}")
        
        dst_folder.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(
                str(source_folder),
                str(dst_folder),
                dirs_exist_ok=True
            )
        except Exception as e:
            raise RuntimeError(
                f"复制失败: {source_folder} -> {dst_folder}"
            ) from e
        


    @abstractmethod
    def publish_to_ddline(self):
        return ''



