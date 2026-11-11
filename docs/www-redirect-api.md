# 飞书多维表格按钮：裸域名自动 301 到 www

后端内部接口：`POST /api/v1/www-redirects`，JSON 请求/响应。
按钮地址保持 `https://d.fwxg.com/dm/api/www-redirects`。本次版本改为裸域名 → www；下方原方向部署验收属于历史记录。

## 飞书按钮请求

在按钮触发的自动化中配置“发送 HTTP 请求”（不要使用只打开网页的按钮）。

- 方法：`POST`
- URL：`https://d.fwxg.com/dm/api/www-redirects`
- 当前 Nginx 把 `/dm/api/<路径>` 重写为 `/api/v1/<路径>`，公网地址不要再加 `/v1`。
- Header：`Content-Type: application/json`

Body 中使用自动化编辑器插入当前记录的字段变量：

```json
{
  "domain": "example.com",
  "doc_url": "https://你的租户.feishu.cn/docx/文档Token",
  "applicant_feishu_id": "ou_域名专员的飞书ID",
  "verification_token": "与原按钮接口相同的Token，可省略"
}
```

`domain` 和 `doc_url` 均可省略、为 `null` 或空字符串，但至少一个能解析出有效域名。
`applicant_feishu_id` 必填，沿用旧接口的姓名/飞书 ID 查找方式；本接口直接执行，申请人须是启用的域名专员或超管。
`verification_token` 可选，复用原有 `FEISHU_VERIFICATION_TOKEN`，无新增配置项或专用请求头。
也支持不带 JSON body、全部通过 POST 查询参数传入；同时提供时以 JSON body 为准，与旧按钮接口一致。
请传纯文本域名/URL；超链接字段需要选择 URL 值，不能传整个单元格对象或数组。

1. `domain` 格式有效时优先使用，不读取 `doc_url`。接受裸域名、www 域名以及 HTTP/HTTPS URL，去除 www、路径、参数后归一化。
2. `domain` 缺失或格式无效时，从 `doc_url` 读取主域名。复用飞书应用身份，支持 docx 和指向 docx 的 wiki 链接；应用必须能读取文档。
3. 文档优先使用 `域名：example.com` / `主域名：example.com`、现有域名章节，缺失时使用标题。发现多个候选则返回 400，要求填写明确的 `domain`。
4. 如果有效的 `domain` 不在授权账号中或不是有效 Zone，则报错；不会悄悄改用文档中的另一个域名。

示例目标：`http://example.com/a?q=1` 和 `https://example.com/a?q=1` → `https://www.example.com/a?q=1`，状态码 301。

## 部署配置与权限

沿用 `POST /api/v1/feishu/doc-button/submit` 的可选 Token 校验逻辑：

| 服务端 FEISHU_VERIFICATION_TOKEN | 请求 verification_token | 行为 |
|---|---|---|
| 已配置 | 非空 | 比对，不匹配返回 403 |
| 已配置 | 未传、null 或空字符串 | 跳过 Token 校验 |
| 未配置 | 任意值或未传 | 跳过 Token 校验 |

不新增 Token、执行人绑定或其他环境配置；请求通过 `applicant_feishu_id` 选择执行人。
申请人不存在、已禁用或角色为 business/admin 时返回 403，缺少申请人返回 422。
Token 校验是兼容旧接口的可选校验，申请人存在性检查不构成调用者身份验证。
业务用户继续使用原有申请审批入口；本接口不修改账号、角色或系统配置，不替代这些操作的超管确认机制。
专员只能操作自己名下域名和 DNS 账号；超管可访问全部。未入本地域名表的域名只在执行人有权限的 Cloudflare 账号中按准确 Zone 名查找，不推测注册域名后缀。
已有本地 DNS 账号绑定时只用绑定账号；否则扫描可见的启用 Cloudflare 账号。多个账号命中返回 409，需在域名管理中绑定唯一账号。

Cloudflare Token 需包含目标 Zone、Zone 读取、DNS 读取/编辑、Single Redirect（Dynamic URL Redirects）编辑权限。
域名 Zone 必须 active；不会自动更换 NS 或注册域名。www 网站及 HTTPS 证书需可用，裸域名的 HTTPS 入口证书也须有效。

## 写入与结果

使用 Single Redirect Rulesets API，条件精确匹配裸域名 `<domain>`，目标由固定 `https://www.<domain>` 及原请求 path 组成，并启用保留查询字符串。
规则放到当前 Single Redirect 入口的第一位，仅 PATCH 同一 `ref` 的规则或新增一条；保留其他规则。沿用旧版 www 规则的稳定 ref，将该接口此前创建的反向规则原地改为裸域名 → www，避免新增双向规则。其他手工/外部系统规则保持原样，需检查是否存在反向跳转。

裸域名没有 A/AAAA/CNAME 时创建代理 A 记录 `192.0.2.1`；已有记录保留原目标并开启代理、TTL 改为自动。无法代理的地址记录会阻止执行。
www 必须已有真实网站解析，接口不会修改 www 记录；若缺少解析或仍指向旧跳转占位地址 `192.0.2.1` / `100::`，会在写入前报错。www 若通过 CNAME 指向裸域名，则裸域名必须已有真实源站解析，不能用占位地址，也不能反向 CNAME 回 www。

成功 HTTP 200 示例：

