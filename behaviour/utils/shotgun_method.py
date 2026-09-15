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
    'Textrue': 'tex',
    'Fur': 'fur',
    'cfx': 'cfx',
    'CFX': 'dyn',
    'ly': 'lay',
    'An': 'ani',
    'Ef': 'efx',
    'lg': 'lgt',
    'Cm': 'cmp',
}


class ThreadSafeShotgun:
    def __init__(self, base_url=None, script_name=None, api_key=None, shotgun_ins=None,  **kwargs):
        self.lock = threading.Lock()
        print("Initializing Shotgun connection...")
        if shotgun_ins:
            self._sg = shotgun_ins
        else:
            self._sg = shotgun_api3.Shotgun(base_url, script_name, api_key, **kwargs)


    def find(self, entity_type, filters, fields, **kwargs):
        with self.lock:
            try:
                result = self._sg.find(entity_type, filters, fields, **kwargs)
                return result
            except Exception as e:
                raise

    def create(self, *arges, **kwargs):
        with self.lock:
            return self._sg.create(*arges, **kwargs)

    def update(self, *arges, **kwargs):
        with self.lock:
            return self._sg.update(*arges, **kwargs)

    def delete(self, *arges, **kwargs):
        with self.lock:
            return self._sg.delete(*arges, **kwargs)

    def find_one(self, *arges, **kwargs):
        with self.lock:
            return self._sg.find_one(*arges, **kwargs)



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


def check_shotgun_entitys(project, entity_name, asset_type, task_name, task_step) -> str:
    sg = FastSg().client
    try:
        task_filters = [
            ['project', 'name_is', project],
            ['entity', 'name_is', entity_name],
            ['entity', 'type_is', asset_type],
            ['content', 'is', task_name]
        ]

        fields = ['step', 'id']

        task = sg.find_one('Task', task_filters, fields)

        if not task:
            return f'can not find task {project} {entity_name} {task_name}'

        if task_step != STEP_MAP[task['step']['name']]:
            return f'manifest中所指定的step {task_step}与Sg中找到的step: {STEP_MAP[task['step']['name']]}不一致'

        return ''

    except Exception:
        return traceback.format_exc()

