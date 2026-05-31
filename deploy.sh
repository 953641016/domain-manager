#!/bin/bash
# 域名管家 - 服务器部署脚本
# 用法：
#   ./deploy.sh          全量重建（前端 + 后端）
#   ./deploy.sh frontend 只重建前端
#   ./deploy.sh backend  只重建后端

set -e

cd /opt/domain-manager

echo "=== [1/4] 拉取最新代码 ==="
git pull

TARGET=${1:-all}

echo "=== [2/4] 重建容器（$TARGET）==="
if [ "$TARGET" = "frontend" ]; then
    docker compose up -d --build --no-deps frontend
elif [ "$TARGET" = "backend" ]; then
    docker compose up -d --build --no-deps backend
else
    docker compose up -d --build
fi

echo "=== [3/4] 清理旧镜像 ==="
docker image prune -f

echo "=== [4/4] 验证服务状态 ==="
docker compose ps
echo ""
curl -s http://localhost:8000/health && echo ""
echo ""
echo "✓ 部署完成"
