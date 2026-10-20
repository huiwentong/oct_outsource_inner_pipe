import json
from pathlib import Path
from behaviour.dispatch_behav.core import StepComponent
from behaviour.utils.queueevent import Event
from behaviour.util_behav.utils import is_valid_file_name

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
            assert isinstance(upload_files, list), \
                "manifest json文件中 ‘upload_files’ 的值应该是个列表：例：‘upload_files’: ['test01.png', 'test02.png']"

            publish_options = manifest_data['publish_options']
            ma_file = publish_options['ma_file']

            invalid_upload_files = []
            if not is_valid_file_name(ma_file):
                invalid_upload_files.append(ma_file)

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
        return super().publish_to_ddline()