from lib.Deadline import DeadlineConnect as Connect
from datetime import datetime
from behaviour.utils.shotgun_method import get_task_context
import threading
import copy
import json
import requests
import os
import getpass
import subprocess
from logger.core import dl_logger as logger
from typing import Any

OCT_DEADLINE_URL104 = '192.168.30.3'
OCT_DEADLINE_PORT = str(8081)
MAX_RETRIES = 5

def get_connection(version='10.4'):
    if version == '10.4':
        CONN = Connect.DeadlineCon(OCT_DEADLINE_URL104, OCT_DEADLINE_PORT)
    else:
        CONN = Connect.DeadlineCon(OCT_DEADLINE_URL104, OCT_DEADLINE_PORT)
    return CONN


CONN = get_connection()

class DeadlineJob(object):
    plugin_name = None
    logger = logger

    def __init__(self, name='Deadline Job', frames='1-1', task_id=None, vendor_id=None):
        self.connection = CONN
        self.job_info:dict[str, Any] = {
            'Plugin': self.plugin_name
        }
        self.plugin_info = {}

        self.extra_info_key_value = dict()
        self.extra_info = dict()
        self.environment = dict()

        self.set_name(name)


        self.set_user('root')

        if vendor_id:
            try:
                self.set_ding_id(vendor_id)
            except:
                pass

        self.set_frame_range(frames)

        # now set default values
        self.set_secondary_pool('None')
        if task_id:
            task_ctx = get_task_context(task_id)
            if task_ctx:
                if isinstance(task_ctx, dict):
                    self.set_task_context(task_ctx)
                else:
                    self.logger.warning('task_id {} not found in shotgun, error {}'.format(task_id, task_ctx))

    def set_plugin_info(self, key, value):
        self.plugin_info[key] = value

    def set_name(self, name):
        self.job_info['Name'] = name

    def name(self):
        return self.job_info.get('Name')

    def set_batch_name(self, name):
        self.job_info['BatchName'] = name

    def batch_name(self):
        return self.job_info.get('BatchName')

    def set_user(self, username):
        self.job_info['UserName'] = username

    def set_frame_range(self, frames, chunk_size=None):
        self.job_info["Frames"] = frames.replace('.0', '')
        if chunk_size:
            self.job_info["ChunkSize"] = int(chunk_size)

    def set_priority(self, priority):
        self.job_info['Priority'] = priority

    def set_ding_id(self, ding_id):
        self.set_environment({'dingtalk_id': ding_id})

    def set_pool(self, pool):
        self.job_info['Pool'] = pool

    def set_secondary_pool(self, pool):
        """
        :param str pool:
        """
        self.job_info['SecondaryPool'] = pool

    def set_group(self, group):
        """
        Set group, `simple_job` for job that use less cpu and memory resource
        and can run multiple jobs in one render node.

        :param str group: options are `default`, `simple_job`
        """
        self.job_info['Group'] = group

    def set_comment(self, comment):
        self.job_info['Comment'] = comment

    def set_department(self, department):
        self.job_info["Department"] = department

    def set_task_timeout_minutes(self, minutes='0'):
        # 默认为 0, which is unlimited, <0 or greater>
        self.job_info["TaskTimeoutMinutes"] = str(minutes)

    def set_concurrent_tasks(self, task_num='1'):
        # <1-16> 一个worker同时最多能渲染几个任务
        self.job_info["ConcurrentTasks"] = task_num

    def set_dependencies(self, parents=None):
        if not isinstance(parents, (list, tuple)):
            parents = [parents]

        ids = []
        for p in parents:
            if isinstance(p, (str, int)):
                ids.append(str(p))

        self.job_info['JobDependencies'] = ','.join(ids)

    def set_extra_info_dict(self, extra_info):
        self.extra_info_key_value.update(extra_info)

    def set_extra_info(self, name, value):
        self.extra_info[name] = value

    def set_environment(self, environment):
        self.environment.update(environment)

    def set_job_error_limit(self, number):
        self.job_info['OverrideJobFailureDetection'] = True
        self.job_info['FailureDetectionJobErrors'] = number

    def set_task_error_limit(self, number):
        self.job_info['OverrideTaskFailureDetection'] = True
        self.job_info['FailureDetectionTaskErrors'] = number

    def set_machine_limit(self, number):
        self.job_info['MachineLimit'] = number

    # pipeline data
    def set_task_context(self, tc):
        if tc is None:
            return

        self.environment['OCT_TASK_ID'] = tc['task_id']

        self.set_project_name(tc['project_name'])
        self.set_entity_type(tc['entity_type'])
        self.set_entity_name(tc['entity_name'])
        self.set_step_name(tc['step_name'])
        self.set_task_name(tc['task_name'])

    def set_project_name(self, value):
        self.set_extra_info('ExtraInfo0', value)

    def set_entity_type(self, value):
        self.set_extra_info('ExtraInfo1', value)

    def set_entity_name(self, value):
        self.set_extra_info('ExtraInfo2', value)

    def set_step_name(self, value):
        self.set_extra_info('ExtraInfo3', value)

    def set_task_name(self, value):
        self.set_extra_info('ExtraInfo4', value)

    def set_component_name(self, value):
        self.set_extra_info('ExtraInfo5', value)

    def set_rez_packages(self, packages):
        if isinstance(packages, (list, tuple)):
            packages = ' '.join(packages)
        packages = packages.replace('platform-windows', '')
        self.extra_info_key_value['DEADLINE_REZ_REQUEST_PACKAGES'] = packages

    def set_rez_tools(self, tools):
        self.extra_info_key_value['DEADLINE_REZ_TOOLS'] = tools

    # def set_rez_packages_from_env(self):
    #     rez_resolve_new = get_rez_packages_from_env()
    #     self.set_rez_packages(rez_resolve_new)

    def set_event_opt_in(self, value):
        self.job_info['EventOI'] = value

    def set_allow_list(self, allow_list):
        """

        :param allow_list: work name connect by comma, e.g. 'wanjingwei,huiwentong'
        :return:
        """
        self.job_info['Allowlist'] = allow_list

    def set_deny_list(self, deny_list):
        """指定任务不使用这些农场机

        :param deny_list: 农场机名称列表, 或以逗号连接的字符串,
                          e.g. ['wanjingwei', 'huiwentong'] 或 'wanjingwei,huiwentong'
        :return:
        """
        if isinstance(deny_list, (list, tuple)):
            deny_list = ','.join(deny_list)
        self.job_info['Denylist'] = deny_list

    def submit_job_with_file(self, scene_file_path):
        for key, value in self.extra_info.items():
            self.job_info[key] = value
        for idx, key in enumerate(list(self.extra_info_key_value.keys())):
            info = '{}={}'.format(key, self.extra_info_key_value[key])
            self.job_info['ExtraInfoKeyValue%d' % idx] = info
        for idx, key in enumerate(list(self.environment.keys())):
            info = '{}={}'.format(key, self.environment[key])
            self.job_info['EnvironmentKeyValue%d' % idx] = info

        tries = MAX_RETRIES
        job_detail = ''
        while True and tries > 0:
            try:
                tries -= 1
                self.logger.info('Submitting job `{}` to deadline...'.format(self.name()))
                print(self.job_info, self.plugin_info)
                job_detail = self.connection.Jobs.SubmitJob(self.job_info, self.plugin_info, aux=[scene_file_path])
                print("\n job_detail -----{job_detail}-----------------\n".format(job_detail=job_detail))
                self.logger.debug(' - job info: {}'.format(job_detail))
                job_id = job_detail['_id']

            except Exception as e:
                self.logger.exception('submit error: {}\n'.format(e, job_detail))
                self.logger.warning('try to submit again, {} try left.'.format(tries))
            else:
                self.logger.info(' - job submitted with id: {}'.format(job_id))
                return job_id

    def submit(self, aux_files=[]):
        if not isinstance(aux_files, list):
            aux_files = [aux_files]
        # aux_files = [to_platform(f) for f in aux_files]

        for key, value in self.extra_info.items():
            self.job_info[key] = value
        for idx, key in enumerate(list(self.extra_info_key_value.keys())):
            info = '{}={}'.format(key, self.extra_info_key_value[key])
            self.job_info['ExtraInfoKeyValue%d' % idx] = info
        for idx, key in enumerate(list(self.environment.keys())):
            info = '{}={}'.format(key, self.environment[key])
            self.job_info['EnvironmentKeyValue%d' % idx] = info

        if aux_files and 'SceneFile' in self.job_info:
            self.job_info.pop('SceneFile')

        tries = MAX_RETRIES
        job_detail = ''
        while True and tries > 0:
            try:
                tries -= 1
                self.logger.info('Submitting job `{}` to deadline...'.format(self.name()))
                print(self.job_info, self.plugin_info)
                job_detail = self.connection.Jobs.SubmitJob(self.job_info, self.plugin_info, aux=aux_files)
                self.logger.debug(' - job info: {}'.format(job_detail))
                job_id = job_detail['_id']
            except Exception as e:
                self.logger.exception('submit error: {}\n'.format(e, job_detail))
                self.logger.warning('try to submit again, {} try left.'.format(tries))
            else:
                self.logger.info(' - job submitted with id: {}'.format(job_id))
                return job_id


