# 域名管家 - 注册商配置指南（域名专员专用）

## 目录
1. [关于本文档](#1-关于本文档)
2. [Cloudflare 注册商](#2-cloudflare-注册商)
3. [GoDaddy 注册商](#3-godaddy-注册商)
4. [Namecheap 注册商](#4-namecheap-注册商)
5. [Enom 注册商](#5-enom-注册商)
6. [Cloudflare DNS 解析](#6-cloudflare-dns-解析)
7. [安全检查清单](#7-安全检查清单)

---

## 1. 关于本文档

### 1.1 使用说明

本文档供**域名专员**使用，用于配置各个注册商和解析商的 API Key。

**📌 重要提示：**
- **最小权限原则** - 只配置必要的权限
- **密钥安全** - 妥善保管 API Key，不要分享
- **专人负责** - 每个注册商账号指定一位域名专员管理

### 1.2 权限要求对照

| 操作 | 需要的权限 |
|------|-----------|
| 查询域名可用性 | Domain Availability |
| 注册域名 | Domain Register |
| 域名续费 | Domain Renew |
| 修改 Nameserver | Nameserver Update |
| 获取域名列表 | Domain List Read |

---

## 2. Cloudflare 注册商

Cloudflare 同时支持**域名注册**和**DNS解析**，推荐作为首选。

### 2.1 获取 API Token

#### 步骤 1: 登录 Cloudflare

访问 https://dash.cloudflare.com/ 使用您的账号登录

#### 步骤 2: 进入 API Tokens 页面

- 点击右上角头像 → 选择 "My Profile"
- 左侧菜单选择 "API Tokens"
- 或者直接访问：https://dash.cloudflare.com/profile/api-tokens

#### 步骤 3: 创建自定义 Token

- 点击 "Create Token"
- 点击 "Get Started" (Custom Token)
- 按照下方配置

#### 步骤 4: Token 配置

**Token Name（必填）:**
```
域名管家 - 注册管理 (生产环境)
```

**Permissions（权限配置）：**

| 权限类别 | 权限项 | 访问级别 |
|----------|--------|---------|
| Zone | Zone | Read |
| Zone | DNS | Edit |
| Account | Account Settings | Read |
| Account | Domain Registrar | Edit |

**Resources（资源范围）：**
- Include → Specific account or zone
- 选择您的账号

**TTL（有效期）：**
- 建议设置为 **No Expiration**（永不失效），或设为 1 年定期轮换

**Client IP Address Filtering（IP过滤，可选但推荐）：**
```
添加您服务器的出口 IP 地址
```

#### 步骤 5: 生成 Token

- 点击 "Continue to summary"
- 确认配置正确，点击 "Create Token"

**⚠️ 重要：**
1. 复制生成的 Token 并立即保存
2. 此 Token 只显示一次！
3. 将 Token 保存到密码管理工具

### 2.2 验证 Token

```bash
# 使用 curl 测试
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json"
```

### 2.3 在域名管家配置

配置项：
```
注册商类型: cloudflare
API Key: (粘贴上面的 Token)
Account ID: (查看 Cloudflare 账号设置页面获取)
```

---

## 3. GoDaddy 注册商

### 3.1 获取 API Key 和 Secret

#### 步骤 1: 登录 GoDaddy 开发者中心

访问: https://developer.godaddy.com/

#### 步骤 2: 创建 API Key

- 点击 "Create New App"
- 填写应用信息:

**App Name（必填）:**
```
域名管家 - 域名管理
```

**Description（可选）:**
```
企业内部域名管理系统使用
```

**Environment（环境）:**
- 先选 **OTE（测试环境）** 验证
- 确认后再创建 **Production（生产环境）**

#### 步骤 3: 获取 Key 和 Secret

创建成功后会显示：
```
API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API Secret: xxxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ 立即保存！** Secret 只显示一次。

### 3.2 权限范围 (Permissions)

GoDaddy API Key 默认有账号下所有权限，无法细粒度控制。

**安全建议：**
- 使用专门的子账号管理 API
- 开启 API Key IP 白名单
- 定期轮换 Key

### 3.3 验证 API Key

```bash
curl -X GET "https://api.godaddy.com/v1/domains?statuses=ACTIVE&limit=10" \
  -H "Authorization: sso-key YOUR_KEY_HERE:YOUR_SECRET_HERE"
```

### 3.4 在域名管家配置

配置项：
```
注册商类型: godaddy
API Key: (上面的 API Key)
API Secret: (上面的 API Secret)
环境: Production
```

---

## 4. Namecheap 注册商

### 4.1 获取 API Key

#### 步骤 1: 登录 Namecheap

访问 https://www.namecheap.com/

#### 步骤 2: 启用 API 访问

- 进入 Account → Profile
- 选择 "Tools" 选项卡
- 找到 "API Access" 部分
- 点击 "Manage" → "Enable"

#### 步骤 3: 获取 API 凭证

会得到以下信息：
- **API Key** - 自动生成
- **API User** - 您的 Namecheap 用户名
- **IP Allowlist** - 必须添加服务器 IP

**重要：**
1. 添加您服务器的公网 IP 地址
2. 最多可添加 10 个 IP
3. 未在白名单的 IP 无法访问 API

### 4.2 权限控制

Namecheap API Key 默认有账号下所有权限。

**安全建议：**
1. 使用专用的子账号
2. 开启 IP 白名单（必填）
3. 定期更换 API Key

### 4.3 在域名管家配置

配置项：
```
注册商类型: namecheap
API Key: (API Key)
API Username: (您的 Namecheap 用户名)
环境: Production
```

---

## 5. Enom 注册商

### 5.1 获取 API Key

#### 步骤 1: 登录 Enom

访问 https://www.enom.com/

#### 步骤 2: 申请 API 访问

- 进入 "Account Settings"
- 选择 "API 配置"
- 点击 "Enable API Access"

**注意：**
- Enom API 可能需要联系客服开通
- 可能需要付费账号

#### 步骤 3: 获取凭证

获得以下信息：
- **UID (User ID)** - 您的 Enom 账号 ID
- **PW (Password)** - API 专用密码

### 5.2 安全配置

**必须启用：**
- IP 白名单
- API 访问日志

### 5.3 在域名管家配置

配置项：
```
注册商类型: enom
UID: (User ID)
PW: (API Password)
环境: Production
```

---

## 6. Cloudflare DNS 解析

**强烈推荐使用 Cloudflare 作为 DNS 解析商！**

### 6.1 配置 API Token

复用上面 "2. Cloudflare 注册商" 创建的 Token，确保以下权限：

| 权限类别 | 权限项 | 访问级别 |
|----------|--------|---------|
| Zone | Zone | Read |
| Zone | DNS | Edit |

### 6.2 获取 Zone ID

每个域名在 Cloudflare 有唯一的 Zone ID：
1. 进入域名 Overview 页面
2. 在右侧 "API" 区域可以看到 "Zone ID"

### 6.3 在域名管家配置

配置项：
```
解析商类型: cloudflare
API Key: (Cloudflare Token)
Zone ID: (可选，或动态获取)
```

---

## 7. 安全检查清单

### 7.1 配置前检查

- [ ] 使用专用的子账号（不是主账号）
- [ ] 已配置最小必要权限
- [ ] 已添加服务器 IP 白名单（如果支持）
- [ ] API Key 已加密保存到密码管理工具
- [ ] 确认不是在公共电脑上操作

### 7.2 配置后检查

- [ ] 在域名管家测试连接成功
- [ ] 查询一个域名可用性（测试读权限）
- [ ] 尝试修改 Nameserver（测试写权限）
- [ ] 操作有记录到审计日志
- [ ] Key 已在团队文档中登记（不记录明文！）

### 7.3 定期维护

| 任务 | 频率 |
|------|------|
| 检查 API 访问日志 | 每周 |
| 轮换 API Key | 每季度 |
| 确认 IP 白名单 | 每季度 |
| 审计操作记录 | 每月 |

### 7.4 各注册商最小权限速查

**Cloudflare（注册商）**

| 权限 | 用途 |
|------|------|
| `Zone:DNS:Edit` | 设置域名 NS 服务器 |
| `Account:Registrar:Domains:Read` | 读取域名信息、到期时间 |
| `Account:Registrar:Domains:Create` | 执行域名注册 |
| `Account:Registrar:Domains:Update` | 执行域名续费 |

> ⚠️ 避免使用 `Account:All`、`Zone:All`、`User:All`

**Cloudflare（DNS 解析）**

| 权限 | 用途 |
|------|------|
| `Zone:DNS:Edit` | 创建、修改、删除 DNS 记录 |
| `Zone:Read` | 读取 Zone ID 等基本信息 |

**GoDaddy**

| 权限 | 用途 |
|------|------|
| `domains.read` | 读取域名信息 |
| `domains.write` | 注册域名 |
| `domains.dns.read` | 读取 DNS 记录 |
| `domains.dns.write` | 修改 DNS 记录 |

> GoDaddy API Key 无细粒度权限控制，务必使用**专用子账号** + IP 白名单。

**Namecheap**

- API 权限通过 **IP 白名单** 控制，无细粒度权限选项
- 必须在账户 Tools → API Access 中添加服务器公网 IP
- 强烈建议使用专用子账号

---

## 8. 常见问题

### Q: API Key 泄露了怎么办？

**A:** 立即执行：
1. 登录对应注册商平台
2. 撤销/删除泄露的 API Key
3. 生成新的 Key
4. 更新域名管家配置
5. 检查审计日志，确认无异常操作
6. 通知超级管理员

### Q: 可以在多个环境使用同一个 Key 吗？

**A:** 不建议。应该：
- 测试环境用测试 Key
- 生产环境用生产 Key

### Q: 测试环境和生产环境有什么区别？

| 注册商 | 测试环境 | 说明 |
|--------|---------|------|
| Cloudflare | 直接用生产 | 没有沙箱环境 |
| GoDaddy | OTE | https://api.ote-godaddy.com |
| Namecheap | Sandbox | https://api.sandbox.namecheap.com |
| Enom | 测试账号 | 联系支持获取 |

---

## 9. 快速配置卡片

给域名专员使用的快速参考：

### Cloudflare 快速步骤

```
1. https://dash.cloudflare.com/profile/api-tokens
2. Create Token → Custom Token
3. Token Name: 域名管家
4. Permissions:
   - Zone:Zone:Read
   - Zone:DNS:Edit
   - Account:Domain Registrar:Edit
5. 保存 Token (只显示一次！)
6. 粘贴到域名管家配置
```

### GoDaddy 快速步骤

```
1. https://developer.godaddy.com/
2. Create New App
3. Name: 域名管家
4. 保存 Key + Secret
5. 粘贴到域名管家配置
```

---

## 附录：支持的注册商功能对照

| 功能 | Cloudflare | GoDaddy | Namecheap | Enom |
|------|-----------|--------|----------|------|
| 域名查询 | ✅ | ✅ | ✅ | ✅ |
| 域名注册 | ✅ | ✅ | ✅ | ✅ |
| 域名续费 | ✅ | ✅ | ✅ | ✅ |
| 获取域名列表 | ✅ | ✅ | ✅ | ✅ |
| 修改 Nameserver | ✅ | ✅ | ✅ | ✅ |
| DNS 解析管理 | ✅ | 单独配置 | 单独配置 | 单独配置 |

---

**需要帮助？**
- 遇到问题联系系统管理员
- 安全问题立即上报超级管理员
