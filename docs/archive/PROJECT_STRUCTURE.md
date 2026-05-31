# 域名管家 - 项目结构说明

## 项目概述

```
domain-manager/
├── backend/          # Python后端 (FastAPI)
├── frontend/         # React前端
├── scripts/          # 部署和管理脚本
├── docs/             # 文档
└── README.md         # 项目说明
```

---

## 完整目录结构

```
domain-manager/
│
├── backend/                             # Python后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI入口
│   │   │
│   │   ├── api/                        # API路由
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py             # 认证API
│   │   │   │   ├── domains.py          # 域名管理API
│   │   │   │   ├── requests.py         # 申请管理API
│   │   │   │   ├── feishu.py           # 飞书Webhook API
│   │   │   │   ├── config.py           # 配置管理API
│   │   │   │   └── users.py            # 用户管理API
│   │   │   └── dependencies.py         # 依赖注入
│   │   │
│   │   ├── models/                     # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py                 # 用户模型
│   │   │   ├── domain.py               # 域名模型
│   │   │   ├── request.py              # 申请模型
│   │   │   ├── registrar.py            # 注册商/账号模型
│   │   │   ├── audit.py                # 审计日志模型
│   │   │   └── permission.py           # 权限定义
│   │   │
│   │   ├── services/                   # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── domain_service.py       # 域名服务
│   │   │   ├── request_service.py      # 申请服务
│   │   │   ├── feishu_service.py       # 飞书服务
│   │   │   ├── registrar_service.py    # 注册商服务
│   │   │   ├── audit_service.py        # 审计服务
│   │   │   └── notification_service.py # 通知服务
│   │   │
│   │   ├── adapters/                   # 外部服务适配
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # 适配器基类
│   │   │   ├── registrar_factory.py    # 注册商工厂
│   │   │   ├── dns_factory.py          # DNS解析商工厂
│   │   │   ├── cloudflare.py           # Cloudflare适配
│   │   │   ├── godaddy.py              # GoDaddy适配
│   │   │   ├── namecheap.py            # Namecheap适配
│   │   │   └── enom.py                 # Enom适配
│   │   │
│   │   ├── bot/                        # 飞书机器人
│   │   │   ├── __init__.py
│   │   │   ├── bot.py                  # 机器人主类
│   │   │   ├── commands.py             # 命令处理
│   │   │   ├── cards.py                # 交互卡片
│   │   │   ├── permission_checker.py   # 权限检查
│   │   │   └── command_permissions.py  # 命令权限配置
│   │   │
│   │   ├── middlewares/                # 中间件
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                 # 认证中间件
│   │   │   └── logging.py              # 日志中间件
│   │   │
│   │   ├── schemas/                    # Pydantic数据验证
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── domain.py
│   │   │   ├── request.py
│   │   │   └── feishu.py
│   │   │
│   │   ├── core/                       # 核心配置
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # 配置管理
│   │   │   ├── security.py             # 安全工具
│   │   │   └── database.py             # 数据库连接
│   │   │
│   │   └── tasks/                      # 定时任务
│   │       ├── __init__.py
│   │       ├── scheduler.py            # 调度器
│   │       └── expiration_checker.py   # 到期检查
│   │
│   ├── tests/                          # 测试
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api/
│   │   ├── test_services/
│   │   └── test_adapters/
│   │
│   ├── scripts/                        # 管理脚本
│   │   ├── __init__.py
│   │   └── manage_users.py             # 用户管理脚本
│   │
│   ├── data/                           # 数据目录
│   │   ├── domainmgr.db                # SQLite数据库
│   │   └── backups/                    # 数据库备份
│   │
│   ├── logs/                           # 日志目录
│   │   ├── app.log
│   │   ├── access.log
│   │   └── error.log
│   │
│   ├── alembic/                        # 数据库迁移
│   │   ├── versions/
│   │   ├── env.py
│   │   └── script.py.mako
│   │
│   ├── requirements.txt                # Python依赖
│   ├── .env.example                    # 环境变量示例
│   ├── .env                            # 环境变量（不提交到Git）
│   └── pyproject.toml                  # 项目配置
│
├── frontend/                           # React前端
│   ├── public/
│   │   ├── index.html
│   │   ├── robots.txt
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── main.tsx                    # 入口
│   │   ├── App.tsx                     # 根组件
│   │   ├── vite-env.d.ts
│   │   │
│   │   ├── api/                        # API客户端
│   │   │   ├── client.ts               # Axios配置
│   │   │   ├── domains.ts              # 域名API
│   │   │   ├── requests.ts             # 申请API
│   │   │   ├── auth.ts                 # 认证API
│   │   │   └── config.ts               # 配置API
│   │   │
│   │   ├── components/                 # 通用组件
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Footer.tsx
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── Table.tsx
│   │   │   │   └── Modal.tsx
│   │   │   └── auth/
│   │   │       └── LoginForm.tsx
│   │   │
│   │   ├── pages/                      # 页面组件
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── domains/
│   │   │   │   ├── DomainList.tsx
│   │   │   │   └── DomainDetail.tsx
│   │   │   ├── requests/
│   │   │   │   ├── RequestList.tsx
│   │   │   │   └── RequestDetail.tsx
│   │   │   ├── expiration/
│   │   │   │   └── ExpirationList.tsx
│   │   │   ├── config/
│   │   │   │   ├── RegistrarList.tsx
│   │   │   │   ├── DnsList.tsx
│   │   │   │   └── UserList.tsx
│   │   │   ├── audit/
│   │   │   │   └── AuditLog.tsx
│   │   │   └── errors/
│   │   │       ├── Forbidden.tsx
│   │   │       └── NotFound.tsx
│   │   │
│   │   ├── router/                     # 路由配置
│   │   │   ├── index.tsx
│   │   │   └── protected.tsx
│   │   │
│   │   ├── stores/                     # 状态管理
│   │   │   ├── useAuthStore.ts
│   │   │   └── useDomainStore.ts
│   │   │
│   │   ├── types/                      # TypeScript类型
│   │   │   ├── user.ts
│   │   │   ├── domain.ts
│   │   │   └── request.ts
│   │   │
│   │   ├── config/                     # 配置
│   │   │   └── routes.ts
│   │   │
│   │   ├── utils/                      # 工具函数
│   │   │   ├── request.ts
│   │   │   ├── format.ts
│   │   │   └── permission.ts
│   │   │
│   │   └── styles/                     # 样式
│   │       ├── index.css
│   │       └── tailwind.css
│   │
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── .env.production
│
├── scripts/                            # 部署和管理脚本
│   ├── deploy.sh                       # 部署脚本
│   ├── backup.sh                       # 备份脚本
│   ├── restore.sh                      # 恢复脚本
│   ├── init_db.py                      # 初始化数据库
│   └── start_service.sh                # 启动服务
│
├── docs/                               # 文档
│   ├── prd.md                          # 产品需求文档
│   ├── arch.md                         # 技术架构文档
│   ├── deployment.md                   # 部署文档
│   ├── feishu-permission-config.md     # 飞书权限配置
│   └── subdirectory-deployment.md      # 二级目录部署
│
├── nginx/                              # Nginx配置
│   ├── nginx.conf                      # 主配置
│   └── conf.d/
│       └── domainmanager.conf          # 域名管家配置
│
├── systemd/                            # Systemd服务
│   └── domainmanager.service
│
├── .gitignore
├── README.md
└── LICENSE
```

