# 域名管家

企业级域名管理系统，提供域名注册、DNS解析、到期提醒等功能，与飞书深度集成。

## ✨ 已完成功能

### 🔐 安全与认证
- ✅ 飞书OAuth扫码登录
- ✅ JWT令牌认证
- ✅ 多角色权限控制（业务同事/域名专员/管理员/超级管理员）
- ✅ 敏感数据加密存储
- ✅ 完整的审计日志系统

### 📋 核心功能
- ✅ 域名管理 - 增删改查、状态跟踪
- ✅ DNS解析管理 - A/AAAA/CNAME/MX/TXT/SRV/NS记录
- ✅ 审批流程 - 提交、审批、拒绝、执行
- ✅ 注册商集成 - Cloudflare、GoDaddy适配器
- ✅ 定时任务 - 域名到期检查、状态同步

### 🎨 用户界面
- ✅ 登录页面（飞书扫码）
- ✅ 仪表盘（统计概览）
- ✅ 域名管理页面
- ✅ 申请管理页面
- ✅ 响应式布局设计

### 🚀 部署
- ✅ Docker容器化部署
- ✅ Docker Compose编排
- ✅ Ubuntu 22.04一键部署脚本
- ✅ Nginx反向代理配置

## 📋 功能特性

- 📋 **域名管理** - 统一管理多平台域名
- 🔄 **DNS解析** - 自动化DNS配置
- ⏰ **到期提醒** - 提前提醒域名续费
- 🤖 **飞书集成** - 机器人对话、审批流程
- 🔐 **权限隔离** - 多角色、多账号权限管理
- 📊 **Web后台** - 域名专员/管理员管理界面
- 📝 **审计日志** - 完整操作记录

## 项目结构

```
domain-manager/
├── backend/                 # Python后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── adapters/       # 外部服务适配
│   │   ├── bot/            # 飞书机器人
│   │   └── core/           # 核心配置
│   ├── data/               # 数据目录
│   └── requirements.txt
│
├── frontend/               # React前端
│   ├── src/
│   │   ├── api/           # API客户端
│   │   ├── pages/         # 页面组件
│   │   └── components/    # 通用组件
│   └── package.json
│
├── scripts/                # 工具脚本
├── nginx/                  # Nginx配置
├── docker-compose.yml      # Docker编排
├── deploy.sh               # 部署入口脚本
└── docs/                   # 文档
```

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### Docker部署（推荐）

**Ubuntu 22.04 LTS 一键部署：**

```bash
# 下载并运行部署脚本
curl -fsSL https://raw.githubusercontent.com/953641016/domain-manager/main/scripts/ubuntu-deploy.sh | bash
```

**手动部署：**

```bash
# 1. 克隆项目
git clone https://github.com/953641016/domain-manager.git
cd domain-manager

# 2. 配置环境变量
cp backend/.env.example backend/.env
nano backend/.env  # 编辑配置

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# 前端: http://localhost
# API: http://localhost/api
```

### 传统部署

如果没有Docker环境，可参考 [服务器部署与运维手册](docs/服务器部署维护文档.md)

## 文档

详细文档请查看 [docs/](docs/) 目录：

| 文档 | 说明 |
|------|------|
| [服务器部署与运维手册](docs/服务器部署维护文档.md) | 部署、SSH、SSL、故障排查（权威） |
| [飞书运维手册](docs/feishu-ops-manual.md) | 飞书平台配置、Webhook、审批流（权威） |
| [安全配置指南](docs/SECURITY_GUIDE.md) | 角色权限、加固步骤、安全检查清单 |
| [注册商配置指南](docs/REGISTRAR_CONFIG_GUIDE.md) | Cloudflare/GoDaddy API Key 获取步骤 |
| [权限与流程设计](docs/权限与流程设计.md) | 审批流、通知设计（权威参考） |
| [技术架构文档](docs/arch.md) | 系统架构概览 |
| [产品需求文档](docs/prd.md) | 产品功能定义 |

## 用户角色

| 角色 | 层级 | 功能 | Web访问 |
|------|------|------|--------|
| 业务同事 (business) | 0 | 通过飞书提交申请 | ❌ |
| 域名专员 (domain_spec) | 1 | 审批、注册、续费、DNS管理 | ✅ |
| 系统管理员 (admin) | 2 | 配置管理、用户管理 | ✅ |
| 超级管理员 (super_admin) | 3 | 全部权限 + 关键操作飞书确认 | ✅ |

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite
- **ORM**: SQLAlchemy
- **异步**: Uvicorn

### 前端
- **框架**: React 18
- **语言**: TypeScript
- **构建**: Vite
- **样式**: Tailwind CSS

### 部署
- **Web服务器**: Nginx（反向代理）
- **容器化**: Docker Compose（3 容器：backend / frontend / nginx）

## 支持的注册商

| 注册商 | 域名注册 | DNS 解析 |
|--------|---------|---------|
| Cloudflare | ✅ | ✅（推荐首选） |
| GoDaddy | ✅ | 单独配置 |

## 开发

### 后端开发
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端开发
```bash
cd frontend
npm install
npm run dev
```

## 用户管理

使用内置的用户管理脚本：

```bash
cd backend
python scripts/manage_users.py add --userid "ou_xxx" --name "张三" --role domain_spec
python scripts/manage_users.py list
```

详细说明请查看 [安全配置指南](docs/SECURITY_GUIDE.md)

## 许可证

MIT License
