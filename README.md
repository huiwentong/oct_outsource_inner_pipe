# outsource-pip · 外包收发包平台

面向十月文化外包收发包流程的根工程。当前包含第一个 Linux 常驻子模块：

- **versionwatch**：FTP 存储空间文件变更监控 daemon（版本监控模块）

## versionwatch 架构

针对“物理存储空间（FTP 服务）”做文件监控，把每一次变更（谁上传、多大、是否覆盖原文件、删除等）记录进
PostgreSQL 历史表。四个数据来源相互配合：

```
FTP 日志(vsftpd xferlog)  ──┐
watchdog(inotify) 事件     ──┼──► 统一事件 FileEvent ──► 去抖+合并 ──► PostgreSQL
定时 hash 校验             ──┘                            (file_history / file_state)
```

| 来源 | 作用 | 说明 |
| --- | --- | --- |
| FTP 日志 | 记录“谁”上传/删除/重命名、大小、客户端 IP | 解析 vsftpd `OK UPLOAD/DELETE/RENAME` 摘要行 |
| watchdog | 实时捕获文件系统变更 | inotify 递归监听，事件去抖后取最终状态 |
| PostgreSQL 历史表 | 持久化每一次变更与版本号 | `file_history` 追加写 + `file_state` 当前状态 |
| 定时 hash 校验 | 兜底发现绕过 FTP/事件的静默变更 | 周期对比 size/mtime/checksum，定期全量 hash |

多来源事件按“路径 + 时间窗口”合并：FTP 日志提供操作者信息，watchdog 提供最终文件状态，合并为一条历史记录。
覆盖原文件时自动递增版本号（例如 v001 → v002）并在 `overwritten` 列标记。

## 目录结构

```
pyproject.toml              # uv 工程（根目录统一管理 Python 依赖）
uv.lock                     # uv 锁定文件
docker-compose.yml          # docker 编排：postgres / versionwatch / vsftpd
docker/
  versionwatch.Dockerfile   # versionwatch 镜像
  vsftpd/                   # 演示用 FTP 子模块
versionwatch/
  src/versionwatch/
    config.py               # VW_ 前缀环境变量配置
    events.py               # 统一事件模型 FileEvent
    ftp_log.py              # vsftpd 日志解析 + tail（支持轮转/截断）
    fs_watch.py             # watchdog(inotify) 监听
    hash_scan.py            # 定时 hash 校验
    pipeline.py             # 去抖 + 多来源合并
    recorder.py             # 历史表写入 + 版本号逻辑
    db.py                   # PostgreSQL schema 与访问
    daemon.py               # 常驻 daemon 主循环
  tests/                    # 单元测试
```

## 快速开始

### 本地开发（uv）

```bash
uv sync                       # 安装依赖（根目录统一管理；首次会自动生成 uv.lock）
uv lock                       # 有网络时固化版本，保证可复现构建
uv run versionwatch --help    # 打印配置错误时给出必需环境变量
uv run pytest                 # 运行测试
```

运行前设置环境变量（或复制 `.env.example` 为 `.env`）：

```bash
export VW_ROOT_DIR=/srv/ftp
export VW_FTP_LOG=/var/log/vsftpd/vsftpd.log
export VW_DATABASE_URL=postgresql://versionwatch:versionwatch@localhost:5432/versionwatch
```

### Docker 一键启动（含演示 FTP）

```bash
docker compose up -d --build
```

> 构建时若缺少 `uv.lock`，uv 会在镜像内自动解析生成；建议在本地执行过 `uv lock` 后再构建，保证可复现。

启动后：

- PostgreSQL：`postgres:16`，库/用户 `versionwatch`
- versionwatch daemon：监控 `/srv/ftp`，tail vsftpd 日志，写历史表
- vsftpd：演示账号 `ftpuser / ftpuser123`，上传文件即触发监控

验证监控效果：

```bash
# 通过 FTP 上传一个文件
curl -T some.ma ftp://ftpuser:ftpuser123@localhost/oct/mk2/shot/s03/a.ma

# 查看历史记录
docker compose exec postgres psql -U versionwatch -d versionwatch \
  -c "SELECT rel_path, event_type, version, overwritten, actor, file_size, observed_at
      FROM file_history ORDER BY id;"
```

### 生产部署

生产环境通常 versionwatch 与真实 vsftpd 同机运行：把 `docker-compose.yml` 中
`ftpdata`/`ftplogs` 卷替换为宿主机 bind mount（`/srv/ftp:/srv/ftp`、`/var/log/vsftpd:/var/log/vsftpd`），
并关闭 `vsftpd` 服务。日志轮转建议使用 `copytruncate`（daemon 已兼容截断与轮转两种方式）。

## 配置项

所有配置使用 `VW_` 前缀环境变量，列表类型需传 JSON 数组。

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `VW_ROOT_DIR` | 必填 | FTP 存储根目录（挂载点） |
| `VW_FTP_LOG` | 必填 | vsftpd 日志路径 |
| `VW_DATABASE_URL` | 必填 | PostgreSQL DSN |
| `VW_LOG_STATE_FILE` | `/var/lib/versionwatch/ftp_log.state` | tail 断点状态 |
| `VW_LOG_START_MODE` | `end` | 无状态文件时从头读还是跳过历史 |
| `VW_DEBOUNCE_SECONDS` | `5` | 同一路径静默多久视为写入结束 |
| `VW_MERGE_WINDOW_SECONDS` | `10` | FTP 日志与 watchdog 事件合并窗口 |
| `VW_HASH_SCAN_ENABLED` | `true` | 是否启用定时 hash 校验 |
| `VW_HASH_SCAN_INTERVAL` | `900` | 扫描间隔（秒） |
| `VW_FULL_HASH_CYCLES` | `24` | 每 N 轮做一次全量 hash |
| `VW_HASH_ALGO` | `blake2b` | 摘要算法 |
| `VW_HASH_ON_EVENT` | `true` | 事件发生时是否计算 checksum |
| `VW_HASH_ON_EVENT_MAX_BYTES` | `0` | 事件 hash 的文件大小上限（0=不限） |
| `VW_EXCLUDE_PATTERNS` | 见 config.py | 排除正则（JSON 数组） |
| `VW_LOG_TIMEZONE` | `Asia/Shanghai` | vsftpd 日志本地时区 |
| `VW_LOG_LEVEL` | `INFO` | 日志级别 |

## 数据库设计

- `file_history`：追加写的变更历史。核心列：`rel_path`、`source`、`event_type`、
  `version`、`previous_version`、`overwritten`、`actor`、`client_ip`、`file_size`、
  `checksum`、`details(jsonb)`、`observed_at`。`event_id`(uuid) 唯一，幂等写入。
- `file_state`：每个路径的当前状态（size/mtime/checksum/version/is_deleted），
  供 hash 校验对比与版本号递增。
- `scan_state`：最近一次 hash 扫描的统计。

版本规则：文件首次出现为 `v001`；已存在文件被覆盖为 `v002`、`v003`……；
删除后重新上传版本号继续累加，便于审计。