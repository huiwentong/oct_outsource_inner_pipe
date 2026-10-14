# -*- coding: utf-8 -*-
import json
from pathlib import Path
from behaviour.utils.queueevent import Event
from behaviour.utils.deadline import CommandLineJob
from behaviour.utils.shotgun_method import find_task
from behaviour.dispatch_behav.core import StepComponent
from behaviour.util_behav.utils import write_temp_json, to_win_path, is_valid_project_name, is_valid_file_name


class Component(StepComponent):
    def __init__(self, event: Event) -> None:
        super().__init__(event)

    def get_manifest_data(self):
        with Path(self.event.manifest_file).open('r') as f:
            manifest_data: dict = json.load(f)
        return manifest_data

    def check_extra(self):
        manifest_data = self.get_manifest_data()

        upload_files = manifest_data.get('upload_files', [])
        publish_options = dict(manifest_data.get('publish_options') or {})
        entity_name = manifest_data['entity_name']
        task_step = manifest_data['task_step']
        task_name = manifest_data['task_name']

        if not isinstance(upload_files, list):
            return "manifest json文件中 ‘upload_files’ 的值应该是个列表：例：‘upload_files’: ['test01.png', 'test02.png']"

        invalid_upload_files = []
        for file in upload_files:
            if is_valid_file_name(file):
                continue
            invalid_upload_files.append(file)

        if invalid_upload_files:
            return "以下文件名存在非法字符（空格，中文，特殊字符等）, 请修改文件名：\n {}".format('\n'.join(invalid_upload_files))

        publish_type = 'Publish' if upload_files else 'Dailies'

        if publish_type == 'Publish':
            ma_file = publish_options.get('ma_file')

            if not ma_file:
                return "Rig Publish 缺少 publish_options.ma_file"

            name_pattern = "{}.{}.{}".format(entity_name, task_step, task_name)

            if not is_valid_project_name(ma_file, name_pattern):
                return "maya 文件的命名不规范！ 正确格式为：{}.vxxx.(ma|mb)".format(name_pattern)

            if ma_file not in upload_files:
                return "Rig ma_file 未包含在 upload_files 中: {}".format(ma_file)

            if not ma_file.lower().endswith(('.ma', '.mb')):
                return "Rig 工程文件必须为 .ma/.mb: {}".format(ma_file)

        return None


    def publish_to_ddline(self):
        root = Path(self.event.manifest_file).parent
        root = to_win_path(root)
        manifest_data = self.get_manifest_data()

        upload_files = manifest_data['upload_files']
        publish_type = 'Publish' if upload_files else 'Dailies'

        publish_options = dict(manifest_data.get('publish_options') or {})
        preview_paths = [str(Path(root) / i) for i in manifest_data.get('previews', [])]

        maya_file = publish_options.get('ma_file')
        maya_path = None

        if publish_type == 'Publish':
            if not maya_file:
                raise RuntimeError('Rig Publish 缺少 ma_file')

            maya_path = str(Path(root) / maya_file)
            publish_options['ma_file'] = maya_path

        entity_name = manifest_data['entity_name']
        asset_type = manifest_data['type']
        task_name = manifest_data['task_name']
        project = manifest_data['project']

        task = find_task(project, entity_name, asset_type, task_name)

        if not task:
            raise RuntimeError('找不到 ShotGrid Task: {} / {} / {}'.format(project, entity_name, task_name))

        pub_data = {
            'task_id': task['id'],
            'dcc_file': maya_path,
            'version_num': self.event.version,
            'user': 'zhouqi',
            'comment': manifest_data.get('comment', ''),
            'publish_type': publish_type,
            'publish_tag_id': 1141,
            'preview_paths': preview_paths,
            'notify': ['zhouqi'],
            'input_form': publish_options,
        }

        publish_json = write_temp_json(pub_data)
        cmd = 'rez-env PySide2 oct_publish -- batch_cli "{}"'.format(publish_json)

        job_name = 'Rig Outsource Recycle: {} {} {}'.format(entity_name, publish_type, self.event.version)

        job = CommandLineJob(name=job_name)
        job.set_command(cmd)
        job.set_pool('user')
        job.set_priority(priority=100)
        job.set_job_error_limit(number=3)
        job.set_task_timeout_minutes(minutes='60')

        job_id = job.submit()
        if not job_id:
            raise RuntimeError('Rig Deadline Job 提交失败，未获取到 job_id')

        print('创建 Rig manifest 任务成功, 任务ID: {}'.format(job_id))
        return job_id