class JobInfo(object):
    _status_code_mapping = {
        0: 'Unknown',
        1: 'Active',
        2: 'Suspended',
        3: 'Completed',
        4: 'Failed',
        6: 'Pending',
    }

    def __init__(self, raw_data):
        self._raw_data:dict = raw_data

    @property
    def id(self):
        return self.raw_data['_id']

    @property
    def raw_data(self):
        return self._raw_data

    @property
    def props(self):
        return self.raw_data['Props']

    @property
    def name(self):
        return self.props['Name']

    @property
    def batch_name(self):
        return self.props['Batch']

    @property
    def project_name(self):
        return self.props['Ex0']

    @property
    def entity_type(self):
        return self.props['Ex1']

    @property
    def entity_name(self):
        return self.props['Ex2']

    @property
    def pipeline_step(self):
        return self.props['Ex3']

    @property
    def task_name(self):
        return self.props['Ex4']

    @property
    def user_name(self):
        return self.props['User']

    @property
    def status_code(self):
        return self.raw_data['Stat']

    @property
    def status(self):
        """
        Stat (Status)::

            0 = Unknown
            1 = Active
            2 = Suspended
            3 = Completed
            4 = Failed
            6 = Pending

        https://docs.thinkboxsoftware.com/products/deadline/10.1/1_User%20Manual/manual/rest-jobs.html#job-property-values
        :return:
        """
        return self._status_code_mapping[self.status_code]

    @property
    def plugin_info(self):
        return self.props['PlugInfo']

    @property
    def plugin_name(self):
        return self.raw_data['Plug']

    @property
    def date_submit_str(self):
        return self.raw_data['Date']

    @property
    def date_start_str(self):
        return self.raw_data['DateStart']

    @property
    def date_complete_str(self):
        return self.raw_data['DateComp']

    @property
    def priority(self):
        return self.props['Pri']

    @property
    def group(self):
        return self.props['Group']

    @property
    def machineList(self):
        return self.props['ListedSlaves']

    @property
    def pool(self):
        return self.props['Pool']

    @property
    def secondary_pool(self):
        return self.props['SecPool']

    def fail(self):
        failed_job(self.id)

    def suspend(self):
        suspend_job(self.id)

    def resume(self):
        resume_job(self.id)

    def pending(self):
        pending_job(self.id)
    
    def requeue(self):
        requeue_job(self.id)

    def delete(self):
        CONN.Jobs.DeleteJob(self.id)

    def refresh(self):
        raw_data:dict = CONN.Jobs.GetJob(self.id) 
        self._raw_data = raw_data

    def change_pool(self, pool='none'):
        if pool not in CONN.Pools.GetPoolNames():
            raise Exception('Pool {} not found.'.format(pool))
        trans_data = self.raw_data
        trans_data['Props']['Pool'] = pool
        print(CONN.Jobs.SaveJob(trans_data))

    def change_secondary_pool(self, pool='none'):
        if pool not in CONN.Pools.GetPoolNames():
            raise Exception('Pool {} not found.'.format(pool))
        trans_data = self.raw_data
        trans_data['Props']['SecPool'] = pool
        print(CONN.Jobs.SaveJob(trans_data))

    def change_group(self, group='none'):
        if group not in CONN.Groups.GetGroupNames():
            raise Exception('Group {} not found.'.format(group))
        trans_data = self.raw_data
        trans_data['Props']['Group'] = group
        print(CONN.Jobs.SaveJob(trans_data))

    def set_priority(self, priority):
        priority = int(priority)
        result = max(0, min(priority, 100))
        trans_data = self.raw_data
        trans_data['Props']['Pri'] = result
        print(CONN.Jobs.SaveJob(trans_data))

    def change_machineLimit(self, machine_list):
        checked_machine_list = []
        all_slaves = CONN.Slaves.GetSlaveNames()
        for i in machine_list:
            if i in all_slaves:
                checked_machine_list.append(i)
        trans_data = self.raw_data
        trans_data['Props']['ListedSlaves'] = checked_machine_list
        print(CONN.Jobs.SaveJob(trans_data))
    
    def add_dependency(self, job_id):
        """
        添加一个依赖任务
        Args:
            job_id: 依赖任务的job_id
        Returns:
            True: 添加成功
            False: 添加失败
        """
        # 获取依赖任务字典
        current_dependencies = self.raw_data['Props'].get('Dep') or []

        # 获取依赖任务的id列表
        current_dependencies_id_list = [i.get('JobID') for i in current_dependencies]
        print('current_dependencies_id_list', current_dependencies_id_list)

        # 如果依赖任务的id列表中不包含当前任务的id, 则添加依赖任务
        if job_id not in current_dependencies_id_list:
            # 深拷贝当前任务数据
            temp_data = copy.deepcopy(self.raw_data)
            # 获取任务属性字典
            tprops = temp_data['Props']
            # 如果依赖任务字典为空, 则创建依赖任务字典
            if tprops.get('Dep') is None:
                tprops['Dep'] = []
            tprops['Dep'].append({'JobID': job_id})
            
            # 保存任务数据
            save_result= CONN.Jobs.SaveJob(temp_data)
            if save_result == 'Success':
                print('add dependency success')
                self.refresh()
                return True
            else:
                print('add dependency failed')
                return False
        else:
            print('job_id already in dependencies')
            return True



