# syntax=docker/dockerfile:1
# versionwatch 镜像：使用 uv 安装依赖后运行常驻 daemon
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 先只拷贝依赖清单，充分利用构建缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# 再拷贝源码并安装项目自身（含 versionwatch 入口）
COPY versionwatch ./versionwatch
COPY lib ./lib
COPY logger ./logger

# 运行时需要挂载：FTP 存储、vsftpd 日志、tail 状态目录
VOLUME ["/srv/ftp", "/var/log/vsftpd", "/var/lib/versionwatch"]

CMD ["python", "-m", "versionwatch.__main__"]