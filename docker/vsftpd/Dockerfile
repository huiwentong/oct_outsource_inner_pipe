# 演示用 vsftpd 子模块：提供 FTP 服务并输出 xferlog 摘要日志
FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends vsftpd \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /srv/ftp /var/log/vsftpd /etc/vsftpd

COPY vsftpd.conf /etc/vsftpd/vsftpd.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 21 30000-30100

ENTRYPOINT ["/entrypoint.sh"]