import json
import shutil
import traceback
from pathlib import Path
from behaviour.utils.queueevent import Event
from behaviour.utils.deadline import CommandLineJob
from behaviour.utils.shotgun_method import find_task
from behaviour.dispatch_behav.core import StepComponent, StepProcessError
from behaviour.util_behav.utils import write_temp_json, to_win_path, is_valid_file_name, is_valid_project_name

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
            root = Path(self.event.manifest_file).parent
            upload_files = manifest_data['upload_files']
            previews = manifest_data['previews']
            asset_type = manifest_data['type']
            publish_options = manifest_data['publish_options']
            ma_file = publish_options['ma_file']
            entity_name = manifest_data['entity_name']
            task_step = manifest_data['task_step']
            task_name = manifest_data['task_name']

            if asset_type != 'asset':
                return "{}环节只接收资产，manifest 的 type 必须为小写 'asset'，当前为：{}".format("fur", asset_type)
            if not isinstance(upload_files, list) or not isinstance(previews, list):
                return "manifest 的 upload_files / previews 必须是列表"
            if not previews:
                return "previews 不能为空，至少需要一个预览文件"

            invalid_upload_files = []
            for file in upload_files:
                if is_valid_file_name(file):
                    continue
                invalid_upload_files.append(file)

            if len(invalid_upload_files) > 0:
                return "以下文件名存在非法字符（空格，中文，特殊字符等）, 请修改文件名：\n {}".format(
                    '\n'.join(invalid_upload_files))

            if upload_files:
                if not ma_file:
                    return "Publish 缺少 publish_options.ma_file"
                if '/' in ma_file or '\\' in ma_file:
                    return "ma 文件必须和 manifest 放在同一层，不能放在子目录：{}".format(ma_file)
                name_pattern = "{}.{}.{}".format(entity_name, task_step, task_name)
                if not ma_file.lower().endswith('.ma') or not is_valid_project_name(ma_file, name_pattern):
                    return "maya 文件的命名不规范！正确格式为：{}.vxxx.ma".format(name_pattern)

                xgen_dir = root / "xgen"
                xgen_dir = xgen_dir if xgen_dir.is_dir() else None
                if xgen_dir:
                    xgen_files = [str(p) for p in root.glob("*.xgen") if p.is_file()]
                    if len(xgen_files) > 1:
                        return "当前任务文件夹有下多个 .xgen 文件： {}".format("\n".join(xgen_files))
                    if not len(xgen_files):
                        return "当前任务文件夹下没有 .xgen 文件"
                    xgen_file = xgen_files[0]
                    xgen_file_format = "{}__{}_hair.xgen".format(str(Path(ma_file).stem), entity_name)
                    if Path(xgen_file).name != xgen_file_format:
                        return (".xgen 的名字正确格式为：{}, 请检查maya文件的名字 或 maya文件中xgen节点的名字是否为‘{}’！"
                                " ").format(xgen_file_format, "{}_hair".format(entity_name))
            return ''

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return 'manifest 检查出错：\n' + traceback.format_exc()

    def copy_to_w(self):
        """只拷贝 manifest 里列出的文件（upload_files + previews + manifest 本身 + maya ），保留相对路径，已存在则覆盖"""
        dst_folder = Path(self.event.dst_path) / self.event.version
        manifest = Path(self.event.manifest_file)
        manifest_data = self.get_manifest_data()
        publish_options = manifest_data['publish_options']
        ma_file = publish_options['ma_file']
        for rel in manifest_data['upload_files'] + manifest_data['previews'] + [manifest.name] + [ma_file]:
            src = manifest.parent / rel
            dst = dst_folder / rel
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            except Exception as e:
                raise RuntimeError("复制失败: {} -> {}".format(src, dst)) from e

    def publish_to_ddline(self):
        try:
            root = Path(self.event.dst_path) / self.event.version
            root = to_win_path(root)
            manifest_data = self.get_manifest_data()

            publish_options = manifest_data['publish_options']
            maya_file = publish_options.get('ma_file')
            if maya_file:
                publish_options['ma_file'] = str(Path(root) / maya_file)

            publish_type = 'Publish' if maya_file else 'Dailies'

            entity_name = manifest_data['entity_name']
            asset_type = manifest_data['type']
            task_name = manifest_data['task_name']
            project = manifest_data['project']
            task = find_task(project, entity_name, asset_type, task_name)

            pub_data = {"task_id": task["id"],
                        "dcc_file": str(Path(root)/ maya_file),
                        "version_num": "",
                        "user": "gongshuai",
                        "comment": manifest_data['comment'],
                        "publish_type": publish_type,
                        "publish_tag_id": 1141,
                        "preview_paths": [str(Path(root) / i) for i in manifest_data['previews']],
                        "notify": ["gongshuai", "jiajiaai"],
                        "input_form": publish_options,
                        "extra_data": {"is_outsourcing": True}}

            publish_json = write_temp_json(pub_data, "/srv/w/temp/temp_files")
            cmd = ('rez-env --paths "//tools02.ds.com/pipeline/packages/int;//tools02.ds.com/pipeline/packages/ext;//tools02.ds.com/pipeline/packages" '
                   'PySide2 oct_publish -- batch_cli {}').format(publish_json)
            self.logger.info("submit to deadline cmd: {}".format(cmd))
            job_name = "Fur Outsource Recycle: {} {} outsource root:{}".format(entity_name, publish_type, root)
            _job = CommandLineJob(name=job_name)
            _job.set_command(cmd)
            _job.set_pool('render')
            _job.set_priority(priority=100)
            _job.set_job_error_limit(number=1)
            _job.set_task_timeout_minutes(minutes='60')
            _job.set_deny_list(['ls', 'liulu'])
            job_id = _job.submit()
            self.logger.info(f'创建manifest任务成功, 任务ID: {job_id}')

        except Exception as e:
            self.logger.error(traceback.format_exc())
            msg = '提交 Deadline 发布任务失败：{}'.format(e)
            self.send_message(False, msg + self.event.summery())
            raise StepProcessError(msg, self.event) from e