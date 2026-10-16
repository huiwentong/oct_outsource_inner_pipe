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
from functools import lru_cache
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


def get_asset_type(asset_name: str, project_name: str) -> str|None:
    """返回资产类型列表。"""
    sg = FastSg().client
    asset = sg.find_one('Asset', [['project', 'name_is', project_name],['code', 'is', asset_name]], ['sg_asset_type'])

    return asset.get('sg_asset_type') if asset else None


# 注意: SG 和 USD 结果在本次运行内缓存, 工具开着期间有新发布要重启才能看到
@lru_cache(maxsize=None)
def latest_publish(entity: str, task: str, project: str) -> dict | None:
    """查最新 Publish 版本, 和 oct ORM 的 Task.latest_published_version 逻辑一致.

    Args:
        entity (str): 资产或镜头名
        task (str): SG 任务名, 如 ``rigging`` / ``rough_layout``
        project (str): 项目名

    Returns:
        dict | None: SG Version, 含 ``sg_path_to_v_folder``, ``sg_path_to_geometry``; 没有发布返回 None
    """
    return FastSg().client.find_one("Version",
        [
            ["entity", "name_is", entity],
            ["project", "name_is", project],
            ["sg_task", "name_is", task],
            ["sg_version_type", "is", "Publish"],
        ],
        ["sg_path_to_v_folder", "sg_path_to_geometry"],
        order=[{"field_name": "id", "direction": "desc"}],
    )


def _asset_types(names: list[str], project: str) -> tuple[tuple[str, str], ...]:
    """按资产名批量查 sg_asset_type, 返回 ((资产名, sg_asset_type), ...)."""
    if not names:
        return ()
    found = FastSg().client.find("Asset", [["code", "in", names], ["project", "name_is", project]], ["code", "sg_asset_type"])
    return tuple((a["code"], a["sg_asset_type"]) for a in found)


@lru_cache(maxsize=None)
def sequence_assets(sequence_id: int, project: str) -> tuple[tuple[str, str], ...]:
    """查场次关联的资产. 按场次缓存, 同一场次的多个镜头只查一次.

    Args:
        sequence_id (int): Sequence 的 id
        project (str): 项目名

    Returns:
        tuple[tuple[str, str], ...]: ((资产名, sg_asset_type), ...); 场次无资产返回空元组
    """
    data = FastSg().client.find_one("Sequence", [["id", "is", sequence_id]], ["assets"])
    return _asset_types([a["name"] for a in (data or {}).get("assets") or []], project)


@lru_cache(maxsize=None)
def shot_assets(shot: str, project: str) -> tuple[tuple[str, str, bool], ...]:
    """查镜头关联的资产, 以及镜头所属场次关联的资产.

    制片开新场次时通常只在 Sequence 上关联资产, 不会给每个镜头都关联, 所以两边都要收.

    Args:
        shot (str): 镜头名, 如 ``s990050``
        project (str): 项目名

    Returns:
        tuple[tuple[str, str, bool], ...]: ((资产名, sg_asset_type, 是否仅来自场次), ...),
            按资产名去重, 镜头资产在前; 镜头不存在或两边都无资产返回空元组
    """
    data = FastSg().client.find_one(
        "Shot", [["code", "is", shot], ["project", "name_is", project]], ["assets", "sg_sequence"]
    ) or {}
    linked_to_shot = _asset_types([a["name"] for a in data.get("assets") or []], project)
    sequence = data.get("sg_sequence")
    linked_to_sequence = sequence_assets(sequence["id"], project) if sequence else ()

    result = []
    for name, asset_type in linked_to_shot:
        result.append((name, asset_type, False))

    shot_asset_names = {name for name, _ in linked_to_shot}
    for name, asset_type in linked_to_sequence:
        if name in shot_asset_names:  # 镜头上已关联过, 不重复收
            continue
        result.append((name, asset_type, True))

    return tuple(result)  # 用 tuple 而不是 list: 结果会被 lru_cache 缓存共用, 不能被调用方修改


if __name__ == '__main__':
    print(FastSg().client)
    print(FastSg().client)
    print(FastSg().client)