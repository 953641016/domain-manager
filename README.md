# 域名管家

企业级域名管理系统，提供域名注册、DNS解析、到期提醒等功能，与飞书深度集成。

## 功能特性

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
├── scripts/                # 部署脚本
├── nginx/                  # Nginx配置
├── systemd/                # Systemd服务
└── docs/                   # 文档
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Nginx 1.20+

### 部署

1. **克隆项目**
   ```bash
   git clone <repo-url>
   cd domain-manager
   ```

2. **初始化部署**
   ```bash
   ./scripts/deploy.sh
   ```

3. **配置环境变量**
   ```bash
   cd backend
   cp .env.example .env
   # 编辑 .env 配置文件
   ```

4. **配置Nginx**
   ```bash
   sudo cp nginx/domainmanager.conf /etc/nginx/conf.d/
   sudo nginx -t && sudo nginx -s reload
   ```

5. **配置Systemd服务**
   ```bash
   sudo cp systemd/domainmanager.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable domainmanager
   sudo systemctl start domainmanager
   ```

## 文档

详细文档请查看 [docs/](docs/) 目录：

- [产品需求文档](docs/prd.md)
- [技术架构文档](docs/arch.md)
- [部署文档](docs/deployment.md)
- [飞书权限配置](docs/feishu-permission-config.md)
- [项目结构说明](docs/PROJECT_STRUCTURE.md)

## 用户角色

| 角色 | 功能 | Web访问 |
|------|------|--------|
| 业务同事 | 提交申请 | ❌ |
| 域名专员 | 审批、注册、续费 | ✅ |
| 系统管理员 | 配置管理、用户管理 | ✅ |

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
- **Web服务器**: Nginx
- **进程管理**: Systemd + Gunicorn

## 支持的注册商

- Cloudflare
- GoDaddy
- Namecheap
- Enom

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

详细说明请查看 [docs/feishu-permission-config.md](docs/feishu-permission-config.md)

## 许可证

MIT License
