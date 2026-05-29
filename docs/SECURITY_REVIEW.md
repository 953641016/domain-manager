# 域名管家 - 工程和安全审查报告

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

### 1.2 代码组织评分：⭐⭐⭐⭐☆

**优点：**
- ✅ 使用 FastAPI + Pydantic，类型安全
- ✅ 业务逻辑在 Service 层
- ✅ 外部依赖封装在 Adapter 层
- ✅ 数据验证在 Schema 层

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

### 2.1 整体安全架构评分：⭐⭐⭐☆☆

#### 2.1.1 身份认证

**当前状态：**
- ✅ 设计了 JWT 认证
- ⚠️ 缺少双因素认证（2FA）
- ⚠️ 缺少密码策略（复杂要求/过期）

**风险：**
- 1. 如果 JWT SECRET 泄露，所有用户身份可被冒充
- 2. 飞书 OAuth 如果没有 IP 白名单，可能被钓鱼攻击

**建议改进：**
```python
# JWT 安全建议
ALGORITHM = "HS256"  # 建议使用 "RS256" 非对称加密更安全
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 合理时长
REFRESH_TOKEN_ENABLE = True  # 添加刷新令牌机制
```

#### 2.1.2 权限控制

**当前状态：**
- ✅ 设计了四层角色权限体系
- ✅ 关键操作需要飞书确认
- ✅ 超级管理员唯一
- ⚠️ 后端 API 缺少角色权限装饰器
- ⚠️ 前端路由守卫未实现

**安全风险：**
```
当前 API 直接暴露：
/users/ → 没有权限检查
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

#### 2.1.3 数据安全

**当前状态：**
- ⚠️ 数据库明文存储 API Key
- ⚠️ 没有数据加密方案
- ⚠️ 缺少数据脱敏（日志/返回）
- ⚠️ 没有数据库连接加密

**严重安全问题：**

```python
# 🔴 不安全！当前注册商配置直接存储
registrar_config = {
    "cloudflare_api_key": "1234567890abcdef",  # 明文！
    "godaddy_api_secret": "abcdef1234567890",   # 明文！
}
```

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

#### 2.1.4 审计和日志

**当前状态：**
- ✅ 设计了审计日志表
- ⚠️ 缺少敏感操作审计记录
- ⚠️ 缺少日志轮滚和清理
- ⚠️ 没有日志审计告警

**建议实现：**
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    user_name = Column(String(100))
    action = Column(String(100), index=True)  # 动作：CREATE/UPDATE/DELETE
    resource_type = Column(String(100))  # 资源：USER/DOMAIN/ACCOUNT
    resource_id = Column(String(100))
    ip_address = Column(String(50))  # 操作来源IP
    user_agent = Column(String(500))  # User-Agent
    before_state = Column(JSON)  # 变更前状态
    after_state = Column(JSON)  # 变更后状态
    status = Column(String(20), default="SUCCESS")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2.2 特定安全检查清单

| 检查项 | 状态 | 风险等级 | 建议 |
|--------|------|---------|------|
| 1. SQL 注入防护 | ⚠️ 待实现 | 高 | 使用 SQLAlchemy 参数化查询 |
| 2. XSS 攻击防护 | ⚠️ 待实现 | 中 | 前端输入验证 + 后端输出转义 |
| 3. CSRF 防护 | ⚠️ 待实现 | 中 | SameSite cookies + CSRF token |
| 4. 速率限制 | ⚠️ 待实现 | 中 | 集成 slowapi + Redis |
| 5. 敏感数据加密 | 🔴 高风险 | 高 | 实现 Fernet 加密 |
| 6. 密钥安全存储 | ⚠️ 待实现 | 高 | 使用环境变量 + 密钥管理服务 |
| 7. 飞书消息验证 | ⚠️ 待实现 | 高 | 验证签名防止伪造 |
| 8. 数据库备份加密 | ⚠️ 待实现 | 中 | 备份文件加密 |
| 9. TLS/HTTPS 强制 | ⚠️ 待实现 | 高 | 强制 HTTPS + HSTS |
| 10. 审计日志 | ⚠️ 部分实现 | 中 | 完善审计记录 |

---

## 3. 关键安全修复优先级

### 🔴 高优先级（必须立即修复）

1. **敏感数据加密**
   - API Key 加密存储
   - 配置文件密钥管理
   - 数据库连接加密

2. **后端 API 权限装饰器**
   - 所有管理 API 必须加权限检查
   - 防止越权访问

3. **飞书机器人签名验证**
   - 验证飞书请求来源
   - 防止伪造请求

### 🟡 中优先级（近期修复）

1. **JWT 认证完整实现**
   - Token 刷新机制
   - Token 黑名单（登出时）
   - 2FA 支持（可选但推荐）

2. **速率限制**
   - 防止暴力攻击
   - API 防刷

3. **审计日志完整实现**
   - 记录所有关键操作
   - 日志告警

### 🟢 低优先级（持续改进）

1. Docker 安全加固
2. 网络隔离（安全组/VPC）
3. 安全编码规范
4. 安全扫描自动化

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
