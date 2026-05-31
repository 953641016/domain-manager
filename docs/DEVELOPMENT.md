# 域名管家 — 本地开发环境搭建

> **版本**：v1.0  
> **更新日期**：2026-05-31

---

## 1. 前提条件

| 工具 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.11+ | 后端运行时 |
| Node.js | 20.x | 前端构建 |
| Git | 2.x | 版本控制 |

**本机工具链（当前项目）：**
- Python 3.11：系统 Python 或 pyenv
- Node.js（便携版）：`C:\Users\张健\.toolchain\node-v20.18.1-win-x64`
  - 使用前在 PowerShell 中临时加入 PATH：
    ```powershell
    $env:Path = "C:\Users\张健\.toolchain\node-v20.18.1-win-x64;$env:Path"
    ```

---

## 2. 克隆与初始化

```bash
git clone https://github.com/953641016/domain-manager.git
cd domain-manager
```

---

## 3. 后端开发

### 3.1 创建虚拟环境

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3.2 安装依赖

```bash
pip install -r requirements.txt
```

### 3.3 配置环境变量

```bash
cp .env.example .env
```

编辑 `backend/.env`，**至少配置以下项**：

```ini
# 飞书应用（开发阶段可用测试应用）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 超级管理员飞书 User ID（ou_xxx 格式）
SUPER_ADMIN_FEISHU_USERID=ou_xxxxxxxxxxxxxxxx

# JWT 签名密钥（任意随机字符串）
SECRET_KEY=dev-secret-key-change-in-production

# 敏感数据加密密钥（运行下方命令生成）
ENCRYPTION_KEY=
```

生成 ENCRYPTION_KEY：
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3.4 初始化数据库

```bash
python scripts/init_db.py
```

### 3.5 启动后端

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --port 8000

# 访问地址：http://localhost:8000
# API 文档：http://localhost:8000/docs
```

---

## 4. 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（代理到后端 8000 端口）
npm run dev

# 访问地址：http://localhost:5173
```

### 4.1 环境变量

`frontend/.env.local`（本地开发，不进 git）：

```ini
VITE_API_BASE_URL=http://localhost:8000
```

---

## 5. 常用开发命令

### 后端

```bash
# 查看所有用户
python scripts/manage_users.py list

# 添加域名专员
python scripts/manage_users.py add --userid "ou_xxx" --name "张三" --role domain_spec

# 运行测试（如有）
pytest

# 检查代码风格
flake8 app/
```

### 前端

```bash
# 类型检查
npx tsc --noEmit

# 代码 lint
npm run lint

# 生产构建（测试）
npm run build
```

---

## 6. 代码结构速览

```
backend/
├── app/
│   ├── api/           # FastAPI 路由（按资源分模块）
│   │   ├── auth.py    # 飞书 OAuth 登录
│   │   ├── domains.py
│   │   ├── requests.py
│   │   └── users.py
│   ├── models/        # SQLAlchemy ORM 模型
│   ├── services/      # 业务逻辑（与路由解耦）
│   │   ├── feishu_service.py   # 飞书 API 调用
│   │   ├── request_service.py  # 申请流程
│   │   └── execution_service.py # 域名操作执行
│   ├── adapters/      # 注册商 API 适配器
│   │   ├── base.py
│   │   ├── cloudflare.py
│   │   └── godaddy.py
│   ├── bot/           # 飞书机器人（Webhook 处理）
│   └── core/          # 配置、数据库连接、加密
├── scripts/           # 运维脚本（init_db, manage_users 等）
└── .env               # 环境变量（不进 git）

frontend/
├── src/
│   ├── api/           # Axios 请求封装
│   ├── pages/         # 页面组件
│   └── components/    # 通用 UI 组件
└── .env.local         # 本地环境变量（不进 git）
```

---

## 7. 飞书本地调试

飞书 Webhook 需要公网可访问的 URL。本地调试选项：

**方案 A：ngrok（推荐快速调试）**

```bash
ngrok http 8000
# 将生成的 https://xxxx.ngrok.io 配置到飞书应用 Webhook 地址
```

**方案 B：直接在测试服务器上开发**

```bash
ssh -i /tmp/zj_deploy.pem root@115.28.211.155
cd /opt/domain-manager
# 直接在服务器上改代码，重启容器测试
docker restart domain-manager-backend
```

---

## 8. 提交规范

```bash
# 格式：<类型>: <描述>
git commit -m "feat: 添加域名批量续费功能"
git commit -m "fix: 修复飞书通知未发送的 bug"
git commit -m "docs: 更新 DEVELOPMENT.md"
git commit -m "refactor: 重构 execution_service 错误处理"
```

| 类型 | 场景 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 代码重构（不改功能） |
| `chore` | 构建、依赖、配置变更 |

---

## 9. 部署到生产

开发完成后，参考 [服务器部署与运维手册](服务器部署维护文档.md) §3 执行部署：

```bash
git add <files>
git commit -m "描述"
git push origin main
# 然后 SSH 到服务器执行 deploy.sh
```

---

## 10. 开发规范自查清单

提交 PR / 推送前，逐条确认：

### 权限与安全

- [ ] 新增写操作路由是否带 `Depends(require_xxx)` 鉴权？
- [ ] 涉及注册商账号、服务商配置、用户角色变更的操作，是否调用了超管飞书确认？
- [ ] 前端是否正确处理了 `{status: "pending_approval"}` 响应（不以"成功"误导用户）？
- [ ] 有无硬编码 API Key / Secret（应在 `.env` 中）？

### 数据库

- [ ] 新增 ORM 模型是否已 import 到 `init_db.py`，确保 `create_all()` 能建表？
- [ ] 有枚举性质的初始数据（服务商类型等）是否以幂等方式写入 `init_db.py`？
- [ ] 有无破坏性字段变更（DROP/改类型/去非空）？如有，是否评估了生产数据影响？

### 前端

- [ ] API 调用是否经由 `src/api/index.ts` 的 `api` 实例？
- [ ] 列表接口解析是否用 `Array.isArray(res.data) ? res.data : []` 保护？
- [ ] CRUD 页面是否包含：加载状态、删除二次确认、错误提示？

### 文档

- [ ] `docs/CHANGELOG.md` 的 `[未发布]` 段落是否已追加本次变更？
- [ ] 如新增 API 路由，是否在路由文件顶部注释了权限要求和返回格式？

> 完整规范见项目根目录 [CLAUDE.md](../CLAUDE.md)。
