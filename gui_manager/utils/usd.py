"""USD 解析. pxr 在函数内延迟导入, 不影响不用 USD 的环节启动."""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=None)
def usd_deps(entry: str) -> tuple[frozenset[str], tuple[str, ...]]:
    """按默认变体 (即最新版本) 打开 stage, 收集实际参与合成的 layer 和贴图.

    Args:
        entry (str): 入口 usda 的本地路径

    Returns:
        tuple[frozenset[str], tuple[str, ...]]: (依赖文件路径集合, 解析不到的 "prim 路径: 写入的路径")
            场景按资产名命名 prim, 从 prim 路径即可看出是哪个资产
    """
    from pxr import Sdf, Usd  # 延迟导入, 不影响其他环节启动

    stage = Usd.Stage.Open(str(entry), Usd.Stage.LoadAll)
    files = {layer.realPath for layer in stage.GetUsedLayers() if layer.realPath}
    unresolved = []
    for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
        for attr in prim.GetAttributes():
            if attr.GetTypeName() != Sdf.ValueTypeNames.Asset:
                continue
            value = attr.Get()
            if not value or not value.path:
                continue
            # ponytail: <UDIM> 贴图解析不到会进 unresolved, 实际遇到再展开
            if value.resolvedPath:
                files.add(value.resolvedPath)
            else:
                unresolved.append(f"{prim.GetPath()}: {value.path}")
    return frozenset(files), tuple(unresolved)

