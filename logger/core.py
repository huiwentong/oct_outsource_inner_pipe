import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path

def get_log(logger_name: str = "permissionmanager", test=False) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)


    if os.path.exists("/var/log/outsource"):
        filename = f"/var/log/outsource/{logger_name}.log"
    else:
        filename = Path(__file__).parent.parent / f'{logger_name}.log'


    file_handler = TimedRotatingFileHandler(
        filename=filename,
        when="midnight",      # 每天凌晨切换
        interval=1,           # 间隔1天
        backupCount=30,       # 保留30天
        encoding="utf-8",
    )

    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    console.setFormatter(formatter)
    file_handler.setFormatter(formatter)


    logger.addHandler(console)
    logger.addHandler(file_handler)


    logger.info(f"{logger_name} started")
    return logger


watch_logger = get_log("versionwatch")