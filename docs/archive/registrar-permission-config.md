# 域名商 API 权限最小化配置指南

## 概述

本指南说明如何为各域名注册商和 DNS 服务商配置最小化权限，确保系统安全。

---

## Cloudflare

### 1. 注册商 API 权限（最小化）

**推荐权限配置：**

```
Zone:DNS:Edit  → 仅为域名设置 NS 服务器
Account:Registrar:Domains:Read  → 读取域名信息
Account:Registrar:Domains:Create  → 注册域名
Account:Registrar:Domains:Update  → 续费域名
```

**权限说明：**
- `Zone:DNS:Edit`：仅用于设置域名的 NS 服务器到 Cloudflare
- `Account:Registrar:Domains:Read`：读取域名信息、到期时间、注册状态
- `Account:Registrar:Domains:Create`：执行域名注册
- `Account:Registrar:Domains:Update`：执行域名续费

**不推荐的权限（避免使用）：**
- `Account:All`
- `Zone:All`
- `User:All`

---

### 2. DNS 解析 API 权限（最小化）

**推荐权限配置：**

```
Zone:DNS:Edit  → 读取和修改 DNS 记录
Zone:Read  → 读取 Zone 信息
```

**权限说明：**
- `Zone:DNS:Edit`：创建、修改、删除 DNS 记录
- `Zone:Read`：读取 Zone ID 等基本信息

---

## GoDaddy

### API 权限配置（最小化）

GoDaddy 使用 API Key 和 Secret 进行认证。

**最小权限范围：**

```json
{
  "products": {
    "domains": {
      "read": true,
      "write": false,
      "delete": false,
      "manage": false,
      "dns": {
        "read": true,
        "write": true,
        "delete": false
      }
    }
  }
}
```

**权限说明：**
- `domains.read`：读取域名信息
- `domains.write`：注册域名（如需要）
- `domains.dns.read`：读取 DNS 记录
- `domains.dns.write`：修改 DNS 记录

---

## Namecheap

### API 权限配置（最小化）

Namecheap API 需要在账户中启用并配置 IP 白名单。

**最小权限配置：**

```
API Permission: Enable
API Access from Specified IP Address: yes
IP Whitelist: <your-server-ip>
```

**权限说明：**
- 仅允许来自指定 IP 的 API 调用
- 不授予账户管理权限

---

## 最佳实践

### 1. 专用服务账号

为域名管家系统创建专用的 API 账号，不使用管理员个人账号。

### 2. IP 白名单

配置域名商 API 的 IP 白名单，仅允许您的服务器 IP 访问。

### 3. API Key 轮换

定期（建议每 3 个月）轮换 API Key。

### 4. 操作审计

启用操作日志，定期审计域名商 API 的调用记录。

### 5. 权限审核

定期审核 API 权限，移除不必要的权限。

---

## 配置检查清单

- [ ] 已使用最小权限原则配置各域名商 API
- [ ] 已创建专用服务账号
- [ ] 已配置 IP 白名单（如支持）
- [ ] 已启用操作日志
- [ ] 已设置 API Key 过期时间
- [ ] 已建立权限审核流程

---

## 安全建议

1. **不要使用全局管理员权限**：为域名管家创建专用的 API 账号
2. **定期轮换 API Key**：每 3 个月更新一次 API Key
3. **监控 API 使用**：设置异常使用告警
4. **启用多因素认证**：为域名商账户启用 MFA
5. **备份 API Key**：安全存储 API Key，使用密码管理器

---

## 问题排查

如遇到权限相关问题：
1. 检查 API Key 是否有效
2. 确认 IP 是否在白名单中
3. 验证权限配置是否正确
4. 查看域名商的错误日志
