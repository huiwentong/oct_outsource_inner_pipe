
from __future__ import annotations
from utils import shotgun
from utils.permissionmanager import get_all_user as pm_get_all_user

PROJECTS: list[dict[str, str]] = shotgun.get_all_projects()


def project_name(project_id: str) -> str:
    for proj in PROJECTS:
        if proj["id"] == project_id:
            return proj["name"]
    return project_id


def get_project_entities_mock(project_id: str) -> list[str]:
    return shotgun.get_project_entities_name(project_id)


def get_vendor_names_mock() -> list[str]:
    ret = pm_get_all_user()
    return [v['name'] for v in ret.get("users")]


if __name__ == "__main__":
    print(get_vendor_names_mock())