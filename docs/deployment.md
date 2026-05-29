# 域名管家 - 部署文档

## 一、技术栈

### 1.1 完整技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|----------|
| **前端** | React | 18.x |
| | TypeScript | 5.x |
| | Tailwind CSS | 3.x |
| | Vite | 5.x - 构建工具 |
| **后端** | Python | 3.11+ |
| | FastAPI | 0.100+ - Web框架 |
| | SQLAlchemy | 2.0+ - ORM |
| | Pydantic | 2.x - 数据验证 |
| | python-dotenv | 环境变量管理 |
| | aiohttp | HTTP客户端（调用注册商API） |
| **数据库** | SQLite | 3.35+ - 轻量级数据库 |
| **Web服务器** | Nginx | 1.20+ - 反向代理 |
| **进程管理** | Gunicorn/Uvicorn | ASGI服务器 |
| **系统** | CentOS | 7/8/9 - 生产环境 |

### 1.2 与PHP项目技术栈对比

| 技术 | 本项目 | PHP项目 | 隔离方式 |
|------|--------|---------|----------|
| 语言 | Python 3.11+ | PHP 7.x/8.x | 使用独立用户/虚拟环境 |
| Web服务器 | Nginx (反向代理) | Nginx + PHP-FPM | 不同的端口/路径/域名 |
| 数据库 | SQLite | MySQL | 完全独立 |
| 进程管理 | Systemd/Gunicorn | PHP-FPM | 独立Systemd服务 |

---

## 二、CentOS部署架构

### 2.1 整体架构

```
                                    ┌─────────────────┐
                                    │   外部访问        │
                                    │  (业务人员/管理员) │
                                    └────────┬────────┘
                                             │
                                             ▼
                              ┌───────────────────────────────┐
                              │   Nginx (端口 80/443)         │
                              │   ┌───────────────────────────┐│
                              │   │ 域名管家: domain.your.com ││
                              │   │  (反向代理 -> localhost:8000)││
                              │   └───────────────────────────┘│
                              │   ┌───────────────────────────┐│
                              │   │ PHP项目1: php1.your.com   ││
                              │   │  (PHP-FPM)                 ││
                              │   └───────────────────────────┘│
                              │   ┌───────────────────────────┐│
                              │   │ PHP项目2: php2.your.com   ││
                              │   │  (PHP-FPM)                 ││
                              │   └───────────────────────────┘│
                              └───────────────────────────────┘
                                         │
                  ┌──────────────────────┼──────────────────────┐
                  │                      │                      │
                  ▼                      ▼                      ▼
      ┌───────────────────────┐ ┌───────────────┐    ┌───────────────┐
      │   域名管家            │ │   PHP-FPM 1   │    │   PHP-FPM 2   │
      │   (用户: domainmgr)   │ │   (用户: www) │    │   (用户: www) │
      │   - FastAPI + Uvicorn │ └───────────────┘    └───────────────┘
      │   - SQLite数据库      │
      │   - 虚拟环境 venv     │
      └───────────────────────┘
```

### 2.2 隔离原则

1. **用户隔离**：使用独立的系统用户运行域名管家
2. **目录隔离**：独立的项目目录
3. **端口隔离**：使用独立的端口（默认8000）
4. **Nginx配置隔离**：独立的server块或vhost配置
5. **进程隔离**：独立的Systemd服务

---

## 三、系统用户和目录结构

### 3.1 创建系统用户

```bash
# 创建专用用户
sudo useradd -r -s /bin/false -m -d /opt/domainmgr domainmgr

# 检查用户
id domainmgr
```

### 3.2 目录结构

```
/opt/domainmgr/
├── domainmgr/              # 项目代码
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   └── adapters/
│   ├── frontend/           # 前端构建产物
│   ├── venv/               # Python虚拟环境
│   ├── data/               # 数据目录
│   │   └── domainmgr.db    # SQLite数据库
│   ├── logs/               # 日志目录
│   │   ├── app.log
│   │   └── access.log
│   └── .env                # 环境变量
└── scripts/                # 部署脚本
```

---

## 四、CentOS部署步骤

### 4.1 系统准备

```bash
# 更新系统
sudo yum update -y

# 安装基础工具
sudo yum install -y git vim wget curl

# 安装Python 3.11 (CentOS 7/8)
# CentOS 7: 使用IUS源
# CentOS 8/9: 直接安装
sudo yum install -y python3.11 python3.11-devel python3.11-pip

# 验证Python
python3.11 --version
```

### 4.2 安装项目

