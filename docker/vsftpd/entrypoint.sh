#!/usr/bin/env bash
# 创建演示 FTP 用户并启动 vsftpd（生产环境请改用真实账号体系/挂载）
set -euo pipefail

FTP_USER="${FTP_USER:-ftpuser}"
FTP_PASS="${FTP_PASS:-ftpuser123}"

if ! id -u "$FTP_USER" >/dev/null 2>&1; then
    useradd -m -d /srv/ftp -s /bin/bash "$FTP_USER"
    echo "$FTP_USER:$FTP_PASS" | chpasswd
fi

mkdir -p /srv/ftp
chown -R "$FTP_USER":"$FTP_USER" /srv/ftp

mkdir -p /var/log/vsftpd
touch /var/log/vsftpd/vsftpd.log
chmod 666 /var/log/vsftpd/vsftpd.log

exec vsftpd /etc/vsftpd/vsftpd.conf