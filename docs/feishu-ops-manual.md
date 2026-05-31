# 飞书集成运维手册

> 适用版本：当前生产环境（2026-05）  
> 应用名称：**池源域名管家**  
> App ID：`cli_aa90bce2dd78dbdf`  
> 生产地址：`https://d.fwxg.com`

---

## 目录

1. [飞书开放平台配置](#1-飞书开放平台配置)
2. [后端环境变量](#2-后端环境变量)
3. [Webhook 端点说明](#3-webhook-端点说明)
4. [卡片交互审批流程](#4-卡片交互审批流程)
5. [初始化超级管理员](#5-初始化超级管理员)
6. [常见问题排查](#6-常见问题排查)
7. [发布新版本（飞书应用）](#7-发布新版本飞书应用)

---

## 1. 飞书开放平台配置

入口：<https://open.feishu.cn/app/cli_aa90bce2dd78dbdf>

### 1.1 凭证与基础信息

路径：**凭证与基础信息**

| 配置项 | 说明 |
|--------|------|
| App ID | 填入 `.env` 的 `FEISHU_APP_ID` |
| App Secret | 填入 `.env` 的 `FEISHU_APP_SECRET` |

### 1.2 安全设置

路径：**安全设置**

| 配置项 | 值 |
|--------|----|
| 重定向 URL（OAuth 回调） | `https://d.fwxg.com/dm/api/auth/callback` |
| IP 白名单 | `115.28.211.155`（生产服务器 IP） |

> ⚠️ 重定向 URL 路径**不含 `v1`**。Nginx `rewrite` 规则负责将 `/dm/api/auth/callback` → `/api/v1/auth/callback`（见 §3.4）。  
> 填写时**不要**写成 `/dm/api/v1/auth/callback`，否则后端会收到 `/api/v1/v1/auth/callback` → 404。

### 1.3 权限管理

路径：**权限管理**，需开通以下权限：

| 权限名称 | 权限 ID | 用途 |
|---------|---------|------|
| 获取用户基本信息 | `contact:user.base:readonly` | OAuth 登录 |
| 获取用户邮箱 | `contact:user.email:readonly` | 用户信息同步 |
| 获取用户手机号 | `contact:user.phone:readonly` | 用户信息同步 |
| 读取通讯录 | `contact:contact:readonly` | 按姓名搜索用户 |
| 发送消息 | `im:message` | 机器人推送卡片/文字 |
| 以应用身份读取通讯录 | `contact:contact.base:readonly` | 搜索用户 |

### 1.4 机器人（Bot）

路径：**应用能力 → 机器人**  
确认机器人功能已**启用**。

### 1.5 事件订阅（接收消息事件）

路径：**事件与回调 → 事件配置**

| 配置项 | 值 |
|--------|----|
| 订阅方式 | 将事件发送至**开发者服务器** |
| 请求地址 | `https://d.fwxg.com/dm/api/feishu/webhook` |
| 已订阅事件 | `im.message.receive_v1`（接收消息） |

> Nginx 将 `/dm/api/feishu/webhook` → `/api/v1/feishu/webhook`（见 §3.4）。

### 1.6 回调配置（卡片按钮交互）⚠️ 关键

路径：**事件与回调 → 回调配置**

> **这是独立于「事件订阅」的另一个配置项，缺失此项会导致卡片按钮点击报错 200340。**

| 配置项 | 值 |
|--------|----|
| 订阅方式 | 将回调发送至**开发者服务器** |
| 请求地址 | `https://d.fwxg.com/dm/api/feishu/webhook` |
| 已订阅的回调 | `card.action.trigger`（卡片回传交互） |

配置步骤：
1. 选择「将回调发送至 开发者服务器」
2. 请求地址填 `https://d.fwxg.com/dm/api/feishu/webhook`，点「保存」
3. 在「已订阅的回调」区域点「添加回调」→ 选择「卡片回传交互」
4. 前往 **版本管理与发布** 创建新版本并发布，改动才生效

### 1.7 配置检查清单

```
[ ] 凭证：App ID / App Secret 已填入 .env
[ ] 安全设置：重定向 URL 已添加
[ ] 安全设置：IP 白名单 115.28.211.155 已添加
[ ] 权限管理：以上权限均已开通
[ ] 机器人：功能已启用
[ ] 事件配置：im.message.receive_v1 已订阅，请求地址正确
[ ] 回调配置：card.action.trigger 已订阅，请求地址正确
[ ] 已发布新版本
```

---

## 2. 后端环境变量

文件位置（服务器）：`/opt/domain-manager/backend/.env`  
或通过 docker-compose 的 `env_file` 挂载。

```ini
# ── 飞书应用 ──────────────────────────────
FEISHU_APP_ID=cli_aa90bce2dd78dbdf
FEISHU_APP_SECRET=<从开放平台凭证页获取>

# Verification Token：在「事件配置」或「回调配置」页面查看
# 事件订阅和卡片回调共用同一个 token（后端统一验证）
FEISHU_VERIFICATION_TOKEN=<Verification Token>

# Encrypt Key（可选，若开启加密则填写）
FEISHU_ENCRYPT_KEY=

# 超级管理员的飞书 user_id（ou_ 开头）
# 决定哪个账号能收到授权卡片并执行审批
SUPER_ADMIN_FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx
```

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `FEISHU_APP_ID` | ✅ | App ID |
| `FEISHU_APP_SECRET` | ✅ | App Secret |
| `FEISHU_VERIFICATION_TOKEN` | ✅ | Token 签名验证，防伪造请求 |
| `FEISHU_ENCRYPT_KEY` | 否 | 事件加密（当前未启用） |
| `SUPER_ADMIN_FEISHU_USER_ID` | ✅ | 超管飞书 user_id，用于寻找审批人和发卡片 |

修改 `.env` 后需重启容器：

```bash
docker compose restart backend
```

---

## 3. Webhook 端点说明

后端统一入口：`POST /api/v1/feishu/webhook`  
对应文件：`backend/app/api/v1/feishu.py` → `feishu_webhook()`

### 3.1 请求类型识别逻辑

```
请求体
├── type == "url_verification"       → 返回 challenge（开放平台 URL 验证）
├── header.event_type == "im.message.receive_v1"  → 机器人消息处理
├── type == "card" 或
│   header.event_type == "card.action.trigger"   → 卡片按钮回调处理
└── 其他                              → 忽略，返回 success
```

### 3.2 Token 签名验证

飞书有两种 Schema：
- **Schema 1.0**（旧）：`token` 在请求体根节点 `body["token"]`
- **Schema 2.0**（新）：`token` 在 `body["header"]["token"]`

后端同时兼容两种位置：

```python
token_in_body = (
    request_body.get("token")
    or request_body.get("header", {}).get("token")
)
feishu_service.verify_webhook_signature_token(token_in_body)
```

若 `FEISHU_VERIFICATION_TOKEN` 未配置，后端跳过验证（仅限开发/测试）。

### 3.3 查看 Webhook 日志

```bash
# 进入后端容器
docker exec -it domain-manager-backend bash

# 查看实时日志
tail -f /app/logs/app.log | grep feishu

# 或查看 access log 确认请求有无到达
tail -f /app/logs/access.log | grep feishu
```

### 3.4 Nginx 路由与 Rewrite 规则

配置文件：`nginx/conf.d/domainmanager.conf`（Docker Compose 挂载）

#### 核心 API 代理块

```nginx
# 域名管家 - API 代理（/dm/api/* → /api/v1/*）
location ^~ /dm/api/ {
    rewrite ^/dm/api/(.*) /api/v1/$1 break;
    proxy_pass http://backend:8000;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    client_max_body_size 10M;
}
```

#### 路径映射对照表

| 外部 URL（飞书/浏览器发出） | 到达后端的路径 |
|----------------------------|--------------|
| `https://d.fwxg.com/dm/api/feishu/webhook` | `POST /api/v1/feishu/webhook` |
| `https://d.fwxg.com/dm/api/auth/callback` | `GET /api/v1/auth/callback` |
| `https://d.fwxg.com/dm/api/users/me` | `GET /api/v1/users/me` |
| `https://d.fwxg.com/dm/api/domains/` | `GET /api/v1/domains/` |

**rewrite 语法说明**

```
rewrite ^/dm/api/(.*) /api/v1/$1 break;
```

- `^/dm/api/(.*)` 捕获 `/dm/api/` 之后的全部路径
- 替换为 `/api/v1/$1`
- `break` 表示不再匹配后续 rewrite 规则，直接 `proxy_pass`

> ⚠️ **常见错误**：在飞书后台填 `https://d.fwxg.com/dm/api/v1/feishu/webhook`（多写了 `v1`），经 rewrite 后后端收到 `/api/v1/v1/feishu/webhook` → 404。正确写法一律省略 `v1`。

#### 验证 Nginx rewrite 是否生效

```bash
# 在服务器上直接测 backend 监听端口（绕过 Nginx）
curl -s http://localhost:8000/api/v1/feishu/webhook \
  -X POST -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123","token":"your_token"}'
# 期望：{"challenge":"test123"}

# 再通过公网完整路径测试（走 Nginx rewrite）
curl -s https://d.fwxg.com/dm/api/feishu/webhook \
  -X POST -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123","token":"your_token"}'
# 两次结果相同 → Nginx rewrite 正常
```

---

## 4. 卡片交互审批流程

### 4.1 卡片类型

| 卡片标题 | 卡片颜色 | 触发场景 | 发送给 |
|---------|---------|---------|-------|
| 👑 超管转让授权申请 | 🔴 红色 | 将某用户角色改为超级管理员（触发原子转让） | 超级管理员 |
| 👤 用户管理授权申请 | 🟠 橙色 | 创建/禁用/激活/修改用户 | 超级管理员 |
| 👤 用户管理授权申请 | 🔴 红色 | 删除用户（不可恢复） | 超级管理员 |
| 🔐 账号配置授权申请 | 🟠 橙色 | 新增/修改注册账号或解析账号 | 超级管理员 |
| 🔐 账号配置授权申请 | 🔴 红色 | 删除注册账号或解析账号（不可恢复） | 超级管理员 |
| 🏷️ 服务商配置授权申请 | 🟠/🔴 | 新增/修改/删除服务商（删除时红色） | 超级管理员 |
| 🌐 DNS 解析申请 | 🔵 蓝色 | 业务员提交 DNS 解析申请 | 归属域名专员 |

> 颜色规则：**红色 = 高危/不可逆**（删除类操作、超管转让），**橙色 = 普通授权**，**蓝色 = DNS 技术操作**。
> 详见 [飞书卡片设计规范](feishu-card-design-spec.md)。

### 4.2 卡片格式（账号操作类）

```
👤 用户管理授权申请
申请人：张健
操作事项：禁用用户
操作对象：系统管理员（系统管理员，禁用后可恢复）

[✅ 授权执行]  [❌ 拒绝]
```

### 4.3 审批流程

```
管理员在 Web 触发敏感操作
    ↓
后端创建 UserOperationConfirmation 记录（status=pending）
    ↓
发飞书卡片给超级管理员（按 SUPER_ADMIN_FEISHU_USER_ID 寻找）
    ↓
超管点击「✅ 授权执行」
    ↓
飞书 → POST https://d.fwxg.com/dm/api/feishu/webhook（card.action.trigger）
    ↓
后端验证：操作人必须是 super_admin 角色
    ↓
执行实际操作（用户增删改 / 账号配置 / 服务商配置）
    ↓
飞书通知发起人：成功 ✅ 或失败 ⚠️
```

### 4.4 卡片按钮 value 结构

```json
// 账号操作卡片（✅ 授权执行）
{
  "action": "approve_account_op",
  "confirmation_id": "123"
}

// 账号操作卡片（❌ 拒绝）
{
  "action": "reject_account_op",
  "confirmation_id": "123"
}

// DNS 解析申请卡片（✅ 批准执行）
{
  "action": "approve_dns_request",
  "request_id": "uuid-xxx"
}

// DNS 解析申请卡片（❌ 拒绝）
{
  "action": "reject_dns_request",
  "request_id": "uuid-xxx"
}
```

### 4.5 确认记录有效期

待审批的确认记录默认 **24 小时**后过期（`CONFIRMATION_EXPIRE_HOURS = 24`），过期后自动变为 `cancelled`，超管点击按钮将返回"已处理或不存在"。

---

## 5. 初始化超级管理员

### 5.1 首次部署

```bash
docker exec -it domain-manager-backend bash
cd /app
python scripts/init_db.py
```

脚本会创建数据表并生成初始超管账号（绑定 `SUPER_ADMIN_FEISHU_USER_ID`）。

### 5.2 直接操作数据库

数据库文件位于容器内 `/app/data/domain_manager.db`。

```bash
# 从容器中查询用户
docker exec domain-manager-backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/domain_manager.db')
cur = conn.cursor()
cur.execute('SELECT id, name, email, role, is_active FROM users')
for row in cur.fetchall():
    print(row)
conn.close()
"

# 直接删除某用户（通过宿主机 sqlite3，需先 docker cp）
docker cp domain-manager-backend:/app/data/domain_manager.db /tmp/dm.db
sqlite3 /tmp/dm.db "DELETE FROM users WHERE email='xxx@company.com';"
docker cp /tmp/dm.db domain-manager-backend:/app/data/domain_manager.db
docker restart domain-manager-backend
```

> ⚠️ 删除超管账号前确认系统内还有其他 super_admin，否则无法通过飞书卡片审批任何操作。

---

## 6. 常见问题排查

### 问题一：点击卡片按钮报错 200340

**原因**：飞书回调没有到达服务器，或服务器返回非 2xx。

排查步骤：
1. 检查「回调配置」是否已配置且已发布版本（见 §1.6）
2. 检查服务器 access log 有无收到 POST 请求
3. 检查 `app.log` 中 `feishu.webhook` 的日志

```bash
docker exec domain-manager-backend tail -100 /app/logs/app.log | grep -E "feishu|webhook|card"
```

### 问题二：卡片按钮点击后返回"只有超级管理员可以审批"

**原因**：点击按钮的飞书账号的 `open_id` 在数据库中没有找到 `super_admin` 角色的用户，或者该用户的 `feishu_open_id` / `feishu_user_id` 字段未正确存储。

排查：查询数据库确认超管记录的飞书 ID 字段。

### 问题三：卡片发不出去（超管收不到消息）

**原因**：`SUPER_ADMIN_FEISHU_USER_ID` 未配置，或该飞书 ID 在数据库中找不到活跃用户。

排查：
1. 检查 `.env` 中 `SUPER_ADMIN_FEISHU_USER_ID` 是否填写
2. 检查数据库 `users` 表中对应 `feishu_user_id` 的记录是否存在且 `is_active=1`

### 问题四：URL 验证（challenge）失败

**原因**：`FEISHU_VERIFICATION_TOKEN` 与开放平台不一致，或端点不通。

确认后端可正常访问：

```bash
curl -s https://d.fwxg.com/dm/api/feishu/webhook \
  -X POST -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test","token":"<your_token>"}'
# 期望返回 {"challenge":"test"}
```

### 问题五：OAuth 登录失败（redirect_uri mismatch）

检查「安全设置」中重定向 URL 是否精确匹配 `https://d.fwxg.com/dm/api/auth/callback`（无尾斜杠）。

---

## 7. 发布新版本（飞书应用）

### 7.1 什么时候需要发新版本

只要在飞书开放平台修改了以下任一配置，**必须创建并发布新版本才能生效**：

| 改动类型 | 举例 |
|---------|------|
| 事件配置 | 新增/删除订阅事件、修改 Webhook 地址 |
| 卡片回调配置 | 修改回调 URL |
| 权限（API 作用域） | 新增 `im:message:send_as_bot` 等权限 |
| 安全设置 | 修改重定向 URL 白名单 |
| 应用名称/描述/图标 | 品牌信息调整 |

> 仅修改服务器 `.env`、重启容器、部署新代码，**不需要**在飞书发新版本，因为 Webhook 地址和权限没有变化。

---

### 7.2 发布步骤

#### Step 1 — 进入"版本管理与发布"

1. 打开 [飞书开放平台](https://open.feishu.cn/) → 进入企业后台
2. 在应用列表中找到 **域名管家**，点击进入应用详情
3. 左侧菜单：**版本管理与发布**

#### Step 2 — 创建新版本

点击右上角 **「创建版本」** 按钮，弹出表单：

| 字段 | 说明 | 示例 |
|------|------|------|
| **版本号** | 格式 `x.x.x`，手动递增，**不能与已有版本重复** | `1.3.4` |
| **版本说明** | 本次改动摘要，方便后续追溯（中英文均可） | `修复 Webhook 回调地址；新增消息发送权限` |
| **可用范围** | 企业自建应用通常保持「**全部员工**」；若仅内测选「部分员工」并添加测试人员 | 全部员工 |

填写完毕后点 **「确定」** 提交。

#### Step 3 — 等待审核

- **企业自建应用**（本项目）：审核由企业管理员自动或手动通过，通常**立即或数分钟内**完成，无需等待飞书官方审核。
- 若长时间（>10 分钟）仍停在「审核中」，检查企业管理后台是否有待审批的应用发布申请。

#### Step 4 — 确认上线

回到 **「版本管理与发布」** 页面，在版本列表中确认该版本的状态已变为 **「已上线」**。

此时新配置（Webhook、权限、回调 URL 等）立即对全体员工生效。

---

### 7.3 发布后验证

```bash
# 1. 触发一次 URL 验证，确认 Webhook 可达
curl -s https://d.fwxg.com/dm/api/feishu/webhook \
  -X POST -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"post-release-test","token":"<your_token>"}'
# 期望：{"challenge":"post-release-test"}

# 2. 查看后端日志，确认没有 token 校验失败
docker exec domain-manager-backend tail -50 /app/logs/app.log | grep -E "feishu|webhook"
```

如果 Webhook 验证通过，说明新版本配置已生效。

---

### 7.4 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 「版本号已存在」 | 填写了已用过的版本号 | 递增 patch 位，如 `1.3.3` → `1.3.4` |
| 审核一直停在「审核中」 | 企业管理员未处理发布申请 | 让企业管理员登录管理后台审批 |
| 发布成功但权限仍报错 | 新增权限未在版本中包含，或员工未重新授权 | 检查「权限管理」页面该权限是否状态为「已启用」 |
| 可用范围未覆盖某员工 | 发布时选了「部分员工」但未添加该员工 | 重新发版，将可用范围改为「全部员工」 |
| 修改了配置但没发版 | 以为保存即生效 | 按 7.2 步骤创建新版本并发布 |

---

## 附录：关键文件索引

| 文件 | 说明 |
|------|------|
| `backend/app/api/v1/feishu.py` | Webhook 入口路由、卡片回调处理 `_handle_card_action` |
| `backend/app/services/feishu_service.py` | 飞书 API 封装（发消息/发卡片/Token 验证） |
| `backend/app/services/user_confirmation_service.py` | 审批卡片发送、审批执行、通知发起人 |
| `backend/app/config.py` | 环境变量读取（`FEISHU_*`、`SUPER_ADMIN_FEISHU_USER_ID`） |
| `backend/.env` | 生产环境变量（服务器上，不提交 Git） |
