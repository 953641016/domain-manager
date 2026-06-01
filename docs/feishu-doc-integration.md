# 飞书文档集成方案（确认版）

> 版本：v1.1  
> 更新日期：2026-05-31  
> 状态：✅ 设计已全部确认，后端部分已实现，待补完  
> 替代：PRD §5（旧版飞书工作流方案已废弃）

---

## 0. 核心原则

1. **飞书文档是主申请入口**，飞书机器人为备用入口
2. **文档表格纯输入，无状态追踪** —— 表格只记录"我想要的配置"，进度不回写
3. **所有容错在后端** —— 幂等判断、重复检测、可用性检查均由服务端负责
4. **写一次** —— 业务同事在 Bitable 填完记录，点一次按钮，在确认页填域名，完成
5. **文档可自由复制** —— 新域名直接复制文档，无需管理员介入，业务同事自助完成

---

## 1. 飞书文档结构

一个飞书文档对应一个域名。文档可以以已有域名文档为模板复制，复用按钮和表格结构。

```
飞书文档（大文档，域名章节为其中一节）
│
└── 二、域名购买/解析
    │
    ├── 域名购买
    │     [申请注册域名] 按钮
    │     （无 Bitable，域名在确认页填写）
    │
    ├── CF域名解析
    │     [申请CF域名跳转解析] 按钮
    │     └── 多维表格：Hostname | Type | Target
    │
    ├── Vercel域名解析
    │     [申请Vercel域名解析] 按钮
    │     └── 多维表格：Hostname | Type | Target
    │
    ├── Clerk域名解析
    │     [申请Clerk域名解析] 按钮
    │     └── 多维表格：Hostname | Type | Target
    │
    ├── GSC网站认证解析
    │     [申请GSC认证解析] 按钮
    │     └── 多维表格：Hostname | Type | Target
    │
    ├── 接口域名解析
    │     [申请接口域名解析] 按钮
    │     └── 多维表格：Hostname | Type | Target
    │
    └── 网站邮箱支持解析
          [申请邮箱映射] 按钮
          └── 多维表格：Hostname | Type | Target
```

> **域名注册**无需 Bitable，域名在确认页输入一次即可。
> DNS 类申请均有 Bitable，用户填好记录后点按钮批量提交。

---

## 2. 按钮类型与 URL 设计

### 2.1 按钮类型

飞书文档级别的**"打开超链接"按钮**，点击在浏览器中打开我们的确认页面。

### 2.2 按钮 URL 格式

**所有按钮 URL 只含 section 标识，不含域名、不含 Bitable ID：**

```
https://{our-domain}/feishu/confirm-request?section=vercel
https://{our-domain}/feishu/confirm-request?section=clerk
https://{our-domain}/feishu/confirm-request?section=domain_register
https://{our-domain}/feishu/confirm-request?section=cf_redirect
...
```

- 复制文档后按钮 URL 不需要修改，直接可用
- 域名由用户在确认页填写
- Bitable 绑定首次自助完成，之后自动匹配

---

## 3. 确认页交互设计

### 3.1 常规使用（已绑定 Bitable）

```
┌──────────────────────────────────────┐
│  申请 Vercel 域名解析                 │
│                                      │
│  域名：[newdomain.com      ]          │  ← 用户填写，唯一需要输入的信息
│                                      │
│  待配置记录（读自下方多维表格）：      │
│  • www   CNAME → e8b247f5...         │
│  • @     CNAME → e8b247f5...         │
│                                      │
│       [确认提交]   [取消]             │
└──────────────────────────────────────┘
```

### 3.2 首次使用新文档（Bitable 未绑定）

```
┌──────────────────────────────────────┐
│  申请 Vercel 域名解析                 │
│                                      │
│  域名：[newdomain.com      ]          │
│                                      │
│  首次使用，请绑定多维表格：           │
│  在飞书文档中将对应表格新页面打开，   │
│  粘贴地址栏 URL：                     │
│  [___________________________]        │
│                                      │
│       [确认提交]   [取消]             │
└──────────────────────────────────────┘
```

