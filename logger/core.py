import logging
from logging.handlers import TimedRotatingFileHandler

def get_log(logger_name: str = "permissionmanager") -> logging.Logger:
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)


    file_handler = TimedRotatingFileHandler(
        filename=f"/var/log/outsource/{logger_name}.log",
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