class CommandLineJob(DeadlineJob):
    plugin_name = 'CommandLine'

    def __init__(self, *args, **kwargs):
        super(CommandLineJob, self).__init__(*args, **kwargs)
        self.plugin_info = {
            'Shell': 'cmd',
            'ShellExecute': True,
            'StartupDirectory': '',
            'Arguments': '',
        }

    def set_command(self, command):
        self.logger.info('Set {} args: {}'.format(self.plugin_name, command))
        self.set_plugin_info('Arguments', command)



def get_job_info(job_id):
    """

    :param job_id:
    :return: instance of JobInfo
    :rtype JobInfo
    """
    job = CONN.Jobs.GetJob(job_id)
    job = JobInfo(job)
    return job


def get_job_id_from_keyword(keyword, unique=True):
    """
    根据提供的关键字, 查找Deadline Job, 返回id

    Args:
        keyword: 搜索关键字
        unique: 是否唯一, 如果为True, 则返回第一个匹配的job_id, 如果为False, 则返回所有匹配的job_id列表
    Returns:
        result: 匹配的job_id, 如果unique为True, 则返回第一个匹配的job_id, 如果为False, 则返回所有匹配的job_id列表
    """
    result = None if unique else []
    keyword = keyword.strip()

    jobs = CONN.Jobs.GetJobs()  # 取所有 jobs

    for job in jobs:
        job_name = (job.get("Props", {}).get("Name", "") or "")
        job_id = job.get("_id")

        if keyword in job_name and job_id:
            if unique:
                result =  job_id
                break
            result.append(job_id)

    return result


