from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import Any, Optional, Type, Union
from PySide6 import QtCore, QtWidgets
import components  # noqa: F401  仅为 auto-discover 提供包路径
from typing import ClassVar
from utils.permissionmanager import add_group2vendor, create_group
from pathlib import Path
from utils.ftp import FtpClient


def inspect_component(component):
    inspect_string = ''
    for _f in fields(component):
        k = _f.name
        v = getattr(component, k)
        if isinstance(v, QtWidgets.QFrame):
            continue
        inspect_string += f'{k}: {str(v)}\n'
    return inspect_string

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



@dataclass
class StepComponent:
    """collector 针对“单个制作环节”的能力模块基类。

    当前全部使用 mock 数据；后续把每个环节真实的抓包逻辑补充到
    ``collect`` / ``mock_defaults`` 即可，UI 不需要改动。
    """

    project:str
    entity:str
    entity_type:str
    transfer_folders: dict = field(default_factory=dict)
    rely_steps: list[str] = field(default_factory=list)
    rely_assets: list[str] = field(default_factory=list)
    auto_build_frame: QtWidgets.QFrame | None = None
    custom_frame: QtWidgets.QFrame | None = None
    ftp_tar: str = ''
    


    def __post_init__(self):
        self.default_ftp_path()
        self.auto_build()
        self.extra_ui()
        self.analysis_relies()
        self.analysis_transfer_folders()
        


    def default_ftp_path(self):
        """数据默认上传到 ftp 的路径。"""
        self.ftp_tar = f"/oct/{self.project}/{self.entity_type}/{self.entity}/{self.step}/requirements"

    def auto_build(self):
        self.auto_build_frame = QtWidgets.QFrame()
        

        h_lay = QtWidgets.QHBoxLayout(self.auto_build_frame)
        h_lay.setSpacing(8)

        extra_label = QtWidgets.QLabel('选择需要额外指定的文件')
        extra_file_picker = QtWidgets.QPushButton('点击选择文件')
        extra_file_line = QtWidgets.QLineEdit()
        extra_file_line.setEnabled(False)

        des_label = QtWidgets.QLabel('备注')
        des_eline = QtWidgets.QLineEdit()
        des_eline.setText(self.description)
        des_eline.textChanged.connect(lambda text: setattr(self, 'description', text))

        

        extra_file_picker.clicked.connect(lambda: self.pick_button(extra_file_line))


        h_lay.addWidget(extra_label)
        h_lay.addWidget(extra_file_picker)
        h_lay.addWidget(extra_file_line)
        h_lay.addWidget(des_label)
        h_lay.addWidget(des_eline)


    def pick_button(self, editline:QtWidgets.QLineEdit):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames()
        print(files)
        editline.setText(' '.join(files))
        editline.setToolTip('\n'.join(files))
        for i in files:
            self.transfer_folders[i] = str(Path(self.ftp_tar) / Path(i).name)


    def start_collection(self, vendor):
        self.check_relies_folders()
        all_group = self.rely_assets+self.rely_steps+[self.project]
        for _g in all_group:
            r = create_group(_g)
            print(r)
        ret = add_group2vendor(vender=vendor, groups=all_group)
        print(ret)
        for source, dst in self.transfer_folders.items():
            with FtpClient() as ftp:
                path_s = Path(source)
                if not path_s.exists():
                    raise FileExistsError(f'file {source} dose not exist!')
                if path_s.is_dir():
                    ftp.upload_dir(Path(source), dst)
                else:
                    ftp.upload_file(Path(source), dst)



    def check_relies_folders(self):
        """检查依赖环节和依赖资产的传输文件夹是否存在。"""
        for k,v in self.transfer_folders.items():
            if not Path(k).exists():
                raise FileNotFoundError(f"依赖文件夹不存在: {k}")
        if not self.rely_steps or not self.rely_assets:
            raise ValueError("没有依赖环节和依赖资产，检查不通过！")

    @abstractmethod
    def analysis_relies(self):
        """用于解析所有的依赖环节和依赖资产"""
        pass


    @abstractmethod
    def analysis_transfer_folders(self):
        """用于解析所有需要打包的传输的文件和文件夹夹"""
        pass



    def extra_ui(self):
        """返回一个额外的 UI 控件，显示在环节补充资料的下方。

        TODO(后续补充): 这里可以返回一个 QTreeView / QTableView，显示该环节的
        历史抓包记录，供用户参考。
        """


# ---------- 注册表 ----------

_REGISTRY: dict[str, Type[StepComponent]] = {}
_DISCOVERED = False

def register(step):
    def func(
        component: Type[StepComponent]
    ) -> Type[StepComponent]:
        """注册环节组件；支持直接传类（以 @register 装饰）或实例。"""
        if not isinstance(component, type):
            raise TypeError(
                f"{cls} must inherit StepComponent"
            )
        _REGISTRY[step] = component
        return component

    return func


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


def get_component(step: str) -> type[StepComponent]:
    _discover()
    try:
        return _REGISTRY[step]
    except KeyError:
        raise KeyError(f"没有注册制作环节组件: {step!r}") from None


def all_components() -> list[type[StepComponent]]:
    _discover()
    return list(_REGISTRY.values())


def step_options() -> list[tuple[str, str, str]]:
    """返回 (step, 中文名, 颜色) 列表，按 order 排序，供 UI 渲染。"""
    comps = sorted(all_components(), key=lambda c: c.order)
    return [(comp.step, comp.name, comp.color) for comp in comps]
