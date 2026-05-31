# 域名管家 - 工程和安全审查报告

> **审查日期：** 2026-05-30
> **审查范围：** 全项目工程架构、安全机制、代码实现
> **状态：** 🔴 有严重安全问题，需立即修复

---

## 1. 工程结构审查

### 1.1 目录架构评分：⭐⭐⭐⭐☆

**优点：**
- ✅ 前后端分离架构清晰
- ✅ 分层设计（API/Service/Model/Schema）
- ✅ 配置集中管理
- ✅ 有文档和部署脚本

**可改进：**
- ⚠️ 缺少集成测试目录
- ⚠️ 缺少 Docker 相关配置
- ⚠️ 缺少 CI/CD 配置

**建议的完整架构：**
```
domain-manager/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── adapters/
│   │   ├── bot/
│   │   └── core/
│   ├── tests/
│   │   ├── unit/          # 单元测试
│   │   ├── integration/    # 集成测试
│   │   └── e2e/           # 端到端测试
│   ├── scripts/
│   ├── alembic/
│   └── data/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   └── tests/
├── docs/
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
└── .gitignore
```

### 1.2 代码组织评分：⭐⭐⭐☆☆

**已实现的模块：**
| 模块 | 状态 | 说明 |
|------|------|------|
| 用户管理 API | ✅ 已实现 | 用户 CRUD，无认证 |
| 用户确认 API | ✅ 已实现 | 基础框架 |
| 飞书集成 API | ✅ 骨架 | 待完善 |
| 用户模型 | ✅ 已实现 | 完整字段 |
| 权限定义 | ✅ 已定义 | 未使用 |
| 数据库连接 | ✅ 已实现 | SQLite |
| 配置管理 | ✅ 已实现 | 基础功能 |

**未实现的核心模块：**
| 模块 | 状态 | 优先级 |
|------|------|--------|
| 认证机制 | ❌ 未实现 | 🔴 高 |
| 权限装饰器 | ❌ 未实现 | 🔴 高 |
| 域名管理 | ❌ 未实现 | 🟡 中 |
| DNS解析管理 | ❌ 未实现 | 🟡 中 |
| 审批流程 | ❌ 未实现 | 🟡 中 |
| 飞书机器人 | ❌ 未实现 | 🟡 中 |
| 审计日志 | ❌ 未实现 | 🟡 中 |
| 加密服务 | ❌ 未实现 | 🔴 高 |
| 速率限制 | ❌ 未实现 | 🟡 中 |

**可改进：**
- ⚠️ 缺少依赖注入容器
- ⚠️ 缺少中间件设计
- ⚠️ 缺少异常统一处理

**建议：**
1. 添加异常处理器 `app/middleware/exception_handler.py`
2. 添加统一响应格式 `app/schemas/response.py`
3. 添加限流中间件 `slowapi`

---

## 2. 安全设计审查

### 2.1 整体安全架构评分：⭐☆☆☆☆ (1/5)

#### 2.1.1 身份认证（🔴 严重问题）

**当前状态：**
- ❌ **认证机制完全未实现**
- ❌ `get_current_user()` 是占位符
- ❌ 所有 API 公开访问，无任何认证
- ⚠️ 缺少双因素认证（2FA）
- ⚠️ 缺少密码策略（复杂要求/过期）

**实际代码问题：**
```python
# backend/app/api/dependencies.py
async def get_current_user():
    """
    获取当前登录用户（待实现）
    """
    pass  # ❌ 完全未实现！
```

**安全风险：**
- 🔴 任何人都可以创建/修改/删除用户
- 🔴 任何人都可以访问所有管理接口
- 🔴 如果部署到公网，立即被攻击

**建议改进：**
```python
# JWT 安全建议
ALGORITHM = "HS256"  # 建议使用 "RS256" 非对称加密更安全
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 合理时长
REFRESH_TOKEN_ENABLE = True  # 添加刷新令牌机制
```

#### 2.1.2 权限控制（🔴 严重问题）

**当前状态：**
- ✅ 设计了四层角色权限体系
- ✅ 关键操作需要飞书确认
- ✅ 超级管理员唯一
- ❌ **后端 API 完全没有权限检查**
- ❌ 前端路由守卫未实现

**安全风险：**
```
当前 API 直接暴露，无任何保护：
GET /api/v1/users → 任何人可获取所有用户
POST /api/v1/users → 任何人可创建用户
PUT /api/v1/users/{id} → 任何人可修改用户
DELETE /api/v1/users/{id} → 任何人可删除用户
```

