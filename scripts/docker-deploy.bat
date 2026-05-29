@echo off
chcp 65001 >nul

echo ==========================================
echo   域名管家 - Docker 部署脚本
echo ==========================================

cd /d "%~dp0.."

REM 检查Docker是否安装
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未安装Docker，请先安装Docker Desktop
    exit /b 1
)

where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未安装docker-compose，请先安装docker-compose
    exit /b 1
)

REM 检查环境变量文件
if not exist "backend\.env" (
    echo 提示: 未找到backend\.env文件
    if exist "backend\.env.example" (
        echo 正在从.env.example创建.env...
        copy backend\.env.example backend\.env
        echo 请编辑 backend\.env 文件填入真实配置
    )
)

REM 构建并启动服务
echo.
echo 正在构建Docker镜像...
docker-compose build

echo.
echo 正在启动服务...
docker-compose up -d

echo.
echo ==========================================
echo   部署完成！
echo ==========================================
echo.
echo 服务访问地址：
echo   - 前端: http://localhost
echo   - API: http://localhost/api
echo   - 健康检查: http://localhost/api/health
echo.
echo 常用命令：
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo   - 查看状态: docker-compose ps
echo.
