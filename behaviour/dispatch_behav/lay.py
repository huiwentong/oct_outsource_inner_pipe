# -*- coding: utf-8 -*-
"""镜头 Layout 收包（rough_layout）；blk / ani 继承本模块，对齐 oct_publish 的 lay -> blk -> ani"""
import hashlib
import json
import re
import shutil
import traceback
from pathlib import Path

from behaviour.utils.queueevent import Event
from behaviour.utils.deadline import CommandLineJob
from behaviour.utils.shotgun_method import find_task
from behaviour.dispatch_behav.core import StepComponent, StepProcessError
from behaviour.util_behav.utils import write_temp_json, to_win_path, is_valid_project_name, is_valid_file_name

PUBLISH_TAG_ID = 283  # 正式
# ponytail: 先写死，外包商在 SG 上有 HumanUser 后改为按外包商取
PUBLISH_USER = 'zhanglingyun'  # SG login，发布者；农场发布失败时 oct_publish 通知此人
NOTIFY = ['zhanglingyun']  # SG login 列表，发布成功后 oct_publish 通知；可留空
# ma 里 Stage 引用 usda 的路径，和 oct_publish rename_outsource_version 改写的范围保持一致
USDA_REF = re.compile(rb'"[^"\r\n]*maya_usd[^"\r\n]*\.usda"')