```bash
# 切换到项目目录
cd /opt/domainmgr

# 克隆代码
sudo git clone <repository-url> domainmgr
sudo chown -R domainmgr:domainmgr /opt/domainmgr

# 切换到项目用户
sudo su -s /bin/bash domainmgr

# 创建虚拟环境
cd /opt/domainmgr/domainmgr
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
# 补全所需依赖
pip install fastapi uvicorn gunicorn python-jose[cryptography] passlib[bcrypt]

# 创建必要目录
mkdir -p data logs

# 复制环境变量
cp .env.example .env
# 编辑 .env 配置
vim .env
```

### 4.3 初始化数据库

```bash
# 在虚拟环境中
source venv/bin/activate
python -c "
from database import Base, engine
Base.metadata.create_all(bind=engine)
print('数据库初始化完成')
"
```

### 4.4 配置Systemd服务

```ini
# /etc/systemd/system/domainmgr.service
[Unit]
Description=Domain Management System - 域名管家
After=network.target

[Service]
Type=notify
User=domainmgr
Group=domainmgr
WorkingDirectory=/opt/domainmgr/domainmgr
Environment="PATH=/opt/domainmgr/domainmgr/venv/bin"
ExecStart=/opt/domainmgr/domainmgr/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    --access-logfile /opt/domainmgr/domainmgr/logs/access.log \
    --error-logfile /opt/domainmgr/domainmgr/logs/app.log \
    --timeout 120 \
    main:app

Restart=always
RestartSec=10

# 资源限制
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# 加载并启动服务
sudo systemctl daemon-reload
sudo systemctl enable domainmgr
sudo systemctl start domainmgr

# 查看状态
sudo systemctl status domainmgr
sudo journalctl -u domainmgr -f
```

---

## 五、Nginx配置（与PHP项目隔离）

### 5.1 方案A：不同域名（推荐）

```nginx
# /etc/nginx/conf.d/domainmgr.conf

# 域名管家 - 独立域名
server {
    listen 80;
    listen [::]:80;
    server_name domain.yourcompany.com;  # 使用独立域名
    
    # 日志
    access_log /var/log/nginx/domainmgr_access.log;
    error_log /var/log/nginx/domainmgr_error.log;

    # 前端静态文件
    location / {
        root /opt/domainmgr/domainmgr/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # 缓存静态文件
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API反向代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# PHP项目1的配置（示例，不修改）
# /etc/nginx/conf.d/php1.conf
server {
    listen 80;
    listen [::]:80;
    server_name php1.yourcompany.com;
    
    # PHP-FPM配置
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php-fpm/php1.sock;
        fastcgi_index index.php;
        include fastcgi_params;
    }
}
```

### 5.2 方案B：同域名不同路径

```nginx
# /etc/nginx/conf.d/domainmgr.conf
server {
    listen 80;
    server_name yourcompany.com;
    
    # 域名管家在 /domainmgr 路径下
    location /domainmgr {
        alias /opt/domainmgr/domainmgr/frontend/dist;
        try_files $uri $uri/ /domainmgr/index.html;
    }
    
    location /domainmgr/api {
        rewrite ^/domainmgr/(.*) /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # PHP项目保持在根路径或其他路径
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }
    
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php-fpm/www.sock;
        include fastcgi_params;
    }
}
```

### 5.3 配置SSL（Let's Encrypt）

```bash
# 安装certbot
sudo yum install -y certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d domain.yourcompany.com

# 自动续期
sudo certbot renew --dry-run
```

### 5.4 测试Nginx配置

```bash
# 检查配置语法
sudo nginx -t

# 重启Nginx
sudo systemctl reload nginx
sudo systemctl restart nginx

# 查看状态
sudo systemctl status nginx
```

---

## 六、环境变量配置

```env
# /opt/domainmgr/domainmgr/.env

# 基础配置
APP_NAME=域名管家
APP_ENV=production
APP_DEBUG=false
APP_URL=https://domain.yourcompany.com

# 数据库
DATABASE_URL=sqlite:////opt/domainmgr/domainmgr/data/domainmgr.db

# 认证
SECRET_KEY=your-very-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# 飞书配置
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=xxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxx
FEISHU_ENCRYPT_KEY=xxxxxx

# 注册商API配置（示例）
CLOUDFLARE_API_TOKEN=xxxxxx
GODADDY_API_KEY=xxxxxx
GODADDY_API_SECRET=xxxxxx

# 系统默认配置
DEFAULT_REGISTRAR=cloudflare
DEFAULT_DNS_PROVIDER=cloudflare
```

---

## 七、日志管理

### 7.1 日志轮转配置

```logrotate
# /etc/logrotate.d/domainmgr
/opt/domainmgr/domainmgr/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 domainmgr domainmgr
    sharedscripts
    postrotate
        systemctl reload domainmgr > /dev/null 2>&1 || true
    endscript
}
```

