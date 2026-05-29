#!/bin/bash
# 域名管家 - 备份脚本
# 用于备份数据库和配置文件

set -e

BACKUP_DIR="/opt/domainmanager/backend/data/backups"
DB_PATH="/opt/domainmanager/backend/data/domainmgr.db"
ENV_PATH="/opt/domainmanager/backend/.env"
DATE=$(date +%Y%m%d_%H%M%S)

echo "====================================="
echo "域名管家 - 备份脚本"
echo "====================================="
echo "备份时间: $DATE"
echo ""

mkdir -p "$BACKUP_DIR"

echo "1. 备份数据库..."
if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_DIR/domainmgr_$DATE.db"
    echo "   完成: domainmgr_$DATE.db"
else
    echo "   警告: 数据库文件不存在"
fi

echo "2. 备份配置文件..."
if [ -f "$ENV_PATH" ]; then
    cp "$ENV_PATH" "$BACKUP_DIR/env_$DATE"
    echo "   完成: env_$DATE"
else
    echo "   警告: 配置文件不存在"
fi

echo "3. 清理旧备份（保留30天）..."
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "env_*" -mtime +30 -delete
echo "   完成"

echo ""
echo "====================================="
echo "备份完成！"
echo "备份位置: $BACKUP_DIR"
echo "====================================="