```json
{
  "status": "configured",
  "domain": "example.com",
  "domain_source": "domain",
  "dns_account_id": 1,
  "source_host": "example.com",
  "target_url": "https://www.example.com",
  "status_code": 301,
  "preserve_path": true,
  "preserve_query_string": true,
  "zone_id": "Cloudflare返回的Zone ID",
  "rule_id": "Cloudflare返回的规则ID",
  "is_config_verified": true,
  "is_live_verified": false,
  "message": "规则和代理解析已配置并读回；公网跳转及证书尚未验证"
}
```

`configured` 表示 Cloudflare 规则和代理解析已读回匹配；不表示 DNS 传播、www 证书签发或网站跳转已完成验收。接口不会对输入域名主动发公网请求。
上线后分别检查 HTTP/HTTPS、根路径/子路径/查询参数，以及 www 没有反跳裸域名，防止循环。

错误返回 `{"detail":"原因"}`。权限/读取错误不会被当成“没有规则”；远程写入之后发生失败返回 502，并标注可能已部分写入和失败阶段。
相同域名重试会更新同一标识的规则。请求超时先检查审计及 Cloudflare 状态，不要把超时认定为完全未执行。并发首次创建可能被 Cloudflare 拒绝，失败请求可串行重试；建议自动化避免同域名同时执行。
接口同步执行，多账号查询和文档读取会增加耗时；按飞书实际 HTTP 节点支持范围设置超时。
执行开始及结果写入审计，不发送额外飞书消息，不回写表格。无数据库迁移。

## 官方接口参考

- [Single Redirect API](https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-api/)
- [逐条新增规则和 position](https://developers.cloudflare.com/ruleset-engine/rulesets-api/add-rule/)
- [www 重定向与代理占位解析](https://developers.cloudflare.com/pages/how-to/www-redirect/)

## 原方向本地验证记录（2026-11-11，历史）

- 新接口 43 项测试通过，覆盖旧接口 Token 兼容矩阵（JSON/查询参数）、申请人角色/归属边界、参数优先级、文档歧义、幂等更新、代理解析、部分失败重试、读回不一致和审计。
- 全量测试：127 通过、2 失败。失败项为 `test_feishu_card_update.py` 的 `test_account_card_action_returns_before_database_validation`（mock 参数数量未跟随调用更新）和 `test_terminal_doc_action_failure_marks_request_failed`（对 SimpleNamespace 调用 SQLAlchemy object_session）。两项均已在独立临时目录的未修改 HEAD 上复现。
- 主应用 OpenAPI 已包含 POST `/api/v1/www-redirects`，复用 `verification_token` 参数，没有专用 Token 请求头；`git diff --check` 通过。
- Cloudflare/飞书写入使用模拟响应测试，未对业务域名添加测试规则；实际表格按钮尚待按上述配置填写。

## 原方向线上部署验收（2026-11-11，历史）

- 后端代码提交：`bc69631087aab4e78e04aac7b10ef5dc86f468ad`，已推送 GitHub main，使用 `bash deploy.sh backend` 部署至 `47.79.243.31:/opt/domain-manager`。
- 后端容器 `healthy`，重启计数 0，`/health` 返回 `{"status":"ok"}`；线上容器运行新增测试 43 项全部通过。
- 公网 `POST https://d.fwxg.com/dm/api/www-redirects`：缺少申请人返回 422；不存在的申请人返回 403，均命中新增路由。
- 使用真实启用专员但不提供域名/文档进行无写入校验：返回 400，说明申请人校验通过且输入保护生效。
- 当前线上 `FEISHU_VERIFICATION_TOKEN` 未配置，因此 `verification_token` 可省略，与旧按钮接口保持一致；未修改线上环境变量。
- 已保留旧镜像标签 `domain-manager-backend:rollback-before-www-bc69631`。未进行真实 Cloudflare 规则创建或公网 301 效果验收。

## 本次方向反转（2026-11-11）

- 请求地址、参数及 Token 兼容逻辑保持不变，裸域名通过 301 跳转至 HTTPS www，并保留路径和查询参数。
- 49 项接口测试通过，包括旧反向规则原地迁移、目标占位解析拦截及 www CNAME 到真实裸域名源站的场景。
- 部署后需对目标域名再次触发接口，才会更新该域名的服务商规则；部署不会批量更改已有规则。

## 既有审批测试修复（2026-11-11，本地）

- 两项既有失败已修复：同步后台函数模拟签名，使用真实 ORM 模型及独立临时 SQLite 验证失败终态持久化。
- 全量测试：136 通过、0 失败（9 条依赖弃用警告）。未修改生产审批代码。

## 方向反转线上发布验收（2026-11-11）

- 代码提交 `0cae6e700137ffd8aa1e7aca0d8a74cb77cb2dfa` 已推送 main，并通过 `bash deploy.sh backend` 部署。包含裸域名 → HTTPS www 方向反转和两项既有审批测试修复。
- 后端容器 `healthy`，重启计数 0，健康接口返回 `{"status":"ok"}`；线上容器全量测试 **136 通过、0 失败**（10 条警告）。
- 公网 POST `https://d.fwxg.com/dm/api/www-redirects` 缺少申请人返回 422，不存在的申请人返回 403；前端 `/dm/` 返回 200。接口参数和 Token 兼容方式未变。
- 回滚镜像：`domain-manager-backend:rollback-before-apex-www-0cae6e7`。
- 未批量更新已有服务商规则，未对业务域名做测试写入。下次调用接口时才为对应域名配置新方向；www 必须已有真实网站解析，已有旧占位地址会在写入前被拦截。
