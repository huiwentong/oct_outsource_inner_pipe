import json
import tempfile
import weakref
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6 import QtWidgets
from shiboken6 import isValid

from components.core import StepComponent, register
from utils.paths import entity_root, relies, strip_version, to_ftp
from utils.shotgun import latest_publish, shot_assets
from utils.usd import usd_deps

RIG_TYPES = {"CH", "PROP"}
USD_TYPES = {"ASB", "ENV"}
PICKER_ROOT = Path("W:/projects/lib/Ani_lib/MG_picker")

# 当前存活的 lay / ani 组件, 供 "应用到全部" 同步 nemo 勾选
_LIVE: weakref.WeakValueDictionary = weakref.WeakValueDictionary()


def _existing(paths, notes, label):
    """筛出存在的路径, 不存在的往 notes 里追加提示.

    Args:
        paths (Iterable[str | Path]): 待检查的本地路径
        notes (list[str]): 提示列表, 原地追加
        label (str): 提示前缀, 通常是实体名

    Returns:
        set[str]: 存在的路径
    """
    out = set()
    for p in paths:
        if Path(p).exists():
            out.add(str(p))
        else:
            notes.append(f"{label} 缺少 {Path(p).name}")
    return out


def _publish_dir(name: str, task: str, project: str) -> tuple[Path | None, str | None]:
    """查最新发布的版本目录, 区分 "没有发布" 和 "有发布但路径为空 / 不存在" 两类问题.

    Args:
        name (str): 资产名
        task (str): SG 任务名, 如 ``rigging``
        project (str): 项目名

    Returns:
        tuple[Path | None, str | None]: (版本目录, 提示); 有问题时版本目录为 None
    """
    v = latest_publish(name, task, project)
    if not v:
        return None, f"{name} 没有 {task} 发布"
    path = v.get("sg_path_to_v_folder")
    if not path:
        return None, f"{name} 的 {task} 发布在 Shotgun 上没有填版本目录路径"
    if not Path(path).exists():
        return None, f"{name} 的 {task} 发布路径不存在: {path}"
    return Path(path), None


@lru_cache(maxsize=None)
def collect_asset(name: str, asset_type: str, project: str) -> tuple[frozenset[str], tuple[str, ...]]:
    """收集单个资产的发包文件: CH / PROP 取 rigging 发布, ASB / ENV 解析 asb usda 依赖, 其他类型不收集.

    Args:
        name (str): 资产名
        asset_type (str): SG 的 sg_asset_type, 如 ``CH`` / ``ENV``
        project (str): 项目名

    Returns:
        tuple[frozenset[str], tuple[str, ...]]: (本地文件路径集合, 提示列表)
    """
    notes: list[str] = []
    files: set[str] = set()
    if asset_type in RIG_TYPES:
        v_dir, note = _publish_dir(name, "rigging", project)
        if not v_dir:
            return frozenset(), (note,)
        rig_dir = v_dir.parent / strip_version(v_dir.name)
        root = v_dir.parent.parent
        files |= _existing([rig_dir / f"{name}.ma", rig_dir / "sourceimages", rig_dir / "controller_data.json",
             root / "asb" / f"{name}.usda"],  # asb usda 只作占位, 不解析依赖
            notes, name,
        )
    elif asset_type in USD_TYPES:
        v_dir, note = _publish_dir(name, "model", project)
        if not v_dir:
            return frozenset(), (note,)
        entry = v_dir.parent.parent / "asb" / f"{name}.usda"
        if not entry.exists():
            return frozenset(), (f"{name} 缺少 {entry}",)
        deps, unresolved = usd_deps(str(entry))
        files |= deps
        notes += [f"解析不到: {u}" for u in unresolved]  # prim 路径已指明资产, 不加前缀以便去重
        # 同目录的 no_tex 版本 (可无): 没有被任何 usda 引用, 解析不到, 需单独加; 它只引用 {name}.usda, 依赖已收齐
        no_tex = entry.with_name(f"{name}.no_tex.usda")
        if no_tex.exists():
            files.add(str(no_tex))
    return frozenset(files), tuple(notes)


