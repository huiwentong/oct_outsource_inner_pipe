"""I 盘路径与 FTP 路径的换算.

I:/projects/{项目}/{asset|shot}/{资产类型|场次}/{实体}/... ↔ /oct/{项目}/{asset|shot}/{实体}/...
"""
from __future__ import annotations

import re

# I:/projects/{项目}/{asset|shot}/{资产类型|场次}/{实体}/{剩余部分}
_ENTITY_RE = re.compile(r"^[a-z]:/projects/([^/]+)/(asset|shot)/([^/]+)/([^/]+)(?:/(.*))?$", re.I)


def _split(path: str):
    """匹配 I 盘路径. 先把反斜杠统一成 /, 兼容 Windows 路径和 SG 返回的路径.

    Args:
        path (str | Path): 本地路径, 如 ``I:/projects/mk2/asset/prp/ds_pifeng_a/rig/a.ma``

    Returns:
        re.Match | None: 不匹配返回 None;
            m.groups() 为 (项目, asset|shot, 资产类型|场次, 实体, 剩余部分), 剩余部分可能为 None
    """
    return _ENTITY_RE.match(str(path).replace("\\", "/"))


def to_ftp(path: str) -> str | None:
    """I 盘路径 → FTP 路径 (去掉资产类型 / 场次这一层).

    Args:
        path (str | Path): I 盘本地路径

    Returns:
        str | None: FTP 路径, 如 ``/oct/mk2/asset/ds_pifeng_a/rig/a.ma``; 不在 I:/projects 下返回 None
    """
    m = _split(path)
    if not m:
        return None
    project, kind, _, name, rest = m.groups()
    return f"/oct/{project}/{kind}/{name}" + (f"/{rest}" if rest else "")


def entity_root(path: str) -> tuple[str, str] | None:
    """取路径所属实体的根目录.

    Args:
        path (str | Path): 实体目录或其下任意文件的 I 盘路径

    Returns:
        tuple[str, str] | None: (实体在 I 盘的根目录, 实体在 FTP 的根目录); 不在 I:/projects 下返回 None
    """
    m = _split(path)
    if not m:
        return None
    project, kind, mid, name, _ = m.groups()
    return f"I:/projects/{project}/{kind}/{mid}/{name}", f"/oct/{project}/{kind}/{name}"


def strip_version(name: str) -> str:
    """去掉名称末尾的版本号.

    Args:
        name (str): 如 ``dasheng.rig.rigging_nemo.v039``

    Returns:
        str: 如 ``dasheng.rig.rigging_nemo``; 没有版本号则原样返回
    """
    return re.sub(r"\.v\d+$", "", name)


def relies(ftp_paths) -> tuple[list[str], list[str]]:
    """从 FTP 路径反推权限组: 第 4 层是实体, 第 5 层是环节 (versionwatch 按这两层挂组).

    Args:
        ftp_paths (Iterable[str]): FTP 路径, 如 ``/oct/mk2/asset/ds_pifeng_a/rig/a.ma``

    Returns:
        tuple[list[str], list[str]]: (实体名列表, 环节名列表), 均已去重排序;
            只到实体层的路径 (如 default_path.json) 不计入
    """
    assets, steps = set(), set()
    for p in ftp_paths:
        parts = p.strip("/").split("/")
        if len(parts) >= 6:  # oct/项目/类型/实体/环节/...
            assets.add(parts[3])
            steps.add(parts[4])
    return sorted(assets), sorted(steps)


if __name__ == "__main__":
    # 路径映射自检: uv run python -m utils.paths
    rig = r"i:\projects\mk2\asset\prp\ds_pifeng_a\rig\ds_pifeng_a.rig.rigging\ds_pifeng_a.ma"
    assert to_ftp(rig) == "/oct/mk2/asset/ds_pifeng_a/rig/ds_pifeng_a.rig.rigging/ds_pifeng_a.ma"
    assert to_ftp("I:/projects/mk2/shot/s99/s990050/lay/s990050.lay.usda") == "/oct/mk2/shot/s990050/lay/s990050.lay.usda"
    assert to_ftp("W:/projects/lib/x.png") is None
    assert entity_root(rig) == ("I:/projects/mk2/asset/prp/ds_pifeng_a", "/oct/mk2/asset/ds_pifeng_a")
    assert entity_root("I:/projects/mk2/shot/s99/s990050") == ("I:/projects/mk2/shot/s99/s990050", "/oct/mk2/shot/s990050")
    assert strip_version("dasheng.rig.rigging_nemo.v039") == "dasheng.rig.rigging_nemo"
    assert relies([
        "/oct/mk2/asset/ds_pifeng_a/rig/a.ma",
        "/oct/mk2/shot/s990050/lay/b.usda",
        "/oct/mk2/asset/ds_pifeng_a/default_path.json",  # 实体层文件不算环节
    ]) == (["ds_pifeng_a", "s990050"], ["lay", "rig"])
    print("paths 自检通过")
