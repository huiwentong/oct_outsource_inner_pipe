"""versionwatch 守护进程入口。"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from versionwatch.config import Settings
from versionwatch.db import connect_with_retry, init_schema, open_connection
from versionwatch.ftp_log import FtpLogTailer
from versionwatch.fs_watch import FsWatcher
from versionwatch.hash_scan import HashScanner
from versionwatch.pipeline import Pipeline
from versionwatch.recorder import Recorder
from logger.core import watch_logger


async def _run(settings: Settings) -> None:
    logger = watch_logger
    logger.info(
        "versionwatch 启动 root_dir=%s ftp_log=%s", settings.root_dir, settings.ftp_log
    )

    if not settings.root_dir.is_dir():
        raise SystemExit(f"监控根目录不存在: {settings.root_dir}")



    # 数据库初始化（建表）
    bootstrap = await connect_with_retry(settings)
    try:
        await init_schema(bootstrap)
    finally:
        await bootstrap.close()




    queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

    recorder = Recorder(settings, open_connection)
    pipeline = Pipeline(settings, queue, recorder)
    tailer = FtpLogTailer(settings, queue)
    # scanner = HashScanner(settings, open_connection, queue.put_nowait)
    # watcher = FsWatcher(settings, queue)

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _request_stop(signame: str) -> None:
        logger.info("收到 %s，正在优雅退出...", signame)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop, sig.name)
        except (NotImplementedError, RuntimeError):
            pass  # 仅主线程可用；Windows 下忽略

    tasks = [
        asyncio.create_task(pipeline.run(), name="pipeline"),
        asyncio.create_task(tailer.run(queue.put_nowait), name="ftp-log-tailer"),
    ]

    # watcher.start(loop)
    try:
        await stop.wait()
    finally:
        logger.info("开始优雅退出...")
        # watcher.stop()
        pipeline.stop()
        tailer.close()
        try:
            await asyncio.wait_for(asyncio.shield(tasks[0]), timeout=settings.shutdown_grace_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                "流水线在 %.1f 秒内未完成，强制退出", settings.shutdown_grace_seconds
            )
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await recorder.close()
    logger.info("versionwatch 已退出")


def main() -> None:
    try:
        settings = Settings()
    except Exception as exc:
        print(f"配置加载失败: {exc}", file=sys.stderr)
        print("必需环境变量: VW_ROOT_DIR, VW_FTP_LOG, VW_DATABASE_URL", file=sys.stderr)
        sys.exit(2)
    try:
        asyncio.run(_run(settings))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()