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
            manifest_data:dict = json.load(f)
        return manifest_data


    def check_extra(self):
        try:
            manifest_data = self.get_manifest_data()
            upload_files = manifest_data['upload_files']
            publish_options = manifest_data['publish_options']
            ma_file = publish_options['ma_file']
            entity_name = manifest_data['entity_name']
            task_step = manifest_data['task_step']
            task_name = manifest_data['task_name']

            name_pattern = "{}.{}.{}".format(entity_name, task_step, task_name)
            if not is_valid_project_name(ma_file, name_pattern):
                return "maya 文件的命名不规范！ 正确格式为：{}.vxxx.(ma|mb)".format(name_pattern)

            assert isinstance(upload_files, list), \
                "manifest json文件中 ‘upload_files’ 的值应该是个列表：例：‘upload_files’: ['test01.png', 'test02.png']"

            invalid_upload_files = []
            for file in upload_files:
                if is_valid_file_name(file):
                    continue
                invalid_upload_files.append(file)

            if len(invalid_upload_files) > 0:
                return "以下文件名存在非法字符（空格，中文，特殊字符等）, 请修改文件名：\n {}".format(
                    '\n'.join(invalid_upload_files))

        except Exception as e:
            self.logger.error(e)
            return e

    def publish_to_ddline(self):
        try:
            root = Path(self.event.dst_path) / self.event.version
            root = to_win_path(root)
            self.logger.info("windows root: {}".format(root))
            self.logger.info("linux root: {}".format(Path(self.event.dst_path) / self.event.version))
            manifest_data = self.get_manifest_data()

            publish_options = manifest_data['publish_options']
            maya_file = publish_options['ma_file']
            publish_options['ma_file'] = str(Path(root) / maya_file)
            src_tex_files = publish_options.get('src_tex_files', [])
            publish_options['src_tex_files'] = [str(Path(root) / i) for i in src_tex_files] if src_tex_files else ["None"]

            publish_type = 'Publish' if maya_file else 'Dailies'
            version_num = Path(maya_file).stem.split(".")[-1]

            entity_name = manifest_data['entity_name']
            asset_type = manifest_data['type']
            task_name = manifest_data['task_name']
            project = manifest_data['project']
            task = find_task(project, entity_name, asset_type, task_name)

            pub_data = {"task_id": task["id"],
                        "dcc_file": str(Path(root)/ maya_file),
                        "version_num": version_num,
                        "user": "gongshuai",
                        "comment": manifest_data['comment'],
                        "publish_type": publish_type,
                        "publish_tag_id": 1141,
                        "preview_paths": [str(Path(root) / i) for i in manifest_data['previews']],
                        "notify": ["gongshuai"],
                        "input_form": publish_options}

            publish_json = write_temp_json(pub_data, "/srv/w/temp/temp_files")
            cmd = ('rez-env --paths "//tools02.ds.com/pipeline/packages/int;//tools02.ds.com/pipeline/packages/ext;//tools02.ds.com/pipeline/packages" '
                   'PySide2 oct_publish -- batch_cli {}').format(publish_json)
            self.logger.info("submit to deadline cmd: {}".format(cmd))
            job_name = "Texture Outsource Recycle: {}".format(entity_name)
            _job = CommandLineJob(name=job_name)
            _job.set_command(cmd)
            _job.set_pool('render')
            _job.set_priority(priority=100)
            _job.set_job_error_limit(number=3)
            _job.set_task_timeout_minutes(minutes='60')
            _job.set_deny_list(['ls', 'liulu'])
            job_id = _job.submit()
            self.logger.info(f'创建manifest任务成功, 任务ID: {job_id}')

        except Exception as e:
            self.logger.error(e)
            return e