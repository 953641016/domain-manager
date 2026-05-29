#!/bin/bash

set -e

echo "=========================================="
echo "  域名管家 - Docker 部署脚本"
echo "=========================================="

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未安装Docker，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未安装docker-compose，请先安装docker-compose"
    exit 1
fi

# 检查环境变量文件
if [ ! -f "backend/.env" ]; then
    echo "提示: 未找到backend/.env文件"
    if [ -f "backend/.env.example" ]; then
        echo "正在从.env.example创建.env..."
        cp backend/.env.example backend/.env
        echo "请编辑 backend/.env 文件填入真实配置"
    fi
fi

# 构建并启动服务
echo ""
echo "正在构建Docker镜像..."
docker-compose build

echo ""
echo "正在启动服务..."
docker-compose up -d

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "服务访问地址："
echo "  - 前端: http://localhost"
echo "  - API: http://localhost/api"
echo "  - 健康检查: http://localhost/api/health"
echo ""
echo "常用命令："
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo "  - 查看状态: docker-compose ps"
echo ""
