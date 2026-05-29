# 服务器部署指南

## 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 115.28.211.155 |
| 用户 | root |
| 系统 | Ubuntu 24.04 LTS |
| 配置 | 2核2G内存 + 40GB SSD |
| 域名 | d.fwxg.com |

---

## 飞书应用凭证

| 配置项 | 值 |
|--------|-----|
| App ID | cli_aa90bce2dd78dbdf |
| App Secret | zDodBxkkPRlSSpt2ejLjRhxJXNYpN5gk |

---

## 部署步骤

### 第1步：SSH连接服务器

```bash
ssh root@115.28.211.155
```

### 第2步：下载部署脚本

```bash
# 在服务器上创建项目目录
mkdir -p /opt/domain-manager
cd /opt/domain-manager

# 下载项目代码（如果已上传）
# 或者直接使用部署脚本
```

### 第3步：运行部署脚本

```bash
# 下载部署脚本
curl -O https://raw.githubusercontent.com/your-repo/deploy.sh

# 或者手动创建（内容见下方）

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

---

## 手动部署步骤（如果没有脚本）

### 1. 更新系统

```bash
apt update && apt upgrade -y
```

### 2. 安装Docker

```bash
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
```

### 3. 上传项目代码

```bash
# 在本地Windows上，使用Git Bash或WSL
cd d:/WorkSpace/domain-manager

# 使用scp上传整个项目
scp -r . root@115.28.211.155:/opt/domain-manager/
```

### 4. 配置环境变量

```bash
cd /opt/domain-manager

# 编辑后端环境变量
nano backend/.env
```

### 5. 配置Nginx

```bash
mkdir -p nginx/conf.d

# 编辑Nginx配置
nano nginx/conf.d/domainmanager.conf
```

### 6. 构建并启动

```bash
cd /opt/domain-manager

# 构建并启动服务
docker compose up -d --build
```

### 7. 初始化数据库

```bash
# 等待服务启动
sleep 10

# 初始化数据库
docker exec domain-manager-backend python scripts/init_db.py
```

---

## 验证部署

### 检查服务状态

```bash
docker compose ps
```

### 访问测试

```bash
# 通过IP访问
curl http://115.28.211.155

# 通过域名访问（需先配置DNS）
curl https://d.fwxg.com
```

---

## 后续配置

### 1. 配置域名解析

在阿里云控制台：
1. 进入"域名解析DNS"
2. 添加A记录：
   - 主机记录: @ 或 d
   - 记录类型: A
   - 记录值: 115.28.211.155

### 2. 配置飞书应用

在飞书开放平台：
1. 进入应用详情页
2. 找到"安全设置"
3. 添加重定向URL: `https://d.fwxg.com/dm/api/v1/auth/feishu/callback`

### 3. 获取超级管理员飞书用户ID

在飞书开放平台：
1. 进入应用详情页
2. 找到"成员与权限"
3. 查找您的用户ID（`ou_` 开头）

### 4. 更新环境变量

```bash
cd /opt/domain-manager

# 编辑后端环境变量
nano backend/.env

# 更新以下字段：
# SUPER_ADMIN_FEISHU_USER_ID=ou_您的飞书用户ID
```

### 5. 重启服务

```bash
docker compose restart
```

---

## 常见问题

### Q: 无法访问服务器

A: 检查阿里云安全组配置：
1. 进入ECS实例详情
2. 找到"安全组"
3. 添加入站规则：
   - 端口: 80, 443
   - 协议: TCP
   - 源: 0.0.0.0/0

### Q: Docker构建失败

A: 检查内存是否足够（2G可能不够）：
```bash
# 查看内存使用
free -h

# 如果内存不足，可以创建Swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q: 飞书登录失败

A: 检查飞书应用配置：
1. 确认App ID和App Secret正确
2. 确认重定向URL配置正确
3. 确认应用已发布（或在测试企业中）

---

## 监控和日志

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看后端日志
docker compose logs -f backend

# 查看Nginx日志
docker compose logs -f nginx
```

### 重启服务

```bash
docker compose restart
```

### 停止服务

```bash
docker compose down
```

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker compose up -d --build
```
