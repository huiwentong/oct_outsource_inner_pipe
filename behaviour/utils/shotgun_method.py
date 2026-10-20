import shotgun_api3
import threading
import gc
import getpass
import os
import traceback

SERVER_URL = os.environ['sg_server_url']
script_name = os.environ['sg_script_name']
api_key = os.environ['sg_api_key']

STEP_MAP = {
    '绑定': 'rig',
    'mod': 'mod',
    'Texture': 'tex',
    'Fur': 'fur',
    'cfx': 'cfx',
    'CFX': 'dyn',
    'ly': 'lay',
    'An': 'ani',
    'Bk': 'blk',
    'Ef': 'efx',
    'lg': 'lgt',
    'Cm': 'cmp',
}


class ThreadSafeShotgun:
    def __init__(self, base_url=None, script_name=None, api_key=None, shotgun_ins=None,  **kwargs):
        self.lock = threading.Lock()
        self.max_try_times = 5
        print("Initializing Shotgun connection...")
        if shotgun_ins:
            self._sg = shotgun_ins
        else:
            self._sg = shotgun_api3.Shotgun(base_url, script_name, api_key, **kwargs)


    def find(self, entity_type, filters, fields, **kwargs):
        try_times = 0
        errors = ''
        with self.lock:
            while try_times < self.max_try_times:
                try:
                    result = self._sg.find(entity_type, filters, fields, **kwargs)
                    return result
                except:
                    errors += f'error time {try_times}: {traceback.format_exc()}\n'
                    try_times += 1
            raise RuntimeError(errors)


    def create(self, *arges, **kwargs):
        try_times = 0
        errors = ''
        with self.lock:
            while try_times < self.max_try_times:
                try:
                    return self._sg.create(*arges, **kwargs)
                except:
                    errors += f'error time {try_times}: {traceback.format_exc()}\n'
                    try_times += 1
            raise RuntimeError(errors)



    def update(self, *arges, **kwargs):
        try_times = 0
        errors = ''
        with self.lock:
            while try_times < self.max_try_times:
                try:
                    return self._sg.update(*arges, **kwargs)
                except:
                    errors += f'error time {try_times}: {traceback.format_exc()}\n'
                    try_times += 1
            raise RuntimeError(errors)

    def delete(self, *arges, **kwargs):
        try_times = 0
        errors = ''
        with self.lock:
            while try_times < self.max_try_times:
                try:
                    return self._sg.delete(*arges, **kwargs)
                except:
                    errors += f'error time {try_times}: {traceback.format_exc()}\n'
                    try_times += 1
            raise RuntimeError(errors)


    def find_one(self, *arges, **kwargs):
        try_times = 0
        errors = ''
        with self.lock:
            while try_times < self.max_try_times:
                try:
                    return self._sg.find_one(*arges, **kwargs)
                except:
                    errors += f'error time {try_times}: {traceback.format_exc()}\n'
                    try_times += 1
            raise RuntimeError(errors)



class FastSg(object):
    _instance = None
    no_need_to_init = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FastSg, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not FastSg.no_need_to_init:
            shotgun = self.get_shogun()
            if not shotgun:
                self.client = ThreadSafeShotgun(base_url=SERVER_URL, script_name=script_name, api_key=api_key)
            else:
                self.client = ThreadSafeShotgun(shotgun_ins=shotgun)
        FastSg.no_need_to_init = True

    def get_shogun(self):
        objs = gc.get_objects()
        for o in objs:
            try:
                if isinstance(o, shotgun_api3.Shotgun):
                    print('find shotgun!')
                    return o
            except Exception as e:
                continue
        return None

def find_task(project, entity_name, asset_type, task_name):

    sg = FastSg().client
    task_filters = [
        ['project', 'name_is', project],
        ['entity', 'name_is', entity_name],
        ['entity', 'type_is', asset_type],
        ['content', 'is', task_name]
    ]

    fields = ['step', 'id']
    task = sg.find_one('Task', task_filters, fields)

    return task


def check_shotgun_entitys(project, entity_name, asset_type, task_name, task_step) -> str:

    try:
        task = find_task(project, entity_name, asset_type, task_name)

        if not task:
            return f'can not find task {project} {entity_name} {task_name}'
        map_step = STEP_MAP[task['step']['name']]
        if task_step != map_step:
            return f'manifest中所指定的step {task_step}与Sg中找到的step: {map_step}不一致'

        return ''

    except Exception:
        return traceback.format_exc()


def get_task_context(task_id):
    sg = FastSg().client
    try:
        task_filters = [
            ['id', 'is', task_id],
        ]

        fields = ['step', 'id', 'content', 'entity', 'project']
        ret = sg.find_one('Task', task_filters, fields)

        tc = {
            'task_id': ret['id'],
            'task_name': ret['content'],
            'step_name': ret['step']['name'],
            'entity_id': ret['entity']['id'],
            'entity_name': ret['entity']['name'],
            'entity_type': ret['entity']['type'],
            'project_id': ret['project']['id'],
            'project_name': ret['project']['name']
        }
    except Exception:
        return traceback.format_exc()
    return tc