绑定后系统保存 `(section, feishu_user_id) → (app_token, table_id)`，
下次同一用户点击同一 section 按钮，自动加载 Bitable 数据，无需重复操作。

> **说明**：同一 section 可能被不同用户绑定不同 Bitable（各人管理自己的域名文档），
> 因此映射以 `(section, user_id)` 为 key，而非全局共享。

### 3.3 域名注册（无 Bitable）

```
┌──────────────────────────────────────┐
│  申请注册域名                         │
│                                      │
│  域名：[newdomain.com      ]          │
│                                      │
│       [确认提交]   [取消]             │
└──────────────────────────────────────┘
```

---

## 4. 完整触发链路

```
用户在 Bitable 填好 DNS 记录（或无需填，如域名注册）
        ↓
点击文档中的"申请XXX"按钮
        ↓
浏览器打开确认页（需飞书 OAuth 登录，验证身份和申请权限）
  ├── 验证用户存在且 is_active
  ├── 验证用户有 assigned_specialist_id（业务同事必须归属专员）
  ├── 首次使用：引导绑定 Bitable
  └── 展示待提交记录摘要
        ↓
用户填写域名 + 点"确认提交"
        ↓
POST /api/v1/feishu/confirm-request
  ├── 读取 Bitable 所有记录（调飞书 Bitable API）
  ├── 过滤空行
  └── 后端幂等判断（见第5节）
        ↓
创建申请记录（source=feishu_doc）
        ↓
向归属专员发飞书审批卡片
        ↓
专员点"批准" → 执行 → 差异化通知（专员看详情，业务同事看结果）
```

---

## 5. 后端容错与幂等处理

### 5.1 域名注册

| 情况 | 处理 |
|------|------|
| 域名在注册商 API 查询不可注册 | 拒绝，告知域名已被占用 |
| 域名已在系统中有记录 | 拒绝，告知已注册 |
| 该域名已有 pending 申请 | 拒绝，告知有待审批申请，避免重复 |
| 正常 | 创建申请，通知专员 |

### 5.2 DNS 解析（每条记录独立判断）

| 情况 | 处理 |
|------|------|
| 记录不存在 | 新增 |
| 记录存在，值完全一致 | 跳过（幂等，无需操作） |
| 记录存在，值不同 | 修改 |

批量提交时逐条处理，部分跳过不影响其他条。执行结果逐条返回给专员。

---

## 6. 数据库设计

### 6.1 Bitable 绑定映射表

```
feishu_bitable_configs
  ├── id
  ├── section        e.g. "vercel", "clerk", "cf_redirect"
  ├── user_id        绑定人（业务同事自助绑定）
  ├── app_token
  ├── table_id
  └── created_at
  UNIQUE (section, user_id)
```

---

## 7. 实现状态

### 已实现 ✅

| 功能 | 文件 |
|------|------|
| 读取 Bitable 记录 | `feishu_service.read_bitable_records()` |
| 向专员发 DNS 审批卡片 | `feishu_service.send_dns_approval_card()` |
| 主确认页数据接口 | `GET /feishu/confirm-data` |
| Bitable 自助绑定 | `POST /feishu/bind-bitable` |
| 提交申请 | `POST /feishu/submit-request` |
| 专员卡片回调处理 | `_handle_dns_card_action()` |
| 确认页前端 | `frontend/src/pages/FeishuConfirm.tsx` |
| DNS 执行幂等（存在且一致则跳过） | `execution_service._execute_dns()` |
| 域名注册幂等检查 | `request_service.get_pending_domain_request()` |
| 扫码注册走超管确认流 | `GET /feishu/add-user-callback`（已修） |

---

## 7.1 新版按钮申请流程（开发中）

> 2026-06-01 确认：业务入口调整为飞书多维表格/文档按钮直接请求后端。按钮只传文档定位与行为参数，后端按文档格式解析域名和 DNS 数据，先创建待审批申请，审核通过后再执行购买或解析。

