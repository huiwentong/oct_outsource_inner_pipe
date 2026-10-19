# -*- coding: utf-8 -*-
import collections
import datetime
import os
import re
import shutil
import tempfile
from pathlib import Path

UDIM_TOKEN_RE = re.compile(r"(<udim>|<uvtile>|%\(udim\)d|\$\{?udim\}?|u#_v#)", re.I)
UDIM_NUMBER_RE = re.compile(r"(?<!\d)1\d{3}(?!\d)")
ABS_PATH_RE = re.compile(
    r"""(?P<path>(?:[A-Za-z]:[/\\]|//)[^\r\n"'|]+?\.(?:"""
    r"bmp|cin|dds|dpx|exr|gif|hdr|iff|jpeg|jpg|pic|png|psd|rla|sgi|tga|tif|tiff|tx|webp|"
    r"""xgen|xdsc|xgd|xgc|xgip|abc|ptx|ptex|xuv))(?=$|[\s"';,\]\)])""", re.I,
)
PROJECT_RE = re.compile(
    r'(setAttr\s+"\.(?:xgProjectPath|projectPath)"\s+-type\s+"string"\s+")([^"]*)("\s*;)', re.I,
)
XGEN_EXTS = {".xgen", ".xdsc", ".xgd", ".xgc", ".xgip"}
ResolveResult = collections.namedtuple("ResolveResult", "source target status candidates")


def maya_path(value):
    return str(value).replace("\\", "/")


class AssetIndex:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.files, self.by_name = [], collections.defaultdict(list)
        for base, dirs, names in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
            for name in names:
                if not name.endswith(".relink.bak"):
                    path = Path(base) / name
                    self.files.append(path)
                    self.by_name[name.casefold()].append(path)

    def resolve(self, source, convert_udim=True):
        expanded = os.path.expandvars(source)
        name = maya_path(expanded).rstrip("/").rsplit("/", 1)[-1]
        token = UDIM_TOKEN_RE.search(name)
        tile = token or (UDIM_NUMBER_RE.search(name) if convert_udim else None)
        matches = self.by_name.get(name.casefold(), [])
        if tile:
            pattern = re.compile(
                "^" + re.escape(name[:tile.start()]) + r"1\d{3}" + re.escape(name[tile.end():]) + "$", re.I,
            )
            matches = [p for p in self.files if pattern.match(p.name)]
        if not matches:
            return ResolveResult(source, None, "missing", [])

        old_parts = [p.casefold() for p in maya_path(expanded).split("/") if p and not p.endswith(":")]

        def score(path):
            common = 0
            for old, new in zip(reversed(old_parts), reversed(path.parts)):
                if old != new.casefold():
                    break
                common += 1
            return common * 100 - len(path.parts)

        ranked = sorted(matches, key=lambda p: (score(p), -len(str(p))), reverse=True)
        directories = {}
        for path in ranked:
            directories.setdefault(path.parent, score(path))
        ordered = sorted(directories, key=lambda p: (directories[p], -len(str(p))), reverse=True)
        candidates = [str(p) for p in ranked[:10]]
        if len(ordered) > 1:
            a, b = ordered[:2]
            if directories[a] == directories[b] and len(str(a)) == len(str(b)):
                return ResolveResult(source, None, "ambiguous", candidates)

        best = ranked[0]
        name = best.name
        if token or (tile and len({p.name.casefold() for p in matches}) > 1):
            match = UDIM_TOKEN_RE.search(name) or UDIM_NUMBER_RE.search(name)
            name = name[:match.start()] + "<UDIM>" + name[match.end():]
        return ResolveResult(source, maya_path(best.parent / name), "resolved", candidates)


class RelinkReport:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        for name in ("changed", "unchanged", "missing", "ambiguous", "errors", "external_files"):
            setattr(self, name, [])

    def add_result(self, label, result):
        if result.status == "resolved":
            if maya_path(result.source) == result.target:
                self.unchanged.append(label)
            else:
                self.changed.append((label, result.source, result.target))
        elif result.status == "ambiguous":
            self.ambiguous.append((label, result.source, result.candidates))
        else:
            self.missing.append((label, result.source))

    def text(self):
        lines = ["已替换: {}  未变化: {}  未找到: {}  有歧义: {}  错误: {}".format(
            *(len(getattr(self, key)) for key in ("changed", "unchanged", "missing", "ambiguous", "errors"))
        )]
        for title, entries in (
            ("替换路径", ["{}: {} -> {}".format(*row) for row in self.changed]),
            ("文件", self.external_files),
            ("未找到", ["{}: {}".format(*row) for row in self.missing]),
            ("有歧义，未修改", ["{}: {} 候选: {}".format(*row) for row in self.ambiguous]),
            ("错误", self.errors),
        ):
            if entries:
                lines.extend(["\n[{}]".format(title)] + entries)
        return "\n".join(lines)


