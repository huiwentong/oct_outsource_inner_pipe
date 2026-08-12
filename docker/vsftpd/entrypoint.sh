#!/usr/bin/env bash
# 创建演示 FTP 用户并启动 vsftpd（生产环境请改用真实账号体系/挂载）
set -e

# 启动 FTP
vsftpd /etc/vsftpd/vsftpd.conf &

# 启动 PermissionManager
uvicorn permissionmanager.app:app \
    --host 0.0.0.0 \
    --port 8000 &

# 保持容器运行
wait -n