def get_job_task_infos(job_id, task_ids=None):
    tasks = CONN.Tasks.GetJobTasks(job_id)
    return tasks


def get_job_report(job_id):
    return CONN.JobReports.GetAllJobReports(job_id)


def get_job_report_contents(job_id):
    return CONN.JobReports.GetAllJobReportsContents(job_id)

def failed_job(job_id):
    CONN.Jobs.FailJob(job_id)

def suspend_job(job_id):
    CONN.Jobs.SuspendJob(job_id)

def resume_job(job_id):
    CONN.Jobs.ResumeJob(job_id)

def pending_job(job_id):
    CONN.Jobs.PendJob(job_id)

def requeue_job(job_id):
    CONN.Jobs.RequeueJob(job_id)


def send_job_info_to_user(job_id, ding_id, message, tips="由自动任务发布"):

    url = 'http://192.168.20.217:8080/ding/msg/simple?user_id={}'.format(ding_id)

    job = get_job_info(job_id)

    status = "❓❓❓"
    if job.status == 'Completed':
        status = '✔✔✔'
    elif job.status == 'Failed':
        status = '❌❌❌'
    elif job.status == 'Suspended':
        status = '❕❕❕'
    elif job.status == 'Pending':
        status = '⏸⏸⏸'
    elif job.status == 'Active':
        status = '▶▶▶'

    mk_message = """
# 🚀 来自农场的通知!
___
* ***任务id:***  {job_id}
* ***通知信息:***  {message}
***
| 任务信息 | 查询结果 |
| :--- | :---: | 
| batch名 | {batch_name_str} | 
| 任务名称 | {name} | 
| 任务状态 | {status} | 
| 任务插件 | {plugin_name} |
| 任务提交人 | {user_name} |
| 项目名称 | {project_name} |
| 任务提交时间 | {date_submit_str} |
***
> 备注：{tips} <br>

`发送时间： {datetime_now}`
""".format(job_id=job.id,
           message=message,
           batch_name_str=job.batch_name,
           name=job.name,
           status=job.status + status,
           plugin_name=job.plugin_name,
           user_name=job.user_name,
           project_name=job.project_name,
           date_submit_str=job.date_submit_str,
           tips=tips,
           datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    data = {'title': '来自农场的通知', 'text': mk_message}
    j_data = json.dumps(data)
    response = requests.post(url, data=j_data)
    return response.text

