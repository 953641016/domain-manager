# Cloudflare Token 权限配置说明

本文档说明域名管家使用 Cloudflare 进行 DNS 解析、域名注册和重定向规则时，Token 需要具备的最小权限。

网页端入口：域名管家后台 → 域名账号管理 → DNS账号管理 → 「Cloudflare 权限说明」。

线上地址：`https://d.fwxg.com/dm/help/cloudflare-token-permissions`

## 一、DNS 解析账号权限

用于域名管家后台「DNS账号」的 Cloudflare Token，需要能访问 Zone 并读写 DNS 记录。

### 必需权限

在 Cloudflare Dashboard 中编辑 Token 时，进入权限策略页面：

1. 资源范围选择：
   - 测试阶段可选「所有域名」
   - 最小权限可选仅包含指定 Zone，例如 `joyai-echo.net`
2. 在 `DNS & Zones` 权限组中勾选：
   - `DNS`：`Edit`
   - `Zone`：`Read`
3. 保存 Token 后，回到域名管家后台 DNS 账号列表点击「自检」。

自检通过时应看到：

- `Zone 读取权限：可读取 Zone 列表`
- `DNS 记录读取权限：可读取 DNS 记录`

### 常见误区

以下权限不能替代 DNS 记录权限：

- `Account DNS Settings`
- `Zone DNS Settings`
- `DNS Firewall`
- `DNS View`

这些权限可能允许读取账号或 Zone 列表，但不能调用 Cloudflare DNS Records API 写入解析记录。

如果执行 DNS 解析时报：

```text
[{'code': 10000, 'message': 'Authentication error'}]
```

通常表示 Token 缺少 `DNS / Edit`，或资源范围未包含当前域名所在 Zone。

## 二、Cloudflare 重定向规则权限

如果申请中包含 CF 重定向规则，例如 `REDIRECT_301`，除了 DNS 权限外，还需要补充重定向规则相关权限。

在 `Rules & Configuration` 权限组中，按 Cloudflare 页面可见项选择：

- `Single Redirect`：`Edit`
- 或 `Dynamic URL Redirects`：`Edit`
- 或 `Rulesets`：`Edit`

不同 Cloudflare 后台版本名称可能略有差异，以页面中和 Redirect / Rulesets 相关的 Zone 级 `Edit` 权限为准。

## 三、域名注册账号权限

用于域名管家后台「注册账号」的 Cloudflare Token，需要 Cloudflare Registrar 权限。

至少需要：

- `Registrar Domains`：`Admin`

同时账号必须满足 Cloudflare Registrar 的前置条件：该域名后缀受 Cloudflare Registrar 支持，且账号已配置付款方式和默认联系人。

## 四、排查步骤

1. 在 Cloudflare 后台确认 Token 权限和资源范围。
2. 在域名管家后台 DNS 账号列表点击「自检」。
3. 如果 `Zone 读取权限` 通过但 `DNS 记录读取权限` 失败，优先补 `DNS / Edit`。
4. 如果 DNS 记录通过但重定向失败，补 Redirect / Rulesets 相关 `Edit` 权限。
5. 权限修改后重新自检，再重新提交或执行申请。
