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


def write_temp_json(data):
    with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return f.name


def to_win_path(lux_path):
    lux_path = str(lux_path)
    print("source path:", lux_path)
    path_map = {
        '/srv/i/': 'i:/',
        '/srv/w/': 'w:/',
        '/srv/s/': 's:/',
    }
    return path_map[lux_path[:7].lower()] + lux_path[7:]
