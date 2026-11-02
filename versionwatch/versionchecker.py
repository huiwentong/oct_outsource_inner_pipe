import asyncio
from datetime import datetime, time
from versionwatch.config import Settings
from versionwatch.warning_msg import send_warning_message
from versionwatch.hashing import hash_file
from logger.core import watch_logger
import traceback
from zoneinfo import ZoneInfo
import os
from glob import glob
import json


logger = watch_logger

class VersionChecker:
    def __init__(self, settings: Settings):
        self.setting = settings
        self._stop = asyncio.Event()

    async def run(self):
        last_scanned_date = None
        while not self._stop.is_set():
            now = datetime.now(ZoneInfo(self.setting.log_timezone))
            if time(2, 0) <= now.time() < time(3, 0):
                if last_scanned_date != now.date():
                    logger.info('>>> **** >>>> **** 开始自动全盘扫描...')
                    try:
                        await self.check_all()
                        logger.info('>>> **** >>>> **** 扫描结束')
                        last_scanned_date = now.date()
                    except Exception:
                        logger.warning('>>> **** >>>> **** 扫描出现问题：' + traceback.format_exc())
                        try:
                            send_warning_message('每天定时自动全盘扫描出现问题：' + traceback.format_exc())
                        except Exception:
                            logger.error('发送告警失败：' + traceback.format_exc())
                        await asyncio.sleep(1200)
            else:
                await asyncio.sleep(3600)



    async def check_all(self):
        await asyncio.to_thread(check_all_sync, '/srv/i', str(self.setting.root_dir))



    def close(self):
        self._stop.set()


def check_all_sync(driver='/srv/i', ftp='/srv/ftp/oct'):
    error = []
    need_to_update = []
    for project in os.listdir(ftp):
        for entity_type in os.listdir(os.path.join(ftp, project)):
            for entity in os.listdir(os.path.join(ftp, project, entity_type)):
                js_file = os.path.join(ftp, project, entity_type,'default_path.json')
                if not os.path.exists(js_file): continue

                with open(js_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f'扫盘程序找到了{js_file}')
                
                default_path_root = str(data['default_path']).lower().replace('i:', driver)
                for step in os.listdir(os.path.join(ftp, project, entity_type, entity)):
                    if not os.path.isdir(os.path.join(ftp, project, entity_type, entity, step)): continue
                    logger.info(f'开始比对 {project}|{entity_type}|{entity}|{step}')
                    if 'rig' != step:
                        try:
                            usda_file = glob(os.path.join(ftp, project, entity_type, entity, step) + '/*.usda')[0]
                        except:
                            logger.warning(f"扫盘过程中没有找到{os.path.join(ftp, project, entity_type, entity, step) + '/*.usda'}")
                            error.append(f"扫盘过程中没有找到{os.path.join(ftp, project, entity_type, entity, step) + '/*.usda'}")
                            continue
                        driver_usda = default_path_root + f'/{step}/{entity}.{step}.usda'
                        if step == 'asb':
                            driver_usda = default_path_root + f'/{step}/{entity}.usda'
                        if hash_file(usda_file) != hash_file(driver_usda):
                            need_to_update.append(f'{project}|{entity_type}|{entity}|{step}')
                    else:
                        for rig_folder in os.listdir(os.path.join(ftp, project, entity_type, entity, step)):
                            try:
                                ma_file = glob(os.path.join(ftp, project, entity_type, entity, step, rig_folder) + '/*.ma')[0]
                            except:
                                continue
                            try:
                                driver_ma_file = glob(default_path_root + f'/{step}/{rig_folder}/*.ma')[0]
                            except:
                                logger.warning(f"扫盘过程中没有找到{default_path_root + f'/{step}/{rig_folder}/*.ma'}")
                                error.append(f"扫盘过程中没有找到{default_path_root + f'/{step}/{rig_folder}/*.ma'}")
                                continue
                            if hash_file(ma_file) != hash_file(driver_ma_file):
                                need_to_update.append(f'{project}|{entity_type}|{entity}|{step}|{rig_folder}')




if __name__ == "__main__":
    check_all_sync()