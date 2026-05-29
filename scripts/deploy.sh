#!/bin/bash
# 域名管家 - 部署脚本
# 用于将代码部署到服务器

set -e

echo "====================================="
echo "域名管家 - 部署脚本"
echo "====================================="

# 项目根目录
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]})/.." && pwd)
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo ""
echo "1. 检查环境..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "创建Python虚拟环境..."
    cd "$BACKEND_DIR"
    python3 -m venv venv
fi

echo ""
echo "2. 安装后端依赖..."
cd "$BACKEND_DIR"
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "3. 构建前端..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi
npm run build

echo ""
echo "4. 创建必要的目录..."
mkdir -p "$BACKEND_DIR/data"
mkdir -p "$BACKEND_DIR/logs"
mkdir -p "$BACKEND_DIR/data/backups"

echo ""
echo "5. 复制配置文件..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "请编辑 $BACKEND_DIR/.env 文件配置"
fi

echo ""
echo "====================================="
echo "部署完成！"
echo "====================================="
echo ""
echo "后续步骤："
echo "1. 编辑 $BACKEND_DIR/.env 配置环境变量"
echo "2. 运行 $PROJECT_DIR/scripts/init_db.py 初始化数据库"
echo "3. 配置 Nginx 和 Systemd"
echo "4. 启动服务"
