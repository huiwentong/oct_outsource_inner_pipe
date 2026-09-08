# -*- coding:utf-8 -*-
"""
===========================================
项目名称: int
文件: fast_sg
作者: huiwentong
创建时间: 2025/9/11
版本: 1.0.0
联系方式: 1120267329@qq.com
描述:
    ******
===========================================
"""
import shotgun_api3
import threading
import gc
import getpass
from utils.config import get_config

SERVER_URL = get_config()['sg_server_url']
script_name = get_config()['sg_script_name']
api_key = get_config()['sg_api_key']

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



def get_all_projects() -> list[dict]:
    sg = FastSg().client
    
    projects = sg.find('Project', 
        [
            ['sg_status', 'is', 'Active'],
            ['sg_res', 'is_not', ''],
        ], 
        ['code', 'name', 'id']
    )
    return projects


def get_project_entities_name(project_id: str) -> list[str]:
    """返回项目下可抓包的实体 / 资产列表。"""
    sg = FastSg().client
    asset_entities = sg.find('Asset', 
        [
            ['project', 'is', {'type': 'Project', 'id': project_id}],
        ], 
        ['code', 'type']
    )
    shot_entities = sg.find('Shot', 
            [
                ['project', 'is', {'type': 'Project', 'id': project_id}],
            ], 
            ['code', 'type']
        )
    
    return [[e['code'], e['type'].lower()] for e in asset_entities] + [[e['code'], e['type'].lower()] for e in shot_entities]





if __name__ == '__main__':
    print(FastSg().client)
    print(FastSg().client)
    print(FastSg().client)