class Component(StepComponent):
    LABEL = 'Layout'
    PRIMARY_TASK = 'rough_layout'

    def __init__(self, event: Event) -> None:
        super().__init__(event)

    def get_manifest_data(self) -> dict:
        with Path(self.event.manifest_file).open('r', encoding='utf-8') as f:
            return json.load(f)

    def extra_input_form(self, task_name: str) -> dict:
        """Publish 时 input_form 的额外字段，blk / ani 覆盖"""
        return {}

    def check_extra(self):
        # 任何异常都转成错误说明返回，不能让异常逃出去阻塞 behaviour pipeline
        try:
            return self._check()
        except Exception:
            self.logger.error(traceback.format_exc())
            return 'manifest 检查出错：\n' + traceback.format_exc()

    def _check(self):
        data = self.get_manifest_data()
        entity_name = data['entity_name']
        task_step = data['task_step']
        task_name = data['task_name']
        upload_files = data['upload_files']
        previews = data['previews']
        ma_file = (data.get('publish_options') or {}).get('ma_file')

        # 回收目录名取自 type，oct_publish 的 check_work_file 按小写 shot 比较
        if data['type'] != 'shot':
            return "{}环节只接收镜头，manifest 的 type 必须为小写 'shot'，当前为：{}".format(self.LABEL, data['type'])
        if not task_name.startswith(self.PRIMARY_TASK):
            return "{}环节只接收 {} 任务，当前为：{}".format(self.LABEL, self.PRIMARY_TASK, task_name)
        if not isinstance(upload_files, list) or not isinstance(previews, list):
            return "manifest 的 upload_files / previews 必须是列表"
        if not previews:
            return "previews 不能为空，至少需要一个预览文件"

        invalid = [f for f in upload_files + previews if not is_valid_file_name(f)]
        if invalid:
            return "以下文件名存在非法字符（空格，中文，特殊字符等），请修改文件名：\n{}".format('\n'.join(invalid))

        if upload_files:
            if not ma_file:
                return "Publish 缺少 publish_options.ma_file"
            if ma_file not in upload_files:
                return "ma_file 未包含在 upload_files 中：{}".format(ma_file)
            # 回收后路径必须正好 9 段，ma 放子目录会多一段，check_work_file 不认
            if '/' in ma_file or '\\' in ma_file:
                return "ma 文件必须和 manifest 放在同一层，不能放在子目录：{}".format(ma_file)
            name_pattern = "{}.{}.{}".format(entity_name, task_step, task_name)
            # 只收 .ma：农场要按文本改写 ma 里的 usda 引用，.mb 改不了
            if not ma_file.lower().endswith('.ma') or not is_valid_project_name(ma_file, name_pattern):
                return "maya 文件的命名不规范！正确格式为：{}.vxxx.ma".format(name_pattern)
            error = self._check_ma(ma_file, upload_files)
            if error:
                return error
        return ''

    def _check_ma(self, ma_file: str, upload_files: list) -> str:
        """检查外包回传的原始 ma：
        1. 外包检查工具生成的校验文件 <ma 文件名>.<md5>.txt 必须写在 upload_files 里，且 md5 与 ma 一致
        2. Stage 引用了 maya_usd 下的 usda 时，同名 usda 必须一起回传，农场会把它另存成 SG 新版本名
        """
        files = [f.replace('\\', '/') for f in upload_files]
        hash_pattern = re.compile(re.escape(ma_file) + r'\.([0-9a-fA-F]{32})\.txt')
        hashes = [m.group(1).lower() for m in map(hash_pattern.fullmatch, files) if m]
        if not hashes:
            return "缺少检查工具生成的校验文件 {}.<md5>.txt，请运行检查工具后把 txt 加入 upload_files 一起回传".format(ma_file)
        if len(hashes) > 1:
            return "upload_files 里只能有一个 {} 的校验文件，当前有 {} 个".format(ma_file, len(hashes))

        # 逐行读一遍，同时算 md5 和查找 usda 引用，避免大 ma 读两次或整个读进内存
        md5 = hashlib.md5()
        has_usda_ref = False
        with (Path(self.event.manifest_file).parent / ma_file).open('rb') as fh:
            for line in fh:
                md5.update(line)
                if not has_usda_ref:
                    has_usda_ref = bool(USDA_REF.search(line))
        if md5.hexdigest() != hashes[0]:
            return "ma 文件与检查工具生成的校验文件不一致，检查后文件被修改过，请重新运行检查工具：{}".format(ma_file)

        usda = 'maya_usd/{}.usda'.format(Path(ma_file).stem)
        if has_usda_ref and usda not in files:
            return "ma 文件引用了 maya_usd 下的 usda，请把 {} 加入 upload_files 一起回传".format(usda)
        return ''

    def copy_to_w(self):
        """只拷贝 manifest 里列出的文件（upload_files + previews + manifest 本身），保留相对路径，已存在则覆盖"""
        dst_folder = Path(self.event.dst_path) / self.event.version
        manifest = Path(self.event.manifest_file)
        data = self.get_manifest_data()
        for rel in data['upload_files'] + data['previews'] + [manifest.name]:
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
        # 失败时自己发通知并转成 StepProcessError：core.process 不为发布失败发通知，普通异常还会阻塞 pipeline
        try:
            return self._submit()
        except Exception as e:
            self.logger.error(traceback.format_exc())
            msg = '提交 Deadline 发布任务失败：{}'.format(e)
            self.send_message(False, msg + self.event.summery())
            raise StepProcessError(msg, self.event) from e

    def _submit(self):
        data = self.get_manifest_data()
        root = to_win_path('{}/{}'.format(self.event.dst_path, self.event.version))
        entity_name = data['entity_name']
        task_name = data['task_name']
        upload_files = data['upload_files']
        previews = data['previews']

        publish_type = 'Publish' if upload_files else 'Dailies'
        if publish_type == 'Publish':
            ma_file = data['publish_options']['ma_file']
            dcc_file = '{}/{}'.format(root, ma_file)
            input_form = {'ma_file': dcc_file}
            input_form.update(self.extra_input_form(task_name))
        else:
            # Dailies 不需要 Maya，dcc_file 传空走 cmd 模式
            dcc_file = None
            input_form = {}

        task = find_task(data['project'], entity_name, data['type'], task_name)
        pub_data = {
            'task_id': task['id'],
            'dcc_file': dcc_file,
            # 外包商不知道 SG 版本：传空让 batch_cli 在农场上取 SG 下一版本号，
            # Publish 时 oct_publish 的 rename_outsource_version 再把 ma / usda 另存成这个版本名
            'version_num': '',
            'extra_data': {'is_outsourcing': True},
            'user': PUBLISH_USER,
            'comment': data['comment'],
            'publish_type': publish_type,
            'publish_tag_id': PUBLISH_TAG_ID,
            'preview_paths': ['{}/{}'.format(root, p) for p in previews],
            'notify': NOTIFY,
            'input_form': input_form,
        }
        self.logger.info('{} publish data: {}'.format(self.LABEL, pub_data))

        publish_json = write_temp_json(pub_data, '/srv/w/temp/temp_files')
        cmd = ('rez-env --paths "//tools02.ds.com/pipeline/packages/int;//tools02.ds.com/pipeline/packages/ext;'
               '//tools02.ds.com/pipeline/packages" PySide2 oct_publish -- batch_cli {}').format(publish_json)
        self.logger.info('submit to deadline cmd: {}'.format(cmd))

        job = CommandLineJob(name='{} Outsource Recycle: {} {} {}'.format(
            self.LABEL, entity_name, publish_type, self.event.version))
        job.set_command(cmd)
        job.set_pool('cache')
        job.set_priority(priority=100)
        job.set_job_error_limit(number=1)
        job.set_task_timeout_minutes(minutes='1440')  # 1 天，缓存输出可能很久
        job.set_deny_list(['ls', 'liulu'])
        job_id = job.submit()
        if not job_id:
            raise RuntimeError('未获取到 Deadline job_id')
        self.logger.info('创建 {} 发布任务成功, 任务ID: {}'.format(self.LABEL, job_id))
        return job_id