```bash
# 测试日志轮转
sudo logrotate -d /etc/logrotate.d/domainmgr
```

---

## 八、备份策略

### 8.1 数据库备份脚本

```bash
# /opt/domainmgr/scripts/backup.sh
#!/bin/bash
BACKUP_DIR="/opt/domainmgr/backups"
DB_PATH="/opt/domainmgr/domainmgr/data/domainmgr.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库（SQLite文件直接复制）
cp $DB_PATH $BACKUP_DIR/domainmgr_$DATE.db

# 备份配置文件
cp /opt/domainmgr/domainmgr/.env $BACKUP_DIR/env_$DATE

# 保留最近30天的备份
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "env_*" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/domainmgr_$DATE.db"
```

```bash
# 设置执行权限
chmod +x /opt/domainmgr/scripts/backup.sh
chown domainmgr:domainmgr /opt/domainmgr/scripts/backup.sh

# 添加到crontab（每天凌晨3点备份）
sudo crontab -e -u domainmgr
# 添加：
0 3 * * * /opt/domainmgr/scripts/backup.sh >> /opt/domainmgr/logs/backup.log 2>&1
```

---

## 九、安全加固

### 9.1 目录权限

```bash
# 设置目录权限
sudo chown -R domainmgr:domainmgr /opt/domainmgr
sudo chmod 700 /opt/domainmgr/domainmgr/.env
sudo chmod 600 /opt/domainmgr/domainmgr/data/domainmgr.db
```

### 9.2 防火墙配置

```bash
# 仅允许80/443端口对外
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --remove-port=8000/tcp  # 不对外暴露8000端口
sudo firewall-cmd --reload
```

### 9.3 Fail2Ban（保护Nginx）

```bash
# 安装fail2ban
sudo yum install -y fail2ban

# 配置Nginx防护
# /etc/fail2ban/jail.d/nginx.conf
[nginx-http-auth]
enabled  = true
filter   = nginx-http-auth
logpath  = /var/log/nginx/error.log
maxretry = 3
bantime  = 3600

[nginx-botsearch]
enabled  = true
filter   = nginx-botsearch
logpath  = /var/log/nginx/error.log
maxretry = 2
bantime  = 3600

# 启动fail2ban
sudo systemctl enable --now fail2ban
```

---

## 十、升级部署

```bash
# 拉取最新代码
cd /opt/domainmgr/domainmgr
sudo -u domainmgr git pull origin main

# 激活虚拟环境
sudo -u domainmgr -s /bin/bash -c "
cd /opt/domainmgr/domainmgr
source venv/bin/activate
pip install -r requirements.txt
"

# 数据库迁移（如有）
sudo -u domainmgr -s /bin/bash -c "
cd /opt/domainmgr/domainmgr
source venv/bin/activate
# 执行迁移脚本
"

# 重启服务
sudo systemctl restart domainmgr

# 查看状态
sudo systemctl status domainmgr
```

---

## 十一、监控和故障排查

### 11.1 服务检查清单

```bash
# 检查所有服务状态
echo "=== Systemd Services ==="
systemctl status nginx
systemctl status domainmgr
systemctl status php-fpm  # 如有PHP项目

echo -e "\n=== Process Check ==="
ps aux | grep -E "(nginx|python|php-fpm)" | grep -v grep

echo -e "\n=== Port Check ==="
ss -tlnp | grep -E ":(80|443|8000|9000)"

echo -e "\n=== Disk Usage ==="
df -h /opt/domainmgr
```

### 11.2 快速故障排查

| 问题 | 排查步骤 |
|------|---------|
| 502 Bad Gateway | 检查domainmgr服务是否启动、端口8000是否监听 |
| 无法访问Web | 检查Nginx配置、防火墙 |
| 数据库错误 | 检查SQLite文件权限、磁盘空间 |
| 飞书消息失败 | 检查飞书API配置、网络连接 |

---

## 十二、生产环境检查清单

- [ ] CentOS系统已更新到最新
- [ ] Python 3.11+ 已安装
- [ ] 使用独立的system用户（domainmgr）
- [ ] 独立的虚拟环境
- [ ] SQLite数据库文件权限正确（0600）
- [ ] .env文件权限正确（0700）
- [ ] Systemd服务已配置并开机启动
- [ ] Nginx反向代理配置正确
- [ ] 独立的域名或路径配置
- [ ] SSL证书已配置
- [ ] 日志轮转已设置
- [ ] 自动备份脚本已配置
- [ ] 防火墙规则已配置
- [ ] Fail2Ban已启用
- [ ] 已完成全流程测试（注册、解析、审批）

