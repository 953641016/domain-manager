#!/bin/bash
# ============================================================================
# 域名管家 - 服务器部署脚本
# 服务器: 115.28.211.155 (阿里云 Ubuntu 24.04)
# 域名: d.fwxg.com
# ============================================================================

set -e

echo "============================================"
echo "  域名管家 - 自动部署脚本"
echo "  服务器: 115.28.211.155"
echo "  系统: Ubuntu 24.04 LTS"
echo "============================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ============================================================================
# 第1步: 更新系统
# ============================================================================
echo ""
echo "=========================================="
echo "第1步: 更新系统"
echo "=========================================="

apt update && apt upgrade -y
print_status "系统更新完成"

# ============================================================================
# 第2步: 安装Docker
# ============================================================================
echo ""
echo "=========================================="
echo "第2步: 安装Docker"
echo "=========================================="

# 安装依赖
apt install -y apt-transport-https ca-certificates curl software-properties-common

# 添加Docker官方GPG密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加Docker仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动Docker
systemctl start docker
systemctl enable docker

print_status "Docker安装完成"

# ============================================================================
# 第3步: 创建项目目录
# ============================================================================
echo ""
echo "=========================================="
echo "第3步: 创建项目目录"
echo "=========================================="

mkdir -p /opt/domain-manager
cd /opt/domain-manager

print_status "项目目录创建完成: /opt/domain-manager"

# ============================================================================
# 第4步: 创建后端环境变量文件
# ============================================================================
echo ""
echo "=========================================="
echo "第4步: 配置环境变量"
echo "=========================================="

# 生成安全密钥
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || openssl rand -base64 48)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "temporary-encryption-key-please-change")

# 创建后端.env文件
cat > backend/.env << 'ENVEOF'
# ============================================================================
# 域名管家 - 后端环境变量配置
# ============================================================================

# 域名和 CORS 配置
FRONTEND_DOMAIN=d.fwxg.com
BACKEND_DOMAIN=d.fwxg.com
ALLOWED_ORIGINS=https://d.fwxg.com,http://d.fwxg.com
FRONTEND_BASE_URL=https://d.fwxg.com

# JWT 认证配置
JWT_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480

# 数据加密配置
ENCRYPTION_KEY=CHANGE_THIS_TO_FERNET_KEY

# 飞书应用配置
FEISHU_APP_ID=cli_aa90bce2dd78dbdf
FEISHU_APP_SECRET=zDodBxkkPRlSSpt2ejLjRhxJXNYpN5gk
FEISHU_VERIFICATION_TOKEN=
FEISHU_ENCRYPT_KEY=
SUPER_ADMIN_FEISHU_USER_ID=

# 数据库配置
DATABASE_URL=sqlite:///./data/domain_manager.db

# 域名专员（管理员）飞书用户ID
ADMIN_USER_IDS=

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
ENVEOF

# 替换密钥占位符
sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" backend/.env
sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" backend/.env

print_status "后端环境变量配置完成"

# ============================================================================
# 第5步: 配置Nginx
# ============================================================================
echo ""
echo "=========================================="
echo "第5步: 配置Nginx"
echo "=========================================="

mkdir -p nginx/conf.d

# 创建Nginx配置
cat > nginx/conf.d/domainmanager.conf << 'NGINXEOF'
server {
    listen 80;
    listen [::]:80;
    server_name d.fwxg.com;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
}
NGINXEOF

print_status "Nginx配置完成"

# ============================================================================
# 第6步: 构建并启动服务
# ============================================================================
echo ""
echo "=========================================="
echo "第6步: 构建并启动服务"
echo "=========================================="

cd /opt/domain-manager

# 构建并启动
docker compose up -d --build

print_status "服务构建并启动完成"

# ============================================================================
# 第7步: 初始化数据库
# ============================================================================
echo ""
echo "=========================================="
echo "第7步: 初始化数据库"
echo "=========================================="

sleep 10

docker exec domain-manager-backend python scripts/init_db.py

print_status "数据库初始化完成"

# ============================================================================
# 第8步: 检查服务状态
# ============================================================================
echo ""
echo "=========================================="
echo "第8步: 检查服务状态"
echo "=========================================="

docker compose ps

echo ""
echo "============================================"
echo "  部署完成！"
echo "============================================"
echo ""
echo "访问地址: http://115.28.211.155"
echo "域名访问: https://d.fwxg.com (需配置DNS)"
echo ""
echo "请完成以下后续步骤:"
echo "1. 在阿里云控制台配置域名解析: d.fwxg.com -> 115.28.111.155"
echo "2. 在飞书开放平台配置重定向URL"
echo "3. 在 backend/.env 中填入超级管理员飞书用户ID"
echo "4. 重启服务: docker compose restart"
echo ""