**必须实现的安全机制：**
```python
from fastapi import Depends, HTTPException, status
from app.models.permission import ROLE_PERMISSIONS
from app.core.database import get_db
from sqlalchemy.orm import Session

def require_role(role: str):
    """角色权限装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_permission(permission: str):
    """细粒度权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            role_perms = ROLE_PERMISSIONS.get(current_user.role, {})
            if not role_perms.get(permission, False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# 使用示例
@router.get("/config/accounts")
@require_permission("can_config_accounts")
def get_registrar_accounts():
    ...
```

#### 2.1.3 CORS配置（🔴 严重问题）

**当前状态：**
- ❌ **CORS 配置完全开放**
- ❌ `allow_origins=["*"]` 在生产环境绝对不能用

**实际代码问题：**
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ 严重安全问题！
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**安全风险：**
- 🔴 任何恶意网站都可以发起跨域请求
- 🔴 容易受到 CSRF/XSS 攻击

#### 2.1.4 数据安全（🟡 中等风险）

**当前状态：**
- ⚠️ 数据库明文存储 API Key
- ⚠️ 没有数据加密方案
- ⚠️ 缺少数据脱敏（日志/返回）
- ⚠️ 没有数据库连接加密

**必须修复：**
```python
# 使用 Fernet 加密存储敏感数据
from cryptography.fernet import Fernet
import os

# 生成密钥（首次运行生成并保存到安全位置）
def generate_key():
    return Fernet.generate_key()

class EncryptionService:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return self.fernet.decrypt(ciphertext.encode()).decode()

# 环境变量配置（不要提交到代码仓库）
# .env
ENCRYPTION_KEY=your_fernet_key_here
```

#### 2.1.5 审计和日志（🟡 中等风险）

**当前状态：**
- ✅ 设计了审计日志表
- ❌ 完全未实现
- ⚠️ 缺少敏感操作审计记录
- ⚠️ 缺少日志轮滚和清理
- ⚠️ 没有日志审计告警

### 2.2 特定安全检查清单

| 检查项 | 状态 | 风险等级 | 建议 |
|--------|------|---------|------|
| 1. API 认证机制 | 🔴 未实现 | 高 | 立即实现 JWT/OAuth 认证 |
| 2. API 权限检查 | 🔴 未实现 | 高 | 为所有管理接口添加权限装饰器 |
| 3. CORS 配置 | 🔴 不安全 | 高 | 限制 origin 为前端域名 |
| 4. 速率限制 | ❌ 未实现 | 中 | 集成 slowapi |
| 5. 敏感数据加密 | 🟡 未实现 | 高 | 实现 Fernet 加密 |
| 6. 密钥安全存储 | 🟡 需改进 | 高 | 使用环境变量 + 密钥管理服务 |
| 7. 飞书消息验证 | ❌ 未实现 | 高 | 验证签名防止伪造 |
| 8. 数据库备份加密 | ❌ 未实现 | 中 | 备份文件加密 |
| 9. TLS/HTTPS 强制 | ❌ 未实现 | 高 | 强制 HTTPS + HSTS |
| 10. 审计日志 | ❌ 未实现 | 中 | 完善审计记录 |
| 11. SQL 注入防护 | ✅ 安全 | 低 | 使用 SQLAlchemy 参数化查询 |
| 12. XSS 攻击防护 | 🟡 需改进 | 中 | 前端输入验证 + 后端输出转义 |

---

## 3. 关键安全修复优先级

### 🔴 高优先级（必须立即修复）

1. **修复 CORS 配置**
   - 限制 allow_origins 为前端域名
   - 开发环境可配置多个域名

2. **实现 JWT 认证**
   - 实现 `get_current_user()`
   - 飞书 OAuth 集成

3. **后端 API 权限装饰器**
   - 所有管理 API 必须加权限检查
   - 防止越权访问

4. **敏感数据加密**
   - API Key 加密存储
   - 配置文件密钥管理

### 🟡 中优先级（近期修复）

1. **速率限制**
   - 防止暴力攻击
   - API 防刷

2. **飞书机器人签名验证**
   - 验证飞书请求来源
   - 防止伪造请求

3. **审计日志完整实现**
   - 记录所有关键操作
   - 日志告警

### 🟢 低优先级（持续改进）

1. Docker 安全加固
2. 网络隔离（安全组/VPC）
3. 安全编码规范
4. 安全扫描自动化

---

## 4. 域名配置方案

### 4.1 域名规划

根据项目需求，规划以下域名：

| 用途 | 域名示例 | 说明 |
|------|---------|------|
| Web 管理后台 | `domainmgr.yourcompany.com` | 前端 Web 界面 |
| API 接口 | `api.domainmgr.yourcompany.com` | 后端 API 服务 |
| 飞书回调 | `api.domainmgr.yourcompany.com` | 飞书 OAuth 回调 |
| 健康检查 | `api.domainmgr.yourcompany.com/health` | 负载均衡健康检查 |

