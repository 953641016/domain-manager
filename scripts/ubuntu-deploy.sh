#!/bin/bash

set -e

echo "=========================================="
echo "  域名管家 - Ubuntu 22.04 部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}请不要使用root用户运行此脚本${NC}"
    exit 1
fi

# 检查系统版本
if ! grep -q "Ubuntu 22.04" /etc/os-release; then
    echo -e "${YELLOW}警告：此脚本专为Ubuntu 22.04设计，其他系统可能不兼容${NC}"
    read -p "是否继续？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 系统更新
echo ""
echo -e "${GREEN}[1/6] 更新系统...${NC}"
sudo apt update && sudo apt upgrade -y

# 2. 安装Docker
echo ""
echo -e "${GREEN}[2/6] 安装Docker...${NC}"
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

sudo systemctl start docker
sudo systemctl enable docker

sudo usermod -aG docker $USER

echo -e "${GREEN}Docker安装完成${NC}"

# 3. 安装Docker Compose
echo ""
echo -e "${GREEN}[3/6] 安装Docker Compose...${NC}"
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo -e "${GREEN}Docker Compose安装完成${NC}"

# 4. 部署项目
echo ""
echo -e "${GREEN}[4/6] 部署项目...${NC}"

# 创建项目目录
sudo mkdir -p /opt/domain-manager
sudo chown -R $USER:$USER /opt/domain-manager
cd /opt/domain-manager

# 克隆项目
if [ ! -d ".git" ]; then
    git clone https://github.com/953641016/domain-manager.git .
else
    git pull
fi

# 配置环境变量
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}请编辑 backend/.env 文件配置环境变量${NC}"
fi

echo -e "${GREEN}项目部署完成${NC}"

# 5. 配置防火墙
echo ""
echo -e "${GREEN}[5/6] 配置防火墙...${NC}"
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo -e "${GREEN}防火墙配置完成${NC}"

# 6. 启动服务
echo ""
echo -e "${GREEN}[6/6] 启动服务...${NC}"
docker-compose up -d

echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "服务访问地址："
echo "  - 前端: http://localhost"
echo "  - API: http://localhost/api"
echo "  - 健康检查: http://localhost/api/health"
echo ""
echo "下一步："
echo "  1. 编辑 backend/.env 配置环境变量"
echo "  2. docker-compose restart 重启服务"
echo ""
echo "常用命令："
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo "  - 查看状态: docker-compose ps"
echo ""
echo -e "${YELLOW}提示：需要重新登录才能免sudo运行docker${NC}"
echo ""