@lru_cache(maxsize=None)
def collect_nemo(name: str, project: str) -> tuple[frozenset[str], tuple[str, ...]]:
    """收集资产的 nemo 绑定 (rigging_nemo / rigging_nemo_low); 没有发布的只提示, 不阻止发包.

    Args:
        name (str): 资产名
        project (str): 项目名

    Returns:
        tuple[frozenset[str], tuple[str, ...]]: (本地文件路径集合, 提示列表)
    """
    notes: list[str] = []
    files: set[str] = set()
    for task in ("rigging_nemo", "rigging_nemo_low"):
        v_dir, note = _publish_dir(name, task, project)
        if not v_dir:
            notes.append(f"{note}, 已跳过")
            continue
        nemo_dir = v_dir.parent / strip_version(v_dir.name)
        files |= _existing([nemo_dir / f"{name}.ma", nemo_dir / "sourceimages"], notes, f"{name} {task}")
    return frozenset(files), tuple(notes)


@lru_cache(maxsize=None)
def _picker_dirs(project: str) -> dict[str, str]:
    """列出项目的 MG picker 目录; 目录名有大小写不一致的 (如 JiangLiuEr), 统一按小写建索引.

    Args:
        project (str): 项目名, 对应 MG_picker 下的大写目录, 如 ``mk2`` → ``MK2``

    Returns:
        dict[str, str]: {小写目录名: 目录路径 (正斜杠)}, 如 ``{"jiangliuer": "W:/projects/lib/Ani_lib/MG_picker/MK2/JiangLiuEr"}``;
            项目没有 picker 目录时返回空字典
    """
    root = PICKER_ROOT / project.upper()
    return {p.name.lower(): p.as_posix() for p in root.iterdir() if p.is_dir()} if root.is_dir() else {}


def find_picker(name: str, project: str) -> str | None:
    """按资产名找 MG picker 目录 (W:/projects/lib/Ani_lib/MG_picker/{项目}/{资产}), 找不到返回 None.

    Args:
        name (str): 资产名
        project (str): 项目名

    Returns:
        str | None: picker 目录的本地路径
    """
    return _picker_dirs(project).get(name.lower())


