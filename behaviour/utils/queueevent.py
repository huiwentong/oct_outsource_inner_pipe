import asyncio
from dataclasses import dataclass, field, fields, asdict
import os
from behaviour import logger
import json
from pathlib import Path
from behaviour.utils.hashing import hash_file
import re

@dataclass
class Event():
    vendor: str
    manifest_file:str = ''
    asset:str = ''
    step:str = ''
    checksum:str = ''
    version:str = ''
    dst_path:str = ''



def find_dst_path_and_version(data):
    path = Path(f'/mnt/W/projects/{data["project"]}/outsourcing/{data["type"]}/{data["entity_name"]}/{data["task_step"]}')
    max_version = 0

    if path.exists():
        for item in path.iterdir():
            match = re.fullmatch(r'v(\d+)', item.name, re.IGNORECASE)
            if match:
                max_version = max(max_version, int(match.group(1)))

    version = f'v{max_version + 1:03d}'

    return path, version



def make_event(manifest_path, vendor) -> Event:
    with Path('/srv/ftp/' + manifest_path).open('r') as f:
        data = json.load(f)
        p,v = find_dst_path_and_version(data)
        return Event(
            vendor=vendor,
            manifest_file=manifest_path,
            asset=data['entity_name'],
            step=data['task_step'],
            checksum=str(hash_file(manifest_path)),
            version=v,
            dst_path=str(p)
        )


    