### 按钮行为

| action | 说明 | 执行类型 |
|--------|------|----------|
| `domain_purchase` | 购买域名申请 | 域名注册 |
| `clerk_dns` | Clerk 域名解析 | DNS 解析 |
| `backend_dns` | 后端接口服务域名解析 | DNS 解析 |
| `vercel_dns` | Vercel 域名解析 | DNS 解析 |
| `cf_dns` | CF 域名解析 | DNS 解析 |
| `gsc_dns` | GSC 网站认证解析 | DNS 解析 |
| `all_dns_except_gsc` | 一键解析 Clerk + 后端接口 + Vercel + CF | DNS 解析 |

### 按钮请求体

```json
{
  "action": "vercel_dns",
  "doc_url": "https://z78zepeihr.feishu.cn/docx/xxxx",
  "doc_format": "standard_v1",
  "applicant_feishu_id": "ou_xxx",
  "source": "feishu_bitable_button"
}
```

- `doc_url` 必填：后端从 URL 中提取 docx token。
- `action` 必填：决定解析文档中的哪一段。
- `doc_format` 默认 `standard_v1`：兼容当前两类文档格式。
- `applicant_feishu_id` 必填：用于匹配系统用户、归属专员与通知申请人。
- 后端接口服务域名若文档只写 `svc.example.com`，解析目标由环境变量 `BACKEND_DNS_DEFAULT_TARGET` 提供。

### 审批卡片

购买域名卡片展示：申请域名、申请人、注册厂商账号下拉、注册年限、预估价格、来源文档、拒绝理由。购买域名卡片不提供备注字段；拒绝理由非必填。

DNS 卡片展示：申请类型、主域名、记录数量、记录预览、DNS 账号下拉、审核备注、拒绝理由。审核人只确认、选择账号、补备注；不在卡片中逐条修改 DNS 记录。若记录内容有误，申请人应修改飞书文档后重新提交。

### 账号权限

下拉选项必须按审核人权限过滤：

- `domain_spec` 只能选择 `owner_id = 当前专员.id` 且启用的注册账号/DNS 账号。
- `super_admin` 可选择全部启用账号。
- `admin` 不参与购买/解析审批；即使回调被触发，后端也必须拒绝。

卡片展示层和回调执行层都必须校验账号归属，不能信任前端或飞书回调传入的账号 ID。

### 待实施（飞书文档侧配置）

| 功能 | 说明 |
|------|------|
| 各节补建 Bitable 表格 | CF/GSC/邮箱三节尚未建 Bitable |
| 各按钮配置 URL | `?section=xxx` 格式 |

---

## 8. 业务人员加入流程

```
管理员在用户管理页面打开"扫码添加"
        ↓
出现飞书 OAuth 二维码
        ↓
业务人员用飞书扫码
        ↓
系统获取飞书用户信息 → 发超管飞书确认卡片
  ┌─────────────────────────────────────┐
  │  新用户申请加入                      │
  │  姓名：张三                          │
  │  飞书ID：ou_xxx                      │
  │  角色：业务人员                      │
  │  来源：扫码注册                      │
  │  [✅ 批准]  [❌ 拒绝]               │
  └─────────────────────────────────────┘
        ↓ 超管在飞书客户端点批准
系统创建用户记录 → 发飞书通知告知业务人员
        ↓
管理员在 Web 后台为该业务人员设置归属专员
  （此操作同样需要超管飞书确认）
```

> 注：若系统尚未配置超管（冷启动阶段），扫码后直接创建用户，跳过确认。

---

## 9. 文档复制使用流程（业务同事视角）

```
1. 复制已有域名文档作为模板
2. 修改 Bitable 表格内容（填入新域名的 DNS 记录）
3. 点任意一个申请按钮
4. 飞书 OAuth 登录（如未登录）
5. 确认页：填写域名 + 首次绑定 Bitable URL
6. 确认提交
7. 收到飞书消息，告知申请已提交，等待专员审批
```

全程无需管理员介入。
