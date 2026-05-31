> ⚠️ **[ARCHIVED]** 本文档为初始搭建存档，当前部署已按此方案完成，无需再参考。  
> 当前运维操作请查阅：[服务器部署维护文档.md](服务器部署维护文档.md)

# 域名管家 - 二级目录部署方案（存档）

## 一、部署架构说明

### 1.1 二级目录部署架构

```
                           ┌─────────────────┐
                           │   外部访问        │
                           │  yourcompany.com │
                           └────────┬────────┘
                                    │
                                    ▼
                   ┌───────────────────────────────┐
                   │   Nginx (端口 80/443)          │
                   │                                │
                   │   /domainmgr/*  ──────────────┼──→ 域名管家
                   │   (反向代理 localhost:8000)      │
                   │                                │
                   │   /*.php          ─────────────┼──→ PHP项目1
                   │   (PHP-FPM)                    │
                   │                                │
                   │   /phpapp/*      ──────────────┼──→ PHP项目2
                   │   (PHP-FPM)                    │
                   └───────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌───────────────┐    ┌───────────────┐
│   域名管家      │    │   PHP-FPM 1   │    │   PHP-FPM 2   │
│  用户: domainmgr│    │   用户: www   │    │   用户: www   │
│  端口: 8000     │    │   端口: 9000  │    │   端口: 9001  │
└─────────────────┘    └───────────────┘    └───────────────┘
```

### 1.2 访问路径说明

| 应用 | 访问URL | 说明 |
|------|---------|------|
| 域名管家前端 | `https://yourcompany.com/domainmgr/` | Web管理后台 |
| 域名管家API | `https://yourcompany.com/domainmgr/api/` | 后端API接口 |
| PHP项目1 | `https://yourcompany.com/` | 现有PHP项目 |
| PHP项目2 | `https://yourcompany.com/phpapp/` | 其他PHP应用 |

---

## 二、Nginx配置（二级目录模式）

### 2.1 完整Nginx配置

```nginx
# /etc/nginx/conf.d/domainmgr.conf

server {
    listen 80;
    listen [::]:80;
    server_name yourcompany.com;
    
    # 访问日志
    access_log /var/log/nginx/domainmgr_access.log;
    error_log /var/log/nginx/domainmgr_error.log;
    
    # ========================================
    # 域名管家 - 二级目录部署
    # ========================================
    location ^~ /domainmgr/ {
        # 静态文件根目录
        alias /opt/domainmgr/domainmgr/frontend/dist/;
        
        # 首页
        index index.html;
        try_files $uri $uri/ /domainmgr/index.html;
        
        # 静态资源缓存（1年）
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }
    }
    
    # 域名管家API反向代理
    location ^~ /domainmgr/api/ {
        rewrite ^/domainmgr/(.*) /$1 break;
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
        
        # 请求体大小限制
        client_max_body_size 10M;
    }
    
    # ========================================
    # robots.txt - 允许爬虫访问首页，禁止访问敏感路径
    # ========================================
    location = /domainmgr/robots.txt {
        alias /opt/domainmgr/domainmgr/frontend/dist/robots.txt;
        add_header Content-Type text/plain;
    }
    
    # ========================================
    # PHP项目配置（示例，不修改）
    # ========================================
    location / {
        # 尝试静态文件
        try_files $uri $uri/ /index.php?$query_string;
    }
    
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php-fpm/www.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi.conf;
    }
}
```

### 2.2 配置说明

#### 路径重写规则

| 原始URL | 重写后URL | 说明 |
|---------|-----------|------|
| `/domainmgr/api/domains` | `/api/domains` | API路径重写 |
| `/domainmgr/` | `/index.html` | 前端路由支持 |

#### location 匹配优先级

```nginx
location ^~ /domainmgr/      # 优先前缀匹配（最优先）
location = /domainmgr/robots.txt  # 精确匹配
location ~ /domainmgr/.*\.php$    # 正则匹配
```

---

## 三、前端配置

### 3.1 环境变量配置

```env
# /opt/domainmgr/domainmgr/frontend/.env.production

# 关键：必须设置为二级目录路径
VITE_BASE_PATH=/domainmgr

# API 路径（留空使用相对路径）
VITE_API_BASE_URL=

# 应用信息
VITE_APP_TITLE=域名管家
VITE_APP_DESCRIPTION=企业级域名管理系统
```

### 3.2 Vite构建配置

```typescript
// vite.config.ts
export default defineConfig({
  // 二级目录部署必须配置
  base: '/domainmgr/',
  
  build: {
    outDir: 'dist',
    // 部署基础路径
    assetsDir: 'assets',
  },
  
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
```

### 3.3 React Router配置

```typescript
// App.tsx
import { BrowserRouter } from 'react-router-dom';
import { APP_BASE_PATH } from '@/config/routes';

function App() {
  return (
    <BrowserRouter basename={APP_BASE_PATH}>
      {/* 路由配置 */}
    </BrowserRouter>
  );
}
```

### 3.4 构建和部署