**本地开发环境：**
| 用途 | 地址 |
|------|------|
| 前端 | `http://localhost:3000` |
| 后端 | `http://localhost:8000` |

### 4.2 Nginx 配置示例

```nginx
# nginx/domainmanager.conf
server {
    listen 80;
    server_name domainmgr.yourcompany.com;
    
    # 强制跳转 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    
    server_name domainmgr.yourcompany.com;
    
    # SSL 证书配置
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 安全响应头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 前端静态文件
    location / {
        alias /opt/domainmanager/frontend/dist/;
        try_files $uri $uri/ /index.html;
    }
    
    # API 转发
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4.3 环境变量配置

更新 `.env` 文件添加域名配置：

```env
# 域名配置
FRONTEND_DOMAIN=domainmgr.yourcompany.com
BACKEND_DOMAIN=api.domainmgr.yourcompany.com
ALLOWED_ORIGINS=https://domainmgr.yourcompany.com,http://localhost:3000
```

### 4.4 CORS 配置修复

根据环境变量动态配置 CORS：

```python
# backend/app/main.py
import os
from dotenv import load_dotenv

load_dotenv()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 5. 部署安全建议

### 5.1 环境隔离

```
生产环境：
- 独立服务器/VPC
- 数据库独立
- 定期安全扫描
- 日志集中管理
```

### 5.2 最小权限原则

```
服务账户：
- domainmgr 用户仅项目目录权限
- 不允许 sudo
- 不运行 root
```

### 5.3 网络安全

```
Nginx 配置：
- 强制 HTTPS
- TLS 1.2+
- HSTS 启用
- 安全响应头
```

### 5.4 备份和恢复

```
每日备份策略：
1. 数据库增量备份
2. 加密存储备份
3. 异地备份
4. 定期恢复演练
```

---

## 6. 安全开发规范

### 6.1 代码审查清单

- [ ] 所有用户输入已验证
- [ ] SQL 查询参数化
- [ ] 敏感数据已加密
- [ ] 权限检查已实现
- [ ] 审计日志已记录
- [ ] 错误不泄露敏感信息

### 6.2 依赖安全扫描

```bash
# 后端依赖检查
pip install safety
safety check

# 前端依赖检查
npm audit
```

---

## 7. 总结和建议

### 总体安全评级：⭐☆☆☆☆ (1/5)

### 关键改进点：

1. **立即修复（今天）：**
   - ✅ 修复 CORS 配置（已在计划中）
   - 实现 JWT 认证框架
   - 为用户管理 API 添加权限检查

2. **近期完成（本周）：**
   - 完整的 JWT 认证
   - 速率限制
   - 审计日志基础

3. **长期建设（本月）：**
   - Docker 容器化
   - CI/CD 集成安全扫描
   - 定期渗透测试
   - 安全事件响应流程

### 安全文档：

建议维护以下文档：
- 安全架构文档
- 安全事件响应流程
- 数据分类和处理规范
- 安全培训材料

---

## 4. 部署安全建议

### 4.1 环境隔离

```
生产环境：
- 独立服务器/VPC
- 数据库独立
- 定期安全扫描
- 日志集中管理
```

### 4.2 最小权限原则

```
服务账户：
- domainmgr 用户仅项目目录权限
- 不允许 sudo
- 不运行 root
```

### 4.3 网络安全

```
Nginx 配置：
- 强制 HTTPS
- TLS 1.2+
- HSTS 启用
- 安全响应头
```

### 4.4 备份和恢复

```
每日备份策略：
1. 数据库增量备份
2. 加密存储备份
3. 异地备份
4. 定期恢复演练
```

---

## 5. 安全开发规范

### 5.1 代码审查清单

- [ ] 所有用户输入已验证
- [ ] SQL 查询参数化
- [ ] 敏感数据已加密
- [ ] 权限检查已实现
- [ ] 审计日志已记录
- [ ] 错误不泄露敏感信息

### 5.2 依赖安全扫描

```bash
# 后端依赖检查
pip install safety
safety check

# 前端依赖检查
npm audit
```

---

## 6. 总结和建议

### 总体安全评级：⭐⭐☆☆☆ (2/5)

### 关键改进点：

1. **立即修复（本周）：**
   - API Key 加密
   - 后端权限装饰器
   - 飞书签名验证

2. **近期完成（本月）：**
   - JWT 完整实现
   - 速率限制
   - 审计日志

3. **长期建设（本季度）：**
   - Docker 容器化
   - CI/CD 集成安全扫描
   - 定期渗透测试
   - 安全事件响应流程

### 安全文档：

建议维护以下文档：
- 安全架构文档
- 安全事件响应流程
- 数据分类和处理规范
- 安全培训材料
