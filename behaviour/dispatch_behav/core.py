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
import requests
from datetime import datetime


class StepProcessError(RuntimeError):
    """步骤组件处理失败时抛出的自定义异常"""

    def __init__(self, message: str, event: Event | None = None):
        self.event = event
        super().__init__(message)

    def __str__(self):
        base = super().__str__()
        if self.event:
            return f"{base} | {self.event.summery()}"
        return base



class StepComponent(ABC):

    def __init__(self, event:Event) -> None:
        self.event = event
        self.logger = logger
        self.msg_ids = []

    def append_msg_ids(self, id):
        self.msg_ids.append(id)
    
    def process(self):
        error = self.check_manifest_file()
        if error:
            self.logger.error(error)
            self.send_message(False, error+self.event.summery())
            raise StepProcessError(error, self.event)
        error = self.check_extra()
        if error:
            self.logger.error(error)
            self.send_message(False, error+self.event.summery())
            raise StepProcessError(error, self.event)
        error = self.check_shotgun()
        if error:
            self.logger.error(error)
            self.send_message(False, error+self.event.summery())
            raise StepProcessError(error, self.event)
        
        self.copy_to_w()
        self.publish_to_ddline()
        self.send_message(True, 'manifest解析成功！'+self.event.summery())


    def check_manifest_file(self):
        with Path(self.event.manifest_file).open('r') as f:
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
        
        # 任务名本身可能带下划线（rough_layout / blocking_a），只去掉 _manifest 后缀
        manifest_name = Path(self.event.manifest_file).stem.removesuffix('_manifest')

        if manifest_name != task_name:
            self.logger.error(f'manifest文件名与内容的任务名不符合！{manifest_name} -> {task_name}')
            wrong_message = f'manifest文件名与内容的任务名不符合！{manifest_name} -> {task_name}'
            return wrong_message

        wrong_message = check_shotgun_entitys(project, entity_name, asset_type, task_name, task_step)
        

        root = Path(self.event.manifest_file).parent
        for file in preview + upload_file:
            path_file:Path = root / file
            # manifest 来自外包商：必须是相对路径（绝对路径在拷贝时 dst_folder / file 会变成复制到自身），
            # 且不能用 ../ 跳出回传目录
            if Path(file).is_absolute() or not path_file.resolve().is_relative_to(root.resolve()):
                wrong_message += f'文件{file}不在manifest所在目录内\n'
            elif not path_file.exists():
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


    def send_message(self, status:bool, message:str):
        for uid in self.msg_ids:
            url = 'http://192.168.20.217:8080/ding/msg/simple'
        
            mk_message = """
# {title}
___
{message}
***
`发送时间： {datetime_now}`
""".format(
            title=["❌ 打包回传的manifest文件识别失败！", "🚀 打包回传的manifest文件识别成功！"][status],
            message=message,
            datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
            post_data = {
                'title': '来自十月的收包通知' ,
                'text': mk_message
            }
        
            # 逐个发送，某个人发送失败不影响其他人，也不中断收包
            try:
                ret = requests.post(
                    url=url,
                    params={'user_id': uid},
                    data=json.dumps(post_data)
                )
                ret.raise_for_status()
            except Exception:
                self.logger.exception(f'钉钉通知发送失败: {uid}')
        
        