```bash
# 1. 安装依赖
cd /opt/domainmgr/domainmgr/frontend
npm install

# 2. 设置环境变量
echo "VITE_BASE_PATH=/domainmgr" > .env.production

# 3. 构建生产版本
npm run build

# 4. 部署到服务器
sudo rsync -avz dist/ domainmgr@yourserver:/opt/domainmgr/domainmgr/frontend/

# 5. 设置权限
sudo chown -R domainmgr:domainmgr /opt/domainmgr/domainmgr/frontend/dist
```

---

## 四、后端配置

### 4.1 CORS配置（支持二级目录）

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS配置 - 支持二级目录部署
origins = [
    "https://yourcompany.com",
    "http://yourcompany.com",
    "https://yourcompany.com/domainmgr",  # 二级目录
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.2 静态文件配置

```python
# main.py
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 挂载静态文件（可选，通常由Nginx处理）
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/robots.txt")
async def robots_txt():
    return FileResponse("/opt/domainmgr/domainmgr/frontend/dist/robots.txt")
```

### 4.3 API路由前缀

```python
# routers/domains.py
from fastapi import APIRouter

# API路由会自动加上 /api 前缀
router = APIRouter(prefix="/api/domains", tags=["域名管理"])

@router.get("/")
async def list_domains():
    """获取域名列表"""
    pass
```

---

## 五、robots.txt配置

### 5.1 robots.txt内容

```txt
# /opt/domainmgr/domainmgr/frontend/dist/robots.txt

User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /manage/
Disallow: /config/
Disallow: /settings/
Disallow: /private/
Disallow: /*.json$
Disallow: /*.xml$

# 允许访问首页和静态资源
Allow: /index.html
Allow: /static/
Allow: /assets/
Allow: /favicon.ico

# Sitemap
Sitemap: https://yourcompany.com/domainmgr/sitemap.xml

# 爬虫访问频率
Crawl-delay: 1

# 禁止恶意爬虫
User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /
```

### 5.2 部署robots.txt

```bash
# 确保 robots.txt 在构建产物中
ls -la /opt/domainmgr/domainmgr/frontend/dist/robots.txt

# 如果没有，手动复制
sudo cp /workspace/frontend/robots.txt /opt/domainmgr/domainmgr/frontend/dist/
sudo chown domainmgr:domainmgr /opt/domainmgr/domainmgr/frontend/dist/robots.txt
```

---

## 六、完整部署检查清单

### 6.1 部署前检查

- [ ] 服务器已安装Python 3.11+
- [ ] Nginx已安装并运行
- [ ] PHP项目正常运行
- [ ] 域名DNS已配置
- [ ] SSL证书已申请（可选）

### 6.2 二级目录配置检查

- [ ] 前端 `.env.production` 中 `VITE_BASE_PATH=/domainmgr`
- [ ] 前端 `vite.config.ts` 中 `base: '/domainmgr/'`
- [ ] React Router 使用 `BrowserRouter` 的 `basename` 配置
- [ ] API客户端使用相对路径或正确的API路径
- [ ] Nginx location 配置 `^~ /domainmgr/`
- [ ] Nginx rewrite 规则正确
- [ ] CORS 配置包含二级目录域名

### 6.3 robots.txt检查

- [ ] robots.txt 存在于构建目录
- [ ] 禁止爬虫访问敏感路径（/api/、/admin/等）
- [ ] 允许爬虫访问首页
- [ ] 配置了 Sitemap 地址

### 6.4 权限检查

- [ ] Nginx用户（www-data）能读取前端静态文件
- [ ] domainmgr用户能读写数据库文件
- [ ] .env 文件权限 600
- [ ] 数据库文件权限 600

### 6.5 功能测试

- [ ] 访问 `https://yourcompany.com/domainmgr/` 正常
- [ ] 登录功能正常
- [ ] API请求正常（`/domainmgr/api/`）
- [ ] 飞书机器人交互正常
- [ ] robots.txt 可访问

### 6.6 SEO和爬虫测试

- [ ] Googlebot 访问测试
- [ ] 百度爬虫访问测试（如适用）
- [ ] robots.txt 规则生效

---

## 七、常见问题

### 7.1 访问404问题

**问题**：访问 `/domainmgr/` 返回404

**解决**：
```bash
# 1. 检查Nginx配置
sudo nginx -t

# 2. 检查静态文件是否存在
ls -la /opt/domainmgr/domainmgr/frontend/dist/index.html

# 3. 检查Nginx日志
sudo tail -f /var/log/nginx/domainmgr_error.log
```

### 7.2 API请求失败

**问题**：前端API请求返回404

**解决**：
```bash
# 1. 检查后端服务是否运行
sudo systemctl status domainmgr

# 2. 检查端口监听
ss -tlnp | grep 8000

# 3. 检查Nginx rewrite规则
# 确保：rewrite ^/domainmgr/(.*) /$1 break;
```

### 7.3 静态资源加载失败

**问题**：CSS、JS文件404

**解决**：
```nginx
# Nginx配置中使用 alias 而非 root
location ^~ /domainmgr/ {
    alias /opt/domainmgr/domainmgr/frontend/dist/;  # 注意尾部斜杠
    # ...
}
```

### 7.4 CORS跨域问题

**问题**：浏览器报CORS错误

**解决**：
```python
# 后端CORS配置
origins = [
    "https://yourcompany.com",
    "https://yourcompany.com/domainmgr",
]
app.add_middleware(CORSMiddleware, allow_origins=origins)
```

---

## 八、性能优化

### 8.1 Nginx缓存配置

```nginx
location ^~ /domainmgr/assets/ {
    alias /opt/domainmgr/domainmgr/frontend/dist/assets/;
    
    # 缓存1年
    expires 1y;
    add_header Cache-Control "public, immutable";
    
    # 启用gzip压缩
    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
}

# 不缓存HTML
location ^~ /domainmgr/ {
    alias /opt/domainmgr/domainmgr/frontend/dist/;
    
    # HTML不缓存
    expires -1;
    add_header Cache-Control "no-store, no-cache, must-revalidate";
}
```

### 8.2 Gzip压缩

```nginx
http {
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml application/xml+rss text/javascript application/vnd.ms-fontobject application/x-font-ttf font/opentype image/svg+xml;
}
```

---

## 九、监控和日志

### 9.1 Nginx日志分析

```bash
# 查看域名管家访问日志
sudo tail -f /var/log/nginx/domainmgr_access.log

# 统计API调用
sudo awk '/\/domainmgr\/api/ {print $7}' /var/log/nginx/domainmgr_access.log | sort | uniq -c | sort -rn

# 错误统计
sudo awk '/domainmgr/ && / 5[0-9][0-9] / {print $7, $9}' /var/log/nginx/domainmgr_access.log | sort | uniq -c
```

### 9.2 应用日志

```bash
# 查看应用日志
sudo journalctl -u domainmgr -f

# 应用错误日志
sudo tail -f /opt/domainmgr/domainmgr/logs/app.log
```

---

## 十、备份和恢复

### 10.1 备份脚本

```bash
#!/bin/bash
# backup.sh - 完整备份脚本

BACKUP_DIR="/opt/domainmgr/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/opt/domainmgr/domainmgr/data/domainmgr.db"
FRONTEND_DIR="/opt/domainmgr/domainmgr/frontend/dist"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 1. 备份数据库
cp $DB_PATH $BACKUP_DIR/domainmgr_$DATE.db

# 2. 备份前端构建
tar -czf $BACKUP_DIR/frontend_$DATE.tar.gz -C /opt/domainmgr/domainmgr frontend/dist

# 3. 备份配置
cp /opt/domainmgr/domainmgr/.env $BACKUP_DIR/env_$DATE

# 4. 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "env_*" -mtime +30 -delete

echo "备份完成: $DATE"
```

### 10.2 恢复脚本

```bash
#!/bin/bash
# restore.sh - 恢复脚本

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: $0 <备份文件路径>"
    exit 1
fi

# 1. 停止服务
sudo systemctl stop domainmgr

# 2. 恢复数据库
cp $BACKUP_FILE /opt/domainmgr/domainmgr/data/domainmgr.db
sudo chown domainmgr:domainmgr /opt/domainmgr/domainmgr/data/domainmgr.db

# 3. 重启服务
sudo systemctl start domainmgr

echo "恢复完成"
```

---

## 十一、安全加固

### 11.1 文件权限

```bash
# 设置严格权限
sudo chown -R domainmgr:domainmgr /opt/domainmgr
sudo chmod 700 /opt/domainmgr/domainmgr/.env
sudo chmod 600 /opt/domainmgr/domainmgr/data/domainmgr.db
sudo chmod 755 /opt/domainmgr/domainmgr/frontend/dist
```

### 11.2 SSL配置

```nginx
# 强制HTTPS
server {
    listen 80;
    server_name yourcompany.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourcompany.com;
    
    ssl_certificate /etc/letsencrypt/live/yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourcompany.com/privkey.pem;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

---

## 十二、升级流程

```bash
#!/bin/bash
# upgrade.sh - 平滑升级脚本

cd /opt/domainmgr/domainmgr

# 1. 拉取最新代码
sudo -u domainmgr git pull origin main

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 数据库迁移（如有）
# alembic upgrade head

# 5. 重新构建前端
cd frontend
npm install
npm run build
cd ..

# 6. 重启服务
sudo systemctl restart domainmgr

# 7. 检查服务状态
sudo systemctl status domainmgr

echo "升级完成"
```

---

这样就完成了完整的二级目录部署方案！包括：

✅ **robots.txt** - 控制搜索引擎爬虫访问
✅ **前端配置** - 支持二级目录部署
✅ **Nginx配置** - 二级目录反向代理
✅ **后端配置** - CORS和API路由
✅ **完整检查清单** - 部署前中后检查
✅ **故障排查指南** - 常见问题解决
✅ **性能优化** - 缓存和压缩配置
✅ **备份恢复** - 完整备份方案

需要我将此内容整合到部署文档中吗？
