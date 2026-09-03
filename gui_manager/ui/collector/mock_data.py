"""collector UI 当前使用的 mock 数据层。

TODO(后续补充): 以下数据全部为演示用 mock，
     后续把 *_mock 替换为真实的数据库 / 服务查询即可。
"""

from __future__ import annotations

# 项目候选列表
PROJECTS: list[dict[str, str]] = [
    {"id": "mk2", "name": "MK2 项目"},
    {"id": "mko", "name": "MKO 项目"},
]


def project_name(project_id: str) -> str:
    for proj in PROJECTS:
        if proj["id"] == project_id:
            return proj["name"]
    return project_id


def get_project_entities_mock(project_id: str) -> list[str]:
    """返回项目下可抓包的实体 / 资产列表（mock）。"""
    _MOCK_ENTITIES = {
        "mk2": [
            "char_mk2_hero",
            "char_mk2_boss",
            "prop_mk2_gun",
            "veh_mk2_tank",
            "shot_mk2_sq010_sc010",
            "shot_mk2_sq010_sc020",
        ],
        "mko": [
            "char_mko_master",
            "prop_mko_sword",
            "env_mko_forest",
            "shot_mko_sq030_sc040",
        ],
    }
    return list(_MOCK_ENTITIES.get(project_id, []))


def get_vendor_names_mock() -> list[str]:
    """外包方列表（mock），后续从 ftpuser / 权限服务查询。"""
    return [
        "示例-星火数码",
        "示例-岚山动画",
        "示例-微光工作室",
        "示例-像素工厂",
    ]
