"""运行配置。

所有配置均可通过环境变量覆盖，前缀为 ``VW_``（例如 ``VW_DATABASE_URL``），
也可写入项目根目录的 ``.env`` 文件。
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VW_",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 被监控的 FTP 存储空间挂载点（容器内路径）
    root_dir: Path = Field(default=Path('/srv/ftp'), description="FTP 存储根目录（挂载点）")

    # vsftpd 日志文件（包含 OK UPLOAD / OK DELETE / OK RENAME 摘要行）
    ftp_log: Path = Field(default=Path('/var/log/vsftpd'), description="vsftpd 日志路径")

    # PostgreSQL 连接串
    database_url: str = Field(default='postgresql://admin:123456@postgres:5432/outsource_inner_pipe', description="PostgreSQL DSN")

    # 日志 tail 状态文件（保存 inode/offset，用于重启后续传）
    log_state_file: Path = Path("/var/lib/versionwatch/ftp_log.state")

    # 事件队列文件，用于中途退出保存未执行的队列
    queue_file: Path = Path("/var/lib/versionwatch/queue.json")

    # 首次启动（无状态文件）时的日志起始位置：end 跳过历史 / begin 从头读
    log_start_mode: str = "end"
    log_poll_interval: float = 1.0

    # watchdog 事件去抖窗口：同一路径静默 N 秒后才认为写入结束
    debounce_seconds: float = 1.0

    # 多来源合并窗口：ftp_log 与 watchdog 事件在此窗口内按路径合并
    merge_window_seconds: float = 10.0

    # 定时 hash 校验
    hash_scan_enabled: bool = True
    hash_scan_interval: int = 900
    hash_scan_grace_seconds: float = 15.0  # 跳过最近仍在写入的文件
    full_hash_cycles: int = 24  # 每 N 轮做一次全量 hash 校验
    hash_algo: str = "blake2b"

    # 事件发生时是否计算 checksum
    hash_on_event: bool = True
    hash_on_event_max_bytes: int = 0  # 0 表示不限制

    # 扫描时单文件 hash 上限（0 表示不限制）
    hash_scan_max_bytes: int = 0

    chunk_size: int = 1 << 20

    # 排除规则（正则，匹配相对路径）
    exclude_patterns: list[str] = [
        r"\.part$",
        r"\.tmp$",
        r"\.swp$",
        r"~$",
        r"(^|/)\.",  # 隐藏文件/目录
        r"\.DS_Store$",
    ]

    # vsftpd 日志使用服务器本地时间
    log_timezone: str = "Asia/Shanghai"

    db_connect_retries: int = 10
    db_connect_delay: float = 3.0

    shutdown_grace_seconds: float = 10.0
    log_level: str = "INFO"