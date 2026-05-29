# ============================================================================
# 域名管家 - 本地部署脚本 (PowerShell)
# 自动上传项目到服务器并执行部署
# ============================================================================

$SERVER_IP = "115.28.211.155"
$SERVER_USER = "root"
$SERVER_PASS = "Cy1411dd"
$REMOTE_DIR = "/opt/domain-manager"
$LOCAL_DIR = "d:\WorkSpace\domain-manager"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  域名管家 - 自动部署脚本" -ForegroundColor Cyan
Write-Host "  服务器: $SERVER_IP" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 第1步: 上传项目代码
# ============================================================================
Write-Host "[1/4] 上传项目代码到服务器..." -ForegroundColor Yellow

# 使用 scp 上传（排除不需要的文件）
$excludeDirs = @("node_modules", ".git", "__pycache__", "*.pyc", "venv", ".env", "data", "logs")

# 创建远程目录
Write-Host "  创建远程目录..." -ForegroundColor Gray
$sshCmd = "ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP `"mkdir -p $REMOTE_DIR`""
Write-Host "  执行: $sshCmd" -ForegroundColor Gray

# 使用 plink 或 scp 上传
# 由于 PowerShell 的 scp 不支持直接传密码，我们需要使用 plink
# 如果没有 plink，可以使用 WinSCP 或手动上传

Write-Host ""
Write-Host "请手动执行以下命令上传项目：" -ForegroundColor Yellow
Write-Host ""
Write-Host "方法1: 使用 Git Bash (推荐)" -ForegroundColor Green
Write-Host "  cd d:/WorkSpace/domain-manager" -ForegroundColor White
Write-Host '  scp -r . root@115.28.211.155:/opt/domain-manager/' -ForegroundColor White
Write-Host ""
Write-Host "方法2: 使用 WinSCP" -ForegroundColor Green
Write-Host "  下载 WinSCP: https://winscp.net/eng/download.php" -ForegroundColor White
Write-Host "  连接信息:" -ForegroundColor White
Write-Host "    主机: $SERVER_IP" -ForegroundColor White
Write-Host "    用户名: $SERVER_USER" -ForegroundColor White
Write-Host "    密码: $SERVER_PASS" -ForegroundColor White
Write-Host "    远程目录: $REMOTE_DIR" -ForegroundColor White
Write-Host ""

# ============================================================================
# 第2步: SSH连接服务器执行部署
# ============================================================================
Write-Host "[2/4] 连接服务器执行部署..." -ForegroundColor Yellow
Write-Host ""
Write-Host "上传完成后，请 SSH 连接服务器执行部署：" -ForegroundColor Yellow
Write-Host ""
Write-Host "ssh $SERVER_USER@$SERVER_IP" -ForegroundColor White
Write-Host "输入密码: $SERVER_PASS" -ForegroundColor White
Write-Host ""
Write-Host "然后执行以下命令：" -ForegroundColor Yellow
Write-Host ""
Write-Host "cd $REMOTE_DIR" -ForegroundColor White
Write-Host "chmod +x deploy_server.sh" -ForegroundColor White
Write-Host "./deploy_server.sh" -ForegroundColor White
Write-Host ""

# ============================================================================
# 第3步: 配置域名解析
# ============================================================================
Write-Host "[3/4] 配置域名解析..." -ForegroundColor Yellow
Write-Host ""
Write-Host "请在 DNSPod 添加 A 记录：" -ForegroundColor Yellow
Write-Host "  域名: fwxg.com" -ForegroundColor White
Write-Host "  主机记录: d" -ForegroundColor White
Write-Host "  记录类型: A" -ForegroundColor White
Write-Host "  记录值: $SERVER_IP" -ForegroundColor White
Write-Host ""

# ============================================================================
# 第4步: 配置飞书应用
# ============================================================================
Write-Host "[4/4] 配置飞书应用..." -ForegroundColor Yellow
Write-Host ""
Write-Host "请在飞书开放平台配置：" -ForegroundColor Yellow
Write-Host "  1. 进入应用详情页" -ForegroundColor White
Write-Host "  2. 找到 安全设置" -ForegroundColor White
Write-Host "  3. 添加重定向URL: https://d.fwxg.com/api/v1/auth/feishu/callback" -ForegroundColor White
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  部署指南完成！" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "后续步骤：" -ForegroundColor Yellow
Write-Host "1. 上传项目代码到服务器" -ForegroundColor White
Write-Host "2. SSH连接服务器执行部署脚本" -ForegroundColor White
Write-Host "3. 配置域名解析" -ForegroundColor White
Write-Host "4. 配置飞书应用重定向URL" -ForegroundColor White
Write-Host "5. 获取飞书用户ID并填入配置" -ForegroundColor White
Write-Host ""
