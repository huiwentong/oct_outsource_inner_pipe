import json
import shutil
import traceback
from pathlib import Path
from behaviour.dispatch_behav.core import StepComponent
from behaviour.utils.queueevent import Event
from behaviour.util_behav.utils import is_valid_file_name, is_valid_project_name

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
            previews = manifest_data['previews']
            asset_type = manifest_data['type']
            publish_options = manifest_data['publish_options']
            ma_file = publish_options['ma_file']
            entity_name = manifest_data['entity_name']
            task_step = manifest_data['task_step']
            task_name = manifest_data['task_name']

            if asset_type != 'asset':
                return "{}环节只接收资产，manifest 的 type 必须为小写 'asset'，当前为：{}".format("mod", asset_type)
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

            return ''

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return 'manifest 检查出错：\n' + traceback.format_exc()

    def copy_to_w(self):
        """只拷贝 manifest 里列出的文件（upload_files + previews + manifest 本身 + maya + zb 文件），保留相对路径，已存在则覆盖"""
        dst_folder = Path(self.event.dst_path) / self.event.version
        manifest = Path(self.event.manifest_file)
        manifest_data = self.get_manifest_data()
        publish_options = manifest_data['publish_options']
        ma_file = publish_options['ma_file']
        zb_file = publish_options.get('zb_file', '')
        projects = [ma_file]
        if zb_file:
            projects.append(zb_file)

        for rel in manifest_data['upload_files'] + manifest_data['previews'] + [manifest.name] + projects:
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
        return super().publish_to_ddline()