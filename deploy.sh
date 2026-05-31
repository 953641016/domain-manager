#!/bin/bash
# 域名管家 - 服务器部署脚本
# 用法：
#   ./deploy.sh          全量重建（前端 + 后端）
#   ./deploy.sh frontend 只重建前端
#   ./deploy.sh backend  只重建后端

set -e

cd /opt/domain-manager

echo "=== [1/4] 拉取最新代码 ==="
if ! git pull 2>&1; then
    PROXY_FILE="$HOME/.git-proxy-url"
    if [ -f "$PROXY_FILE" ]; then
        echo "直连失败，通过代理重试..."
        HTTPS_PROXY="$(cat "$PROXY_FILE")" git -c http.proxyAuthMethod=basic pull
    else
        echo "git pull 失败，且 $PROXY_FILE 不存在，退出"
        exit 1
    fi
fi

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
