# 演示用 vsftpd 子模块：提供 FTP 服务并输出 xferlog 摘要日志
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends vsftpd \
    && rm -rf /var/lib/apt/lists/*

# 创建固定的运行目录
RUN mkdir -p \
    /srv/ftp \
    /var/log/vsftpd \
    /etc/vsftpd \
    /var/run/vsftpd/empty

WORKDIR /app
COPY docker/vsftpd/vsftpd.conf /etc/vsftpd/vsftpd.conf
COPY docker/vsftpd/entrypoint.sh /entrypoint.sh

ENV UV_HTTP_TIMEOUT=300
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project


COPY permissionmanager ./permissionmanager
RUN uv sync --no-dev --frozen

RUN chmod +x /entrypoint.sh

EXPOSE 21 30000-30100 8000 

ENTRYPOINT ["/entrypoint.sh"]