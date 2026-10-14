from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from components.core import register
from components.lay import LayComponent, _existing
from utils.shotgun import latest_publish
from utils.usd import usd_deps


@lru_cache(maxsize=None)
def collect_shot(shot: str, project: str) -> tuple[frozenset[str], tuple[str, ...]]:
    """收集镜头文件: <shot>.asb_all.usda / <shot>.lay.usda 及其依赖, 
       以及 rough_layout / blocking / animation 的 ma 文件.

    Args:
        shot (str): 镜头名
        project (str): 项目名

    Returns:
        tuple[frozenset[str], tuple[str, ...]]: (本地文件路径集合, 提示列表)

    Raises:
        ValueError: 镜头没有 rough_layout 发布, 或发布记录在但 ma 文件不存在
    """
    rough = latest_publish(shot, "rough_layout", project)
    if not rough:
        raise ValueError(f"{shot} 没有 rough_layout 发布")
    rough_ma = rough.get("sg_path_to_geometry")
    if not rough_ma or not Path(rough_ma).exists():
        raise ValueError(f"{shot} rough_layout 的 ma 文件不存在: {rough_ma}")
    notes: list[str] = []
    root = Path(rough["sg_path_to_v_folder"]).parent.parent

    # {shot}.asb_all.usda 是镜头的场景 usda, layout 改过场景后再发布的文件, 解析依赖补齐其引用的场景资产
    asb_all_usda = root / "asb" / f"{shot}.asb_all.usda"
    files = set(_existing([asb_all_usda, root / "lay" / f"{shot}.lay.usda"], notes, shot))
    if asb_all_usda.exists():
        deps, unresolved = usd_deps(str(asb_all_usda))
        # 只补场景资产; 镜头目录下的依赖 (lay.usda 及其引用的 rough_layout 版本 usda) 不发,
        # lay.usda 已单独上传, 仅供外包检查工具读取, 不需要它的依赖
        files |= {f for f in deps if not Path(f).is_relative_to(root)}
        notes += [f"解析不到: {u}" for u in unresolved]  # 与 lay 同格式, 同一缺失只显示一次
    asb_all_no_tex_usda = root / "asb" / f"{shot}.asb_all.no_tex.usda"
    if asb_all_no_tex_usda.exists():
        files.add(str(asb_all_no_tex_usda))

    for task in ("rough_layout", "blocking", "animation"):
        v = rough if task == "rough_layout" else latest_publish(shot, task, project)
        if not v:
            continue  # blocking / animation 可以没有
        ma = Path(v["sg_path_to_geometry"])
        files |= _existing([ma], notes, f"{shot} {task}")
        if (ma.parent / "maya_usd").exists():
            files.add(str(ma.parent / "maya_usd"))
    return frozenset(files), tuple(notes)



@register('ani')
@dataclass
class AniComponent(LayComponent):
    """动画发包 (blocking / animation 不区分): layout 的资产 + 镜头文件."""
    step:str = "ani"
    name:str = "动画"
    color:str = "#f59e0b"
    order:int = 7
    description:str = "这是一个ani的资产"

    def _collect(self):
        super()._collect()
        try:
            files, notes = collect_shot(self.entity, self.project)
        except ValueError as e:  # 没有 rough_layout 发布或其 ma 文件缺失
            self.errors.append(str(e))
            return
        self._add(files)
        self.notes += notes
