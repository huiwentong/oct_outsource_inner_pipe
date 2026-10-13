import re
import json
import tempfile
from pathlib import Path


def is_valid_project_name(file_path: str, valid_name_pattern: str) -> bool:
    pattern = r"{}\.v(\d{{3}})\.(ma|mb)$".format(valid_name_pattern)
    match = re.match(pattern, Path(file_path).name, re.I)
    if not match:
        return False
    return True

def is_valid_file_name(file_path: str) -> bool:
    pattern = r'^[A-Za-z0-9_.-]+$'
    match = re.match(pattern, Path(file_path).name, re.I)
    if not match:
        return False
    return True


def write_temp_json(data, root_dir=None):
    if root_dir is None:
        root_dir = Path(tempfile.gettempdir())
    else:
        root_dir = Path(root_dir)

    root_dir.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=".json", dir=str(root_dir))

    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        import os
        os.close(fd)
        raise

    return to_win_path(path)


def to_win_path(lux_path):
    lux_path = str(lux_path)
    print("source path:", lux_path)
    path_map = {
        '/srv/i/': 'i:/',
        '/srv/w/': 'w:/',
        '/srv/s/': 's:/',
    }
    return path_map[lux_path[:7].lower()] + lux_path[7:]
