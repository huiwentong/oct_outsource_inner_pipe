from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Optional, Type, Union

import components  # noqa: F401  仅为 auto-discover 提供包路径


@dataclass
class FieldSpec:
    """环节补充资料中的一个字段定义，UI 会根据 kind 自动生成控件。"""

    key: str                       # 字段标识，读取数据时使用
    label: str                     # 显示名称
    kind: str = "text"             # text | combo | check
    options: Optional[list[str]] = None   # kind == combo 时使用
    default: Any = ""              # 默认值 / mock 自动加载值
    placeholder: str = ""
    help: str = ""


class StepComponent:
    """collector 针对“单个制作环节”的能力模块基类。

    当前全部使用 mock 数据；后续把每个环节真实的抓包逻辑补充到
    ``collect`` / ``mock_defaults`` 即可，UI 不需要改动。
    """

    step: str = ""                 # 环节英文标识，例如 "mod"
    name: str = ""                 # 环节中文名
    color: str = "#64748b"         # 环节徽章颜色
    order: int = 99                # 界面排列顺序
    fields: list[FieldSpec] = field(default_factory=list)

    def default_ftp_path(self, project: str, entity: str) -> str:
        """数据默认上传到 ftp 的路径。"""
        return f"/oct/{project}/{entity}/{self.step}"

    def mock_defaults(self, entity: str, project: str) -> dict[str, Any]:
        """mock 数据：按实体自动加载该环节补充资料的默认值。

        TODO(后续补充): 这里替换为真实的数据库 / 工程文件查询逻辑。
        """
        return {}

    def collect(self, payload: dict[str, Any]) -> None:
        """执行抓包逻辑（当前仅打印，不真正上传）。

        TODO(后续补充): 在这里根据 payload 查询制作文件并上传到 ftp。
        """
        print(f"[mock抓包] {payload}")


# ---------- 注册表 ----------

_REGISTRY: dict[str, StepComponent] = {}
_DISCOVERED = False


def register(
    component: Union[Type[StepComponent], StepComponent],
) -> StepComponent:
    """注册环节组件；支持直接传类（以 @register 装饰）或实例。"""
    if isinstance(component, type):
        component = component()
    _REGISTRY[component.step] = component
    return component


def _discover() -> None:
    """自动加载 components 下每个环节的模块（mod.py、tex.py...）。"""
    global _DISCOVERED
    if _DISCOVERED:
        return

    for module in pkgutil.iter_modules(components.__path__):
        if module.name in ("core",):
            continue
        importlib.import_module(f"components.{module.name}")
    _DISCOVERED = True


def get_component(step: str) -> StepComponent:
    _discover()
    try:
        return _REGISTRY[step]
    except KeyError:
        raise KeyError(f"没有注册制作环节组件: {step!r}") from None


def all_components() -> list[StepComponent]:
    _discover()
    return list(_REGISTRY.values())


def step_options() -> list[tuple[str, str, str]]:
    """返回 (step, 中文名, 颜色) 列表，按 order 排序，供 UI 渲染。"""
    comps = sorted(all_components(), key=lambda c: c.order)
    return [(comp.step, comp.name, comp.color) for comp in comps]