---

## 目录说明

### Backend 目录

#### `/backend/app/api/` - API路由
```
api/
├── v1/
│   ├── auth.py          # 登录/登出
│   ├── domains.py       # 域名CRUD
│   ├── requests.py      # 申请管理
│   ├── feishu.py        # 飞书Webhook
│   ├── config.py        # 配置管理
│   └── users.py         # 用户管理
└── dependencies.py      # 依赖注入 (获取当前用户等)
```

#### `/backend/app/models/` - 数据模型
```
models/
├── user.py             # 用户表
├── domain.py           # 域名表
├── request.py          # 申请表
├── registrar.py        # 注册商/账号表
├── audit.py            # 审计日志表
└── permission.py       # 权限定义
```

#### `/backend/app/services/` - 业务逻辑层
```
services/
├── domain_service.py       # 域名注册、续费、查询
├── request_service.py      # 申请提交、审批
├── feishu_service.py       # 飞书消息、卡片
├── registrar_service.py    # 注册商操作封装
├── audit_service.py        # 审计记录
└── notification_service.py # 通知发送
```

#### `/backend/app/adapters/` - 外部服务适配
```
adapters/
├── base.py                 # 适配器基类
├── registrar_factory.py    # 注册商工厂
├── dns_factory.py          # DNS工厂
├── cloudflare.py           # Cloudflare实现
├── godaddy.py              # GoDaddy实现
├── namecheap.py            # Namecheap实现
└── enom.py                 # Enom实现
```

#### `/backend/app/bot/` - 飞书机器人
```
bot/
├── bot.py                  # 机器人主类
├── commands.py             # 命令处理函数
├── cards.py                # 飞书卡片模板
├── permission_checker.py   # 权限检查装饰器
└── command_permissions.py  # 命令权限配置
```

### Frontend 目录

#### `/frontend/src/pages/` - 页面组件
```
pages/
├── Login.tsx
├── Dashboard.tsx
├── domains/
│   ├── DomainList.tsx
│   └── DomainDetail.tsx
├── requests/
│   ├── RequestList.tsx
│   └── RequestDetail.tsx
├── expiration/
│   └── ExpirationList.tsx
├── config/
│   ├── RegistrarList.tsx
│   ├── DnsList.tsx
│   └── UserList.tsx
└── audit/
    └── AuditLog.tsx
```

---

## 关键文件

### 后端入口文件

#### `/backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1 import auth, domains, requests, feishu, config, users

app = FastAPI(title="域名管家 API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(domains.router, prefix="/api/v1/domains", tags=["域名"])
app.include_router(requests.router, prefix="/api/v1/requests", tags=["申请"])
app.include_router(feishu.router, prefix="/api/v1/feishu", tags=["飞书"])
app.include_router(config.router, prefix="/api/v1/config", tags=["配置"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])

@app.get("/")
async def root():
    return {"message": "域名管家 API"}
```

### 前端入口文件

#### `/frontend/src/main.tsx`
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

---

## 开发工作流

```
开发流程：
1. 后端开发：
   - 在 models/ 定义数据模型
   - 在 services/ 实现业务逻辑
   - 在 adapters/ 实现外部服务集成
   - 在 api/ 定义API接口
   - 在 bot/ 实现飞书机器人命令

2. 前端开发：
   - 在 types/ 定义类型
   - 在 api/ 定义API调用
   - 在 pages/ 实现页面
   - 在 components/ 实现通用组件

3. 部署：
   - 运行 scripts/deploy.sh
   - 更新 nginx/ 配置
   - 使用 systemd/ 服务管理
```

---

## Git 忽略规则

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment variables
.env

# Database
*.db
*.sqlite

# Logs
*.log
logs/

# Frontend
node_modules/
dist/
.DS_Store

# Backups
backups/
```