def default_path_files(local_paths) -> dict[str, str]:
    """为涉及的每个实体 (资产和镜头) 在临时目录生成 default_path.json.

    Args:
        local_paths (Iterable[str]): 本次要上传的 I 盘本地路径

    Returns:
        dict[str, str]: {本地 json 路径: FTP 目标路径}
    """
    out = {}
    roots = {entity_root(p) for p in local_paths} - {None}
    for i_root, ftp_root in roots:
        name = ftp_root.rsplit("/", 1)[-1]
        json_file = Path(tempfile.gettempdir()) / "oct_default_path" / ftp_root.strip("/") / "default_path.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        json_file.write_text(
            json.dumps({"entity_name": name, "default_path": i_root}, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        out[str(json_file)] = f"{ftp_root}/default_path.json"
    return out


@register('lay')
@dataclass
class LayComponent(StepComponent):
    """layout 发包: 收集镜头关联的资产 (ASB/ENV 解析 USD 依赖, CH/PROP 收 rig)."""
    step:str = "lay"
    name:str = "Layout"
    color:str = "#14b8a6"
    description:str = "这是一个lay的资产"
    order:int = 6

    def analysis_relies(self):
        """依赖从上传路径反推, 在 analysis_transfer_folders 末尾的 _refresh 里计算."""

    def analysis_transfer_folders(self):
        self.notes, self.errors = [], []
        self._rig_assets, self._nemo_keys, self._nemo_notes = [], [], []
        if self.entity_type != 'shot':
            self.errors.append(f'{self.name}发包只支持镜头')
        else:
            self._collect()
        self._refresh()

    def _collect(self):
        assets = shot_assets(self.entity, self.project)  # 镜头资产 + 所属场次资产
        if not assets:
            self.notes.append(f'{self.entity} 及其场次在 Shotgun 上都没有关联资产')
        for name, asset_type, from_sequence in assets:
            files, notes = collect_asset(name, asset_type, self.project)
            self._add(files)
            self.notes += [f'(场次资产) {n}' for n in notes] if from_sequence else notes
            if asset_type in RIG_TYPES:
                self._rig_assets.append(name)
                if files:  # 没有 rig 文件就没有 default_path.json, picker 单独发过去落不了盘
                    self._add_picker(name, asset_type, entity_root(next(iter(files))))

    def _add_picker(self, name: str, asset_type: str, root: tuple[str, str] | None):
        """把资产的 MG picker 目录加入上传清单, 放到它的 rig 目录下; 道具一般不做 picker, 只提示角色缺失.

        Args:
            name (str): 资产名
            asset_type (str): SG 的 sg_asset_type, ``CH`` / ``PROP``
            root (tuple[str, str] | None): 该资产 rig 文件的 ``entity_root`` 结果 (I 盘根目录, FTP 根目录),
                保证 picker 和 rig 文件落在同一个 FTP 实体目录下; 为 None 时不加 picker

        Returns:
            None: 原地写入 ``self.transfer_folders`` 和 ``self.notes``
        """
        picker = find_picker(name, self.project)
        if not picker:
            if asset_type == "CH":
                self.notes.append(f"{name} 没有 MG picker")
        elif root:
            self.transfer_folders[picker] = f"{root[1]}/rig/mg_picker"
        else:  # rig 文件不在 I:/projects 下, _add 已提示跳过, 这里说明 picker 为什么也没发
            self.notes.append(f"{name} 的 rig 文件不在 I:/projects 下, MG picker 一并跳过")

    def _add(self, files) -> list[str]:
        """加入上传清单 (按 FTP 路径去重), 返回新加入的本地路径."""
        dsts = set(self.transfer_folders.values())
        added = []
        for f in sorted(files):
            dst = to_ftp(f)
            if not dst:
                self.notes.append(f'不在 I:/projects 下, 已跳过: {f}')
            elif dst not in dsts:
                self.transfer_folders[f] = dst
                dsts.add(dst)
                added.append(f)
        return added

    def _refresh(self):
        self.rely_assets, self.rely_steps = relies(self.transfer_folders.values())
        lines = list(dict.fromkeys(self.errors + self.notes + self._nemo_notes))  # 保序去重
        self._notes_label.setText('\n'.join(lines[:8]) + (f'\n…等共 {len(lines)} 条, 悬停查看全部' if len(lines) > 8 else ''))
        self._notes_label.setToolTip('\n'.join(lines))
        self._notes_label.setVisible(bool(lines))

    def _toggle_nemo(self, checked: bool):
        for k in self._nemo_keys:
            self.transfer_folders.pop(k, None)
        self._nemo_keys, self._nemo_notes = [], []
        if checked:
            for name in self._rig_assets:
                files, notes = collect_nemo(name, self.project)
                self._nemo_keys += self._add(files)
                self._nemo_notes += notes
        self._refresh()

    def _apply_nemo_to_all(self):
        checked = self.nemo_box.isChecked()
        for comp in list(_LIVE.values()):
            if isValid(comp.nemo_box):  # 已删除的任务行, Qt 控件已销毁
                comp.nemo_box.setChecked(checked)

    def gener_default_path(self):
        """不用 core 的实现: 它按资产写死, 镜头会报错且路径不对, 见 ani_collector_plan.md."""
        self.transfer_folders.update(default_path_files(list(self.transfer_folders)))

    def check_relies_folders(self):
        if self.errors:
            raise ValueError('; '.join(self.errors))
        super().check_relies_folders()

    def extra_ui(self):
        self.custom_frame = QtWidgets.QFrame()
        v_lay = QtWidgets.QVBoxLayout(self.custom_frame)
        _LIVE[id(self)] = self
        self.nemo_box = nemo_box = QtWidgets.QCheckBox('同时收集 nemo 绑定 (角色 / 道具, 没有 nemo 发布的会跳过)')
        nemo_box.toggled.connect(self._toggle_nemo)
        apply_all = QtWidgets.QPushButton('应用到全部')
        apply_all.setToolTip('把本行的 nemo 勾选状态同步到所有 Layout / 动画任务')
        apply_all.clicked.connect(self._apply_nemo_to_all)
        nemo_row = QtWidgets.QHBoxLayout()
        nemo_row.addWidget(nemo_box)
        nemo_row.addWidget(apply_all)
        nemo_row.addStretch(1)
        self._notes_label = QtWidgets.QLabel()
        self._notes_label.setStyleSheet('color:#dc2626;')
        self._notes_label.setWordWrap(True)
        self._notes_label.setVisible(False)
        v_lay.addLayout(nemo_row)
        v_lay.addWidget(self._notes_label)