def rewrite_xgen_text(text, index, report, label):
    count = 0

    def replace(match):
        nonlocal count
        result = index.resolve(match.group("path").rstrip())
        report.add_result(label, result)
        if result.status == "resolved" and maya_path(result.source) != result.target:
            count += 1
            return result.target
        return match.group(0)

    return ABS_PATH_RE.sub(replace, text), count


def rewrite_maya_ascii(text, index, report):
    output, node_type, node_name = [], "", ""
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        node = re.search(r'^\s*createNode\s+(\S+).*?-n\s+"([^"]+)"', line)
        if node:
            node_type, node_name = node.groups()
        line, count = rewrite_xgen_text(line, index, report, "MA:{} {}".format(number, node_name))
        output.append(line)
        if count and node_type == "file" and "<UDIM>" in line and re.search(
            r'setAttr\s+"\.(?:ftn|fileTextureName)"', line
        ):
            output.append('\tsetAttr ".uvt" 3;' + ("\r\n" if line.endswith("\r\n") else "\n"))

    def project(match):
        target = maya_path(index.root).rstrip("/") + "/"
        if maya_path(match[2]).rstrip("/") == target.rstrip("/"):
            report.unchanged.append("XGen projectPath")
            return match.group(0)
        report.add_result("XGen projectPath", ResolveResult(match[2], target, "resolved", []))
        return match[1] + target + match[3]

    return PROJECT_RE.sub(project, "".join(output))


def _read_text_file(path):
    raw = path.read_bytes()
    if b"\0" in raw[:4096]:
        return None, None
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    declared = re.search(rb"(?m)^//Codeset:\s*(\d+)", raw[:4096])
    encodings = ["cp" + declared[1].decode("ascii")] if declared else []
    for encoding in encodings + ["utf-8", "gb18030", "latin-1"]:
        try:
            return raw.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            pass


def _encode_maya_ascii(text, encoding):
    text = text.lstrip("\ufeff")
    if not text.startswith("//Maya ASCII"):
        raise ValueError("无效的 Maya ASCII 文件头。")
    return text.encode("utf-8" if encoding == "utf-8-sig" else encoding)


def relink_xgen_files(index, report, make_backup=True):
    xgen_root = index.root / "xgen"
    files = [p for p in index.files if p.suffix.casefold() in XGEN_EXTS or (
        xgen_root in p.parents and p.suffix.casefold() in {".json", ".xml", ".mel"}
    )]
    if not files:
        report.external_files.append("未找到可编辑的 XGen 文本文件。")
    for path in sorted(files):
        try:
            text, encoding = _read_text_file(path)
            if text is None:
                report.external_files.append("跳过二进制文件: {}".format(path))
                continue
            text, count = rewrite_xgen_text(text, index, report, str(path))
            if count and not report.dry_run:
                backup = Path(str(path) + ".relink.bak")
                if make_backup and not backup.exists():
                    shutil.copy2(path, backup)
                path.write_bytes(text.encode(encoding))
                report.external_files.append("{}: 已替换 {} 处".format(path, count))
        except Exception as exc:
            report.errors.append("{}: {}".format(path, exc))


def execute_relinker(maya_file, image_root):
    """将原 MA 移到 image_root/source，替换路径并以原名输出；返回报告。"""
    index, scene = AssetIndex(image_root), Path(maya_file).expanduser().resolve()
    text, encoding = _read_text_file(scene)
    _encode_maya_ascii(text, encoding)
    source = index.root / "source_project"
    source.mkdir(exist_ok=True)
    backup = source / scene.name
    stamp, counter = datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), 0
    while backup.exists():
        suffix = "." + str(counter) if counter else ""
        backup = source / "{}.{}{}{}".format(scene.stem, stamp, suffix, scene.suffix)
        counter += 1
    shutil.move(str(scene), str(backup))
    report, staged = RelinkReport(), None
    try:
        data = _encode_maya_ascii(rewrite_maya_ascii(text, index, report), encoding)
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".maya_relink_", suffix=".tmp",
                                         dir=scene.parent, delete=False) as handle:
            staged = Path(handle.name)
            handle.write(data)
        os.replace(staged, scene)
    except Exception:
        shutil.move(str(backup), str(scene))
        raise
    finally:
        if staged and staged.exists():
            staged.unlink()
    report.external_files.extend(["Maya 原文件备份: {}".format(backup), "Maya 新文件: {}".format(scene)])
    relink_xgen_files(index, report)
    print(report.text())
    return report
