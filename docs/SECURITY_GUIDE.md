# 域名管家 - 安全配置指南

## 目录
1. [权限体系](#1-权限体系)
2. [超级管理员配置](#2-超级管理员配置)
3. [安全加固步骤](#3-安全加固步骤)
4. [部署安全检查清单](#4-部署安全检查清单)

---

## 1. 权限体系

### 1.1 角色层级

| 角色 | 层级 | Web访问 | 权限 |
|------|------|---------|------|
| 业务同事 (business) | 0 | ❌ | 仅通过飞书提交申请 |
| 域名专员 (domain_spec) | 1 | ✅ | 管理域名、审批申请 |
| 系统管理员 (admin) | 2 | ✅ | 管理用户、系统配置 |
| 超级管理员 (super_admin) | 3 | ✅ | 全部权限、关键操作确认 |

### 1.2 权限矩阵

| 功能 | 业务同事 | 域名专员 | 系统管理员 | 超级管理员 |
|------|---------|---------|-----------|----------|
| 提交域名申请 | ✅ | ✅ | ✅ | ✅ |
| 域名可用性查询 | ❌ | ✅ | ✅ | ✅ |
| 直接注册域名 | ❌ | ✅ | ✅ | ✅ |
| 域名续费 | ❌ | ✅ | ✅ | ✅ |
| DNS解析管理 | ❌ | ✅ | ✅ | ✅ |
| 申请审批 | ❌ | ✅ | ✅ | ✅ |
| 查看用户列表 | ❌ | ❌ | ✅ | ✅ |
| 编辑用户信息 | ❌ | ❌ | ✅ | ✅ |
| **升级为域名专员** | ❌ | ❌ | ❌ | **需超级管理员确认** |
| **升级为系统管理员** | ❌ | ❌ | ❌ | **需超级管理员确认** |
| **配置注册商账号** | ❌ | ❌ | ❌ | **需超级管理员确认** |
| 查看审计日志 | ❌ | ❌ | ✅ | ✅ |

---

## 2. 超级管理员配置

### 2.1 初始化超级管理员

#### 步骤 1: 配置飞书用户 ID

```bash
# 编辑 backend/.env
# 设置超级管理员的飞书用户 ID
SUPER_ADMIN_FEISHU_USERID=ou_your_super_admin_id_here
```

#### 步骤 2: 运行数据库初始化脚本

```bash
cd backend
python scripts/init_db.py
```

**脚本会自动：**
1. 创建所有数据表
2. 创建默认超级管理员用户
3. 设置超级管理员角色权限

#### 步骤 3: 验证超级管理员

```bash
# 使用用户管理脚本验证
cd backend
python scripts/manage_users.py list --role super_admin
```

### 2.2 超级管理员唯一约束

**⚠️ 关键安全设计：**

1. **唯一超级管理员**
   - 系统中同一时间只能有一个 `super_admin`
   - 尝试创建第二个会被拒绝

2. **飞书确认机制**
   - 任何涉及 `super_admin` 的变更
   - 都需要当前超级管理员飞书确认

3. **关键操作确认列表**

| 操作 | 需要确认 | 确认者 |
|------|---------|--------|
| 升级为域名专员 | ✅ | 任意管理员 |
| 升级为系统管理员 | ✅ | 超级管理员 |
| 降级系统管理员 | ✅ | 超级管理员 |
| 配置注册商账号 | ✅ | 超级管理员 |
| 变更超级管理员 | ✅ | 超级管理员 |

---

## 3. 安全加固步骤

### 3.1 敏感数据加密

#### 步骤 1: 生成加密密钥

```bash
cd backend
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 输出类似: gAAAAABk...
```

#### 步骤 2: 配置环境变量

```bash
# 编辑 backend/.env
ENCRYPTION_KEY=your_generated_key_here
```

#### 步骤 3: 使用加密服务

```python
from app.core.encryption import EncryptionService

encryption = EncryptionService(os.getenv("ENCRYPTION_KEY"))

# 加密
encrypted_api_key = encryption.encrypt("real_api_key_12345")

# 解密
plaintext_api_key = encryption.decrypt(encrypted_api_key)
```

### 3.2 后端 API 权限装饰器

```python
# app/middleware/permission.py
from functools import wraps
from fastapi import HTTPException, status, Depends
from app.models.user import User
from app.models.permission import ROLE_PERMISSIONS

def require_role(required_role: str):
    """检查用户角色"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            user_role_level = ROLE_PERMISSIONS.get(current_user.role, {}).get("role_level", 0)
            required_level = ROLE_PERMISSIONS.get(required_role, {}).get("role_level", 999)
            
            if user_role_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_permission(permission_name: str):
    """检查具体权限"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            role_perms = ROLE_PERMISSIONS.get(current_user.role, {})
            if not role_perms.get(permission_name, False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

### 3.3 飞书机器人签名验证

```python
# app/bot/signature.py
import hashlib
import hmac
from fastapi import Request, HTTPException

async def verify_feishu_signature(request: Request):
    """验证飞书请求签名"""
    signature = request.headers.get("X-Lark-Signature")
    timestamp = request.headers.get("X-Lark-Request-Timestamp")
    nonce = request.headers.get("X-Lark-Request-Nonce")
    
    if not all([signature, timestamp, nonce]):
        raise HTTPException(status_code=400, detail="无效请求")
    
    # 验证签名
    body = await request.body()
    expected_signature = calculate_signature(
        os.getenv("FEISHU_ENCRYPT_KEY"),
        timestamp,
        nonce,
        body.decode()
    )
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="签名验证失败")

def calculate_signature(encrypt_key: str, timestamp: str, nonce: str, body: str) -> str:
    string_to_sign = f"{timestamp}{nonce}{body}"
    hmac_obj = hmac.new(encrypt_key.encode(), string_to_sign.encode(), hashlib.sha256)
    return hmac_obj.hexdigest()
```

### 3.4 速率限制

```python
# app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

# 使用示例
@router.post("/users")
@limiter.limit("10/minute")
async def create_user(request: Request):
    ...
```

---

## 4. 部署安全检查清单

### 4.1 部署前检查

- [ ] 所有敏感配置已放入环境变量
- [ ] `.env` 已添加到 `.gitignore`
- [ ] 数据库密码已使用强密码
- [ ] JWT SECRET 已使用随机字符串生成
- [ ] ENCRYPTION_KEY 已生成并安全存储
- [ ] 飞书应用密钥已配置
- [ ] TLS 证书已准备好

### 4.2 Nginx 安全配置

```nginx
# nginx/domainmanager-secure.conf
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    
    server_name yourdomain.com;
    
    # TLS 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 安全响应头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 域名管家配置
    location /domainmgr {
        alias /opt/domainmanager/frontend/dist;
        ...
    }
    
    location /domainmgr/api {
        proxy_pass http://127.0.0.1:8000;
        ...
    }
}

# HTTP 跳转 HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 4.3 Systemd 服务安全配置

```systemd
# systemd/domainmanager-secure.service
[Unit]
Description=Domain Manager
After=network.target

[Service]
Type=notify
User=domainmgr
Group=domainmgr
WorkingDirectory=/opt/domainmanager/backend
Environment="PATH=/opt/domainmanager/backend/venv/bin"
ExecStart=/opt/domainmanager/backend/venv/bin/gunicorn app.main:app ...

# 安全加固
NoNewPrivileges=true
PrivateDevices=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/opt/domainmanager/backend/data /opt/domainmanager/backend/logs
PrivateTmp=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.4 定期安全任务

```
每日：
- 检查系统日志异常
- 检查数据库访问日志
- 备份数据

每周：
- 检查用户权限变更
- 检查审计日志
- 依赖安全扫描 (safety check / npm audit)

每月：
- TLS 证书检查
- 备份恢复演练
- 安全配置复查

每季度：
- 完整渗透测试
- 安全策略评审
- 安全培训
```

---

## 5. 安全事件响应

### 5.1 安全事件处理流程

1. **发现问题**
   - 记录发现时间、现象
   - 保留证据（日志、截图等）

2. **报告上级**
   - 及时通知超级管理员
   - 必要时通知安全团队

3. **控制影响**
   - 暂停可疑服务
   - 撤销泄露的密钥
   - 重置受影响用户

4. **调查原因**
   - 分析日志
   - 找出根本原因
   - 评估影响范围

5. **修复漏洞**
   - 修复安全问题
   - 加强相关防护

6. **总结改进**
   - 编写事件报告
   - 更新安全策略
   - 完善监控机制

### 5.2 紧急联系方式

- 超级管理员：
- 技术负责人：
- 安全团队：

---

## 附录

### A. 完整权限配置文件示例

```python
# app/models/permission.py - 完整权限定义
ROLE_PERMISSIONS = {
    "super_admin": {
        "name": "超级管理员",
        "description": "唯一超级管理员，拥有所有权限",
        "role_level": 3,
        "web_access": True,
        "can_submit_register": True,
        "can_direct_register": True,
        "can_renew": True,
        "can_approve": True,
        "can_config_accounts": True,
        "can_manage_users": True,
        "can_manage_permissions": True,
        ...
    },
    ...
}
```

### B. 数据库备份脚本

```bash
# scripts/backup-secure.sh
#!/bin/bash
BACKUP_DIR="/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
ENCRYPT_PASS=$(openssl rand -base64 32)

# 备份
sqlite3 /data/domainmgr.db ".backup /tmp/domainmgr_backup.db"

# 加密
gpg --yes --batch --passphrase="$ENCRYPT_PASS" -c /tmp/domainmgr_backup.db
mv /tmp/domainmgr_backup.db.gpg $BACKUP_DIR/domainmgr_$DATE.db.gpg

# 保存加密密码到安全位置
echo "Backup $DATE encryption password: $ENCRYPT_PASS" >> $BACKUP_DIR/encryption_keys.txt
chmod 600 $BACKUP_DIR/encryption_keys.txt

# 清理
rm /tmp/domainmgr_backup.db
```
