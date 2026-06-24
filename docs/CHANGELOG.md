# CHANGELOG

本文档记录域名管家的主要功能变更和修复历史。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 新增
- **GSC 认证值直传参数**（`backend/app/api/v1/feishu.py`、`backend/app/services/feishu_doc_parser.py`）：飞书文档按钮 `gsc_dns` 支持可选 `gsc_verification` 参数；传入 `google-site-verification=...` 时直接生成根域 TXT 认证记录，为空或不传时继续从飞书文档解析。
- **注册成功后自动发起后端解析申请**（`backend/app/services/execution_service.py`）：域名注册最终成功后自动创建 `backend_dns` 待审批申请，默认生成 `svc` A 记录到 `BACKEND_DNS_DEFAULT_TARGET`，并发送给同一域名专员审批；若同域名已有待处理/已完成后端解析申请则不重复创建。
- **域名购买直传域名参数**（`backend/app/api/v1/feishu.py`、`docs/feishu-doc-integration.md`）：飞书文档按钮 `domain_purchase` 支持可选 `register_domain` 参数；传入时以该域名作为注册目标，不再从文档正文解析域名，为空则保持原文档解析流程，DNS 解析类按钮不使用该参数。
- **Cloudflare Token 权限说明**（`docs/CLOUDFLARE_TOKEN_PERMISSIONS.md`、`frontend/src/pages/Help/CloudflareTokenPermissions.tsx`）：新增 Cloudflare DNS 解析、重定向规则和 Registrar Token 最小权限配置说明；后台新增 `/help/cloudflare-token-permissions` 可读页面，并在 DNS账号管理页提供入口。
- **飞书卡片回调开发规范**（`docs/feishu-card-design-spec.md`）：新增 `200341` 超时避坑规则，明确卡片回调 3 秒内返回、禁止响应前调用外部 API 或更新卡片，后续慢操作必须后台化。
- **飞书菜单自主注册域名**（`backend/app/api/v1/feishu.py`）：支持机器人底部菜单事件触发“自主注册域名”入口；域名专员/超级管理员点击后返回飞书表单卡片，可填写域名、注册账号、年限和可选联系人 JSON，提交后直接创建并批准注册申请，后台执行注册、发送结果卡片并写入操作日志；无权限用户会收到无权限提示卡片。
- **DNS 记录同步合并逻辑**（`backend/app/tasks/scheduler.py`）：定时同步远程 DNS 记录时不再只计数，会将服务商返回的记录合并到本地表，支持新增、更新、远程缺失记录软删除，并在审计日志中记录新增/更新/删除数量。
- **基础单元测试**（`pytest.ini`、`backend/tests/`）：新增后端测试入口，覆盖 Web 端业务流程写接口禁用、DNS 记录同步合并、Namecheap/Enom 占位注册商隐藏。
- **服务商账号自检**（`backend/app/api/v1/domains.py`、`frontend/src/pages/Config.tsx`）：注册账号和 DNS 账号列表新增“自检”按钮；后端只读调用服务商接口检查凭据与权限，注册账号检测查价/可注册性接口，Cloudflare DNS 检测 Token 与 Zone 读取权限，DNSPod 检测域名列表读取权限，并在前端展示原始失败原因。
- **Cloudflare 重定向规则执行**（`backend/app/adapters/cloudflare.py`、`backend/app/services/execution_service.py`）：DNS 申请中的 `REDIRECT_301`、`REDIRECT_302` 不再按普通 DNS 记录处理，Cloudflare 账号会通过 Rulesets API 创建或更新 Single Redirect 规则，并保持审批重复点击时幂等更新。
- **后台申请详情账号选择**（`frontend/src/pages/Requests/Detail.tsx`）：后台 `/requests` 详情页待审批申请新增注册账号/DNS账号下拉选择，点击通过时会将所选账号传给后端执行，未选择时仍保留后端自动推断。
- **超管审批卡片信息增强**（`backend/app/services/user_confirmation_service.py`）：账号/默认配置授权卡片新增申请时间、拒绝理由输入框（可选）、注册商/DNS 服务商信息；审批结果同时通知申请人和审核人。
- **飞书文档按钮申请流**（`backend/app/api/v1/feishu.py`、`backend/app/services/feishu_doc_parser.py`）：新增 `POST /api/v1/feishu/doc-button/submit`，支持飞书多维表格/文档按钮仅传 `action + doc_url + doc_format + applicant_feishu_id`，后端读取 docx 内容并按 `domain_purchase`、`clerk_dns`、`backend_dns`、`vercel_dns`、`cf_dns`、`gsc_dns`、`all_dns_except_gsc` 归一生成申请。
- **新版审批卡片**：购买域名卡片展示域名、申请人、注册账号下拉、注册年限、预估价格、来源文档、拒绝理由；DNS 卡片展示记录预览、DNS 账号下拉、审核备注、拒绝理由。审批通过后自动执行，拒绝后通知申请人。
- **域名购买报价联动**（`backend/app/api/v1/feishu.py`）：购买域名审批卡片按审核人可用的 Cloudflare/GoDaddy 注册账号实时获取报价，下拉选项展示账号与价格；审批通过时按最终选择的账号重新查价，服务商明确返回不可注册时阻止执行。
- **后台默认注册服务商配置**（`frontend/src/pages/Config.tsx`）：注册账号表单按 Cloudflare/GoDaddy 展示 Token、Account ID、API Key、Secret 等对应字段，支持新增/编辑时设为默认注册服务商；列表页用徽标与“默认注册账号”列清晰展示默认账号。
- **飞书文档解析配置收口**（`backend/app/config.py`、`backend/app/services/feishu_doc_parser.py`）：文档、Wiki 和多维表格读取统一复用 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，不再维护独立的 `FEISHU_DOC_APP_ID` / `FEISHU_DOC_APP_SECRET`；保留 `BACKEND_DNS_DEFAULT_TARGET` 用于后端接口域名默认解析目标。

### 安全/权限
- **审批账号过滤**：审批卡片中的注册账号/DNS账号仅展示当前域名专员名下启用账号；超管可见全部启用账号。回调执行时再次校验账号归属，避免越权使用他人账号。
- **统计/审计权限收口**（`backend/app/models/permission.py`、`backend/app/api/v1/audit.py`、`frontend/src/App.tsx`）：按权限规划允许域名专员访问统计报表和操作日志；后端审计接口改为 `can_view_audit` / `can_view_statistics` 权限，并对域名专员仅返回本人及归属业务人员相关数据。
- **系统任务审计展示**（`backend/app/services/audit_service.py`）：系统定时任务写入审计日志时若无人工操作人，用户列统一显示为“系统任务”，避免后台日志列表出现空用户。
- **系统同步日志资源名**（`backend/app/tasks/scheduler.py`）：域名状态同步和 DNS 记录同步日志写入真实成功/失败数量，资源列显示如“DNS记录同步: 成功 4 / 失败 0”，不再显示空资源名。
- **操作日志筛选增强**（`backend/app/api/v1/audit.py`、`backend/app/services/audit_service.py`、`frontend/src/pages/Logs.tsx`）：操作日志支持按“用户操作/系统任务”、日期范围、关键词、用户关键词筛选，便于系统任务增多后快速定位。
- **操作日志筛选体验优化**（`frontend/src/pages/Logs.tsx`）：日志类型从下拉框改为“全部日志 / 用户操作 / 系统任务”选项卡，筛选控件收纳到独立卡片中；关键词、用户、日期、操作、资源筛选改为点击“搜索”后再请求，日期区间改为仿 Element DatePicker 的双月范围选择器，支持快捷范围、起止日期高亮和统一确认，避免输入时频繁刷新列表。

### 修复
- **域名购买直传域名不再强依赖文档链接**（`backend/app/api/v1/feishu.py`）：`domain_purchase` 传入 `register_domain` 时不再要求 `doc_url`，也不再解析文档 token，避免飞书多维表格只传域名或来源链接格式异常时返回 400；卡片无来源文档时显示“未提供”。
- **飞书业务申请有效期校验**（`backend/app/services/request_service.py`、`backend/app/api/v1/feishu.py`）：域名购买/DNS 解析等业务申请审批统一增加 24 小时后端有效期校验；逾期点击批准或拒绝会自动作废并返回提示，但不回写原审批卡片、不额外发送过期通知，避免长期 pending 申请被误执行。域名专员通过飞书应用底部菜单打开的自主注册域名表单增加 1 小时输入有效期，超时提交会提示重新打开表单。
- **飞书域名购买审批回调兼容**（`backend/app/api/v1/feishu.py`）：兼容飞书卡片旧版/新版回调结构、JSON 字符串形式的按钮 `value` 和根节点操作人信息；域名购买审批和自主注册表单未修改注册账号下拉框时会兜底使用默认注册账号，后台校验失败时主动向审批人/申请人发送“审批未执行”原因通知，避免卡片显示已受理但实际未扣费、未执行、无结果。
- **飞书申请人提交回执卡片**（`backend/app/api/v1/feishu.py`）：飞书文档/多维表格按钮提交域名购买或 DNS 解析申请后，除审核人收到可操作审批卡片外，申请人同步收到无按钮的只读“申请已提交/待审批”卡片，便于确认申请已进入审核流程。
- **飞书超管审批原卡片状态回写**（`backend/app/services/feishu_service.py`、`backend/app/services/user_confirmation_service.py`）：用户管理/账号配置授权卡片在审批通过或拒绝后，会用原 `message_id` 更新为“已授权/已拒绝/已授权但执行失败”状态并移除操作按钮，同时保留后续结果通知卡片，避免旧卡片看起来仍可审批。
- **飞书业务审批原卡片状态回写**（`backend/app/api/v1/feishu.py`、`backend/app/services/execution_service.py`）：域名购买、DNS 解析和旧版多维表格 DNS 审批卡片发送后保存 `message_id`；审批通过会先回写为“已批准，正在执行”，拒绝会回写为“已拒绝”，执行完成/失败/异步注册待确认会继续更新同一张原卡片并移除操作按钮。
- **飞书卡片 200341 超时治理**（`backend/app/api/v1/feishu.py`）：按飞书官方 3 秒回调要求，将超管授权、文档按钮审批、旧版 DNS 审批和自主注册表单统一改为“回调内只做参数解析并立即返回 toast，数据库校验、服务商调用、卡片更新和通知全部后台处理”，避免响应前调用更新卡片或执行慢操作导致客户端报 `200341`。
- **Cloudflare DNS 自检操作提示**（`backend/app/api/v1/domains.py`、`frontend/src/pages/Config.tsx`）：DNS账号自检失败时返回并展示 Cloudflare 后台权限配置步骤，方便直接按提示补齐 `DNS/Edit`、`Zone/Read` 和重定向规则权限。
- **Cloudflare DNS 账号自检准确性**（`backend/app/api/v1/domains.py`）：Cloudflare Account API Token 不再用 `/user/tokens/verify` 误判；自检新增 DNS 记录读取权限检查，能提前暴露只有 Zone 列表权限、无法读取/写入 DNS 记录的问题。
- **飞书文档 Vercel JSON 代码块解析**（`backend/app/services/feishu_doc_parser.py`）：支持 `vercelDomainsRecords` 代码块中的 `host/name/type/value` 结构，避免一键解析申请漏掉 Vercel 根域名与 `www` 记录。
- **飞书 DNS 审批默认账号兜底**（`backend/app/api/v1/feishu.py`）：飞书卡片未回传 `select_static.initial_option` 时，后端自动使用申请中的 `default_dns_account_id`，避免卡片已显示默认账号但点击批准仍提示“请选择 DNS 账号”。
- **Web 端业务流程写接口禁用**（`backend/app/api/v1/requests.py`）：`POST /requests`、审批、拒绝、更新、完成、失败等 Web 写接口统一返回 405，申请和审批主流程仅保留飞书入口，Web 后台用于查询、统计和配置。
- **后台注册商占位项隐藏**（`backend/app/api/v1/registrar.py`、`backend/app/adapters/registrar_factory.py`）：Namecheap/Enom 暂不实现真实适配，注册商列表和旧版列表接口临时隐藏这两个占位项，避免后台误配置；工厂当前支持项收口为 Cloudflare/GoDaddy。
- **交接文档待办收口**（`docs/项目交接文档.md`）：移除飞书文档侧 Bitable 配置和 Namecheap/Enom 适配器待办，保留当前实际待推进事项。
- **系统管理员申请详情只读**（`backend/app/api/v1/requests.py`、`frontend/src/pages/Requests/Detail.tsx`）：后台申请详情页待审批操作区仅域名专员和超级管理员可见；审批、拒绝、更新申请接口同步收紧为域名专员/超管角色，系统管理员只能查看申请信息。
- **DNS 审批默认账号选择**（`backend/app/api/v1/feishu.py`、`backend/app/api/v1/requests.py`）：提交 DNS 解析申请时优先读取域名列表中已绑定的 DNS 账号作为默认审批账号；飞书审批卡片默认选中该账号，后台申请详情页也会在待审批状态默认展示该账号，审核人员仍可下拉切换。
- **域名注册购买链路校正**（`backend/app/adapters/cloudflare.py`、`backend/app/adapters/godaddy.py`、`backend/app/services/execution_service.py`、`backend/app/api/v1/feishu.py`）：Cloudflare 注册改用官方 `/registrar/registrations` 接口与 `domain_name` 字段；GoDaddy 购买按审批选择传递注册年限并使用当前授权时间；注册执行前若查价/可用性检查失败会直接阻断，避免未确认价格时继续购买；GoDaddy 查价失败保留 `ACCESS_DENIED` 等原始错误信息展示到审批卡片。
- **Cloudflare 注册异步确认**（`backend/app/adapters/cloudflare.py`、`backend/app/services/execution_service.py`）：注册请求改为 `Prefer: respond-async`；若 Cloudflare 立即返回最终结果则直接发送最终卡片，若仍在处理则先发送“域名注册已提交/待确认”卡片，并由后台轮询 `registration-status` 反查注册资源后再次发送最终结果卡片；请求超时时不再直接判失败，避免 Cloudflare 已扣费/已注册但系统误报失败或触发重复购买。
- **域名页 DNS 操作**（`frontend/src/pages/Domains/index.tsx`、`frontend/src/pages/Domains/Detail.tsx`）：域名列表 DNS 按钮改为跳转详情页 DNS 区域，避免 `/dns` 未配置路由导致 404；详情页“查看 DNS 记录”按钮接入 `/api/v1/dns/domain/{domain_id}` 并展示记录列表。
- **域名购买报价原始原因展示**（`backend/app/api/v1/feishu.py`）：注册商返回域名不可注册时，飞书审批卡片报价保留原始 `message`（如 `domain_unavailable`），方便审核人员快速定位问题。
- **飞书文档主域名识别**（`backend/app/services/feishu_doc_parser.py`）：支持 `2、域名` 下一行填写主域名的文档格式，避免新需求文档提示“未能从文档中解析出主域名”。
- **飞书文档 Clerk JSON 代码块解析**（`backend/app/services/feishu_doc_parser.py`）：兼容 `domainsRecords` 代码块中的 `host/type/value` 结构，和旧版表格、主机名/类型/目标值格式一起自动解析并去重。
- **后端域名默认解析目标**（`backend/app/config.py`、`backend/.env.example`）：`backend_dns` 文档解析生成的后端接口域名 A 记录默认解析到 `54.89.199.228`。
- **申请失败/拒绝日志可见**（`backend/app/services/execution_service.py`、`backend/app/schemas/request.py`、`frontend/src/pages/Requests/Detail.tsx`）：执行失败时从 DNS 单条记录中提取失败摘要写入申请与审计日志，后台申请详情展示失败日志和执行明细；后台拒绝申请的拒绝理由改为可选，填写后继续记录到申请详情。
- **后台拒绝理由入口**（`frontend/src/pages/Requests/Detail.tsx`）：后台申请详情页待审批区域直接展示“拒绝理由（可选）”输入框，拒绝按钮与输入框同屏显示，不再隐藏到弹窗中。
- **失败飞书卡片原因展示**（`backend/app/services/execution_service.py`）：申请执行失败时，发送给申请人和审批人的飞书结果卡片统一展示失败原因，DNS 失败会显示单条记录失败摘要。
- **Cloudflare 原始错误保留**（`backend/app/adapters/cloudflare.py`）：Cloudflare 重定向规则接口失败时保留原始 `errors` 内容，便于根据官方错误码和消息排查权限或接口问题。
- **Cloudflare 通配符重定向格式**（`backend/app/adapters/cloudflare.py`）：Single Redirect 规则改为通配符模式，生成 `https://www.domain/*` → `https://domain/${1}`，并保留查询字符串，和 Cloudflare 控制台截图配置保持一致。
- **后台申请审批 DNS账号推断**（`backend/app/api/v1/requests.py`、`backend/app/services/execution_service.py`）：后台 `/requests` 页面批准 DNS 申请时，若未显式选择 DNS账号，会按本地域名绑定、同域名历史成功申请、当前用户默认 DNS账号自动补齐；DNS 执行成功后回填域名与 DNS账号绑定，避免后台审批执行时报“未配置DNS解析账号或解析商”。
- **超管审批卡片超时**（`backend/app/api/v1/feishu.py`）：账号配置/用户管理等超管审批卡片点击授权或拒绝后先快速响应飞书，再后台执行写库与结果通知，避免卡片弹出 `200341` 超时错误。
- **飞书卡片审批超时**（`backend/app/api/v1/feishu.py`）：文档按钮/DNS 审批卡片点击批准后先在 3 秒内返回交互响应，再由后台线程执行域名购买或 DNS 解析，避免执行已成功但飞书客户端弹出 `200341` 超时错误。
- **域名列表与 DNS 账号表单**（`backend/app/api/v1/domains.py`、`backend/app/schemas/domain.py`、`frontend/src/pages/Domains/index.tsx`、`frontend/src/pages/Config.tsx`）：域名列表新增所属 DNS 账号展示；DNS账号新增/编辑表单按 Cloudflare/DNSPod 显示 Token、Account ID、Secret ID 等对应字段说明。
- **超管审批结果通知时间字段**（`backend/app/services/user_confirmation_service.py`）：修复超管审核账号/默认配置申请后结果通知误读 `approved_at` 导致飞书卡片提示处理失败的问题，改为使用确认模型实际字段 `confirmed_at`。
- **飞书文档链接兼容**（`backend/app/services/feishu_doc_parser.py`）：`doc_url` 解析支持直接 token、未编码/多次编码链接、Markdown 链接、嵌套链接以及飞书 Wiki 链接；Wiki 链接会先通过 Wiki 节点接口解析真实 docx token。
- **用户管理卡片专员显示**（`backend/app/services/user_confirmation_service.py`）：用户管理授权申请、审批结果、目标用户变更通知中的“归属专员”由数字 ID 改为专员姓名显示。
- **卡片样式一致性**（`backend/app/api/v1/feishu.py`、`backend/app/services/feishu_service.py`、`backend/app/services/user_confirmation_service.py`）：DNS 文档审批、旧版 DNS 审批、超管确认卡片统一为“批准单独一行、拒绝按钮在左、拒绝理由输入框在右”的表单布局；超管结果卡片补充处理时间。
- **审批结果通知卡片化**（`backend/app/api/v1/feishu.py`、`backend/app/services/execution_service.py`）：文档按钮申请拒绝、通过完成、执行失败通知改为飞书卡片展示，并统一显示处理时间。
- **飞书审批卡片表单渲染**（`backend/app/api/v1/feishu.py`、`backend/app/services/user_confirmation_service.py`）：按飞书 JSON 1.0 表单容器规范，将注册服务商/DNS账号下拉、拒绝理由输入框与提交按钮放入 `form`，并修正 `select_static.initial_option` 为文本值，避免控件被过滤或卡片 JSON 解析失败。
- **域名购买报价可见性**（`backend/app/api/v1/feishu.py`）：购买域名审批卡片正文新增完整“服务商报价”列表；注册服务商下拉改为“注册商 | 特征账号 | 价格/状态”，避免长账号占据主要空间。
- **域名购买卡片操作布局**（`backend/app/api/v1/feishu.py`）：移除默认选择说明；批准并执行按钮单独一行，拒绝按钮在左、拒绝理由输入框在右同一行展示。
- **拒绝理由输入框宽度**（`backend/app/api/v1/feishu.py`）：修正拒绝行列宽配置，拒绝按钮保持自适应宽度，拒绝理由输入框占据剩余空间，避免移动端被压缩成窄框。
- **域名购买审批卡片展示优化**（`backend/app/api/v1/feishu.py`）：卡片正文不再显示“默认注册服务商/默认预估价格/服务商报价列表”，改为仅展示“注册服务商”和“预估价格”说明；注册服务商下拉项展示对应预估价，审核人切换选择时选中项同步体现价格。
- **飞书文档按钮幂等重发**（`backend/app/api/v1/feishu.py`、`backend/app/services/request_service.py`）：域名购买已有待审批申请时不再返回 409，而是刷新报价并重新发送审批卡；已批准/已完成的同域名购买申请会直接返回已处理，避免重复购买。
- **审核卡片申请时间**（`backend/app/api/v1/feishu.py`、`backend/app/services/feishu_service.py`）：域名购买、DNS 解析、旧版确认页/多维表格审批卡片均展示申请时间；重发响应只返回飞书发送状态与消息 ID，避免响应内容过长。
- **注册商 API 超时保护**（`backend/app/adapters/cloudflare.py`、`backend/app/adapters/godaddy.py`）：Cloudflare/GoDaddy 查价与注册相关 HTTP 请求增加 4 秒超时，避免飞书文档按钮提交时被外部服务慢响应拖到客户端超时。
- **飞书按钮参数兼容**（`backend/app/api/v1/feishu.py`、`backend/app/services/user_service.py`）：`POST /api/v1/feishu/doc-button/submit` 兼容飞书多维表格以 Query 参数提交；`applicant_feishu_id` 支持传公司内唯一姓名，后端优先按姓名精确匹配，匹配不到再按飞书 ID 匹配。
- **Cloudflare 注册商查价接口**（`backend/app/adapters/cloudflare.py`）：更新为官方 `domain-check` 接口，解析 `pricing.registration_cost` 作为注册价格。
- **默认配置确认执行**（`backend/app/services/user_confirmation_service.py`）：补齐 `SET_DEFAULT_CONFIG` 审批通过后的落库逻辑；新增注册账号勾选“设为默认”时，审批通过后会写入归属专员默认注册账号。
- **DNS 执行保护**（`backend/app/services/execution_service.py`）：对暂不支持的 DNS 记录类型提前标记失败，避免将 `REDIRECT_301` 等非标准 DNS 类型直接发送到解析服务商 API。

---

## [1.3.6] — 2026-06-01

### 修复
- **审批路由权限守卫**（`backend/app/api/v1/requests.py`）：`PUT /requests/{id}` 误用 `require_manage_users`，`domain_spec` 角色（`can_approve_request=True` 但 `can_manage_users=False`）实际被拦截无法更新申请。改为 `require_approve_request`，与同文件其余审批路由一致。

### 新增
- **域名到期飞书通知**（`backend/app/tasks/scheduler.py`）：`check_expiring_domains()` 原 TODO 补全。现在按优先级发送飞书卡片：优先通知域名归属专员；7天内到期或域名无主时同步通知超管作为兜底。调用现有 `FeishuService.send_domain_alert_card()`，失败只记 warning 不阻断其余域名处理。

---

## [1.3.5] — 2026-06-01

### 运维
- **`deploy.sh` 代理回退机制**：`git pull` 直连失败时自动读取服务器 `/root/.git-proxy-url` 通过代理重试，解决国内服务器无法稳定访问 GitHub 的问题；代理仅对 git 生效，不修改系统全局网络配置

### 文档
- **交接文档审查修正**（`docs/项目交接文档.md`）：修正10处错误与遗漏
  - `DEVELOPMENT.md`：环境变量名 `SECRET_KEY` 更正为 `JWT_SECRET_KEY`（错误变量名导致认证失败）
  - `DEVELOPMENT.md`：为"直接在服务器改代码"方案加安全警告，说明其为生产操作
  - 部署命令由旧式 `docker-compose` 统一更正为 V2 格式 `docker compose`
  - 补入飞书 Webhook 安全字段 `FEISHU_VERIFICATION_TOKEN`、`FEISHU_ENCRYPT_KEY`（遗漏会导致验签失效）
  - `CLOUDFLARE_API_TOKEN` 由"必填"更正为"可选"
  - 补充首次部署超管初始化流程（`init_db.py` + `SUPER_ADMIN_FEISHU_USER_ID`）
  - 补充 `manage_users.py` 无法创建 `super_admin` 的说明
  - 二级目录部署文档路径修正至 `docs/archive/`
  - `arch.md` 引用加历史文档免责说明；`docs/` 文件计数由 17 更正为 24；模型数由 9 更正为 10
  - `arch.md` 顶部添加偏差速查表（API 前缀 `/api/...` 与实际 `/api/v1/...` 的差异、权限示例代码的错误）
  - 联系方式由空占位符填入实际维护者（张立坤，飞书）

### 清理
- 删除 `backend/app/database.py`：项目初期遗留的旧版 SQLAlchemy 初始化文件，已全面迁移至 `app/core/database`，无任何引用
- 删除 `services/workflow.py`：根目录下的旧版工作流引擎，仍使用早期废弃的 `from database import` 路径，无任何引用

---

## [1.3.4] — 2026-05-31

### 安全/权限
- **域名专员数据隔离**：全面落实"每位专员只能看自己的数据"原则，修复以下越权缺口：
  - `GET /domains/{id}`：domain_spec 访问他人域名返回 403（原无校验）
  - `GET /domains/expiring/list`：domain_spec 只返回自己名下的到期域名（原返回全部）
  - `GET /requests`：domain_spec 只返回自己及其归属业务用户的申请（原返回全部）
  - `GET /requests/stats`：domain_spec 只统计自己归属范围的申请（原统计全局）
  - `GET /requests/{id}`：domain_spec 访问不属于自己范围的申请返回 403（原无校验）
  - `GET /dns/records`：domain_spec 只返回自己域名的 DNS 记录（原返回全部）
  - `GET /dns/records/{id}`：domain_spec 访问他人域名的 DNS 记录返回 403（原无校验）
  - `GET /dns/domain/{id}`：domain_spec 访问他人域名的 DNS 记录返回 403（原无校验）
- **SSL 证书接口权限收紧**：`GET /ssl/certificates`、`POST /ssl/alerts`、`GET /ssl/health` 由任意登录用户可访问改为 admin/super_admin 专属（这些接口读取宿主机服务器证书，与业务域名无关）

### 技术
- `DomainService.get_expiring_domains()` 新增 `owner_id` 参数，domain_spec 视角只查自己名下域名
- `RequestService.get_requests()`、`get_request_count()` 新增 `requester_ids: List[int]` 参数，用于 domain_spec 多用户范围过滤
- `RequestService.get_stats()` 新增 `requester_ids` 参数，支持 domain_spec 作用域统计
- `DnsService.get_records()`、`get_record_count()` 新增 `domain_ids: List[int]` 参数，用于 domain_spec 多域名范围过滤
- `requests.py` 新增工具函数 `_get_specialist_scope_ids()` 封装"专员 + 归属业务用户 ID"查询逻辑

---

## [1.3.3] — 2026-05-31

### 新增
- **默认配置 per-user 化**：`SystemDefaults` 表由单行全局设计改为每位专员一行，每人维护独立的注册商/DNS/账号偏好
- 超管在「默认配置」页面可查看全体专员的当前默认配置（表格形式），并可逐行点击「编辑」替该专员设置默认值
- domain_spec 仍看到自己的默认配置表单，账号下拉只展示自己名下的账号
- 超管编辑弹窗中的注册账号/DNS 账号下拉按该专员 `owner_id` 过滤，不会混入其他人的账号

### 技术
- `backend/app/models/system.py`：`SystemDefaults` 添加 `user_id` FK + `UniqueConstraint`，支持 per-user 唯一行
- `backend/scripts/init_db.py`：新增迁移步骤（PRAGMA table_info 检测 → ALTER TABLE ADD COLUMN → 清理旧全局行 → CREATE UNIQUE INDEX IF NOT EXISTS）
- `backend/app/api/v1/config.py`：新增 `GET /config/defaults/all`（超管专属，返回所有专员+其默认配置数组）、`PUT /config/defaults/{uid}`（超管替他人设置，飞书确认）
- 所有默认配置变更走 `ConfirmationOperationType.SET_DEFAULT_CONFIG` 飞书确认通道，返回 `pending_approval`

---

## [1.3.2] — 2026-05-31

### 新增
- **账号归属权限模型**：`RegAccount` / `DnsAccount` 现在严格归属于创建该账号的专员（`owner_id`），只有账号归属人和超管可见、可管理
- 账号列表/详情响应新增 `owner_name` 字段（后端 JOIN 注入，前端无需二次请求）
- `POST /domains/accounts/reg` 和 `POST /domains/accounts/dns` 新增 `target_owner_id` 字段：super_admin 新建时可在 Web 端下拉选择归属专员（domain_spec 或自身），domain_spec 创建时忽略此字段、自动归属自己
- 账号列表前端增加"归属专员"列（仅超管可见）
- 新建账号弹窗对超管显示"归属专员"下拉列表（含全部 domain_spec 及 super_admin 用户）

### 修复
- `GET /domains/accounts/reg/{id}` 和 `GET /domains/accounts/dns/{id}` 鉴权由 `get_current_active_user`（任意登录用户）改为 `require_view_accounts`，并增加 domain_spec 归属校验（访问他人账号返回 403）
- 前端账号增删改弹窗不再显示"操作成功"，改为统一展示后端 `pending_approval` 消息，避免误导用户认为操作已立即生效
- 前端编辑/删除按钮对 domain_spec 按 `owner_id === currentUserId` 受限，非归属账号显示"无权操作"而非隐藏（与后端鉴权一致）

### 规范
- `POST /domains/accounts/reg` 和 `POST /domains/accounts/dns` 移除创建流程中的死代码（`_make_confirmation` 返回后的不可达语句）

---

## [1.3.1] — 2026-05-31

### 修复
- 服务商管理页面空列表（API URL 错误 + 响应格式不匹配 + 数据库未种子 + 重复 router 挂载，共 4 层根因）
- 新增注册商/DNS服务商完整增删改查 UI，含超管确认提示

### 规范
- 新增 `CLAUDE.md`：固化权限模型、API 设计、数据库变更、安全红线等强制约束（AI 辅助开发每次自动加载）
- `docs/DEVELOPMENT.md §10` 新增人工开发自查清单

---

## [1.3.0] — 2026-05-31

### 新增
- 飞书文档（Bitable）集成：业务同事通过飞书文档按钮提交 DNS/注册申请
- 用户扫码注册流程：新用户扫码后由超级管理员飞书确认，支持冷启动直通
- 审批结果双向通知：审批/拒绝后分别通知专员（含执行详情）和业务同事（含结果摘要）
- 飞书确认卡片支持"显示详情"展开折叠

### 修复
- 修复飞书 OAuth 回调在注册场景下跳转逻辑
- 修复 DNS 执行幂等判断（记录存在且值一致时正确跳过）
- 修复超管确认卡片路由前缀 `/dm/` 缺失问题

### 文档
- 整理项目文档体系：11 份过时/误导性文档归入 `docs/archive/`
- 新增 `docs/DEVELOPMENT.md`（本地开发环境搭建指南）
- 新增 `docs/CHANGELOG.md`（本文件）
- 修订 `README.md`：角色表补全 super_admin、技术栈更正为 Docker Compose、注册商列表修正
- `REGISTRAR_CONFIG_GUIDE.md §7.4` 新增各注册商最小权限速查表
- `SECURITY_GUIDE.md` 修复重复 §5 编号
- `feishu-doc-integration.md` 修复重复 §8 编号

---

## [1.2.0] — 2026-05-（早期）

### 新增
- 飞书机器人 Webhook 集成（交互卡片审批）
- 超级管理员（super_admin）角色及飞书确认机制
- Docker Compose 容器化部署（取代 Systemd + Gunicorn 方案）
- 服务器迁移至 Git 检出管理（`/opt/domain-manager`）

### 修复
- 解决 Nginx 子路径 `/dm/` 下前端路由 404 问题
- 修复后端 API 路由前缀与 Nginx 配置不一致

---

## [1.1.0] — 2026 年早期

### 新增
- GoDaddy 注册商适配器
- DNS 解析管理（A/AAAA/CNAME/MX/TXT/SRV/NS）
- 审批流程（提交→审批→执行）
- 审计日志系统

---

## [1.0.0] — 项目初始版本

### 新增
- 飞书 OAuth 扫码登录 + JWT 认证
- 多角色权限控制（business / domain_spec / admin）
- 域名管理（增删改查、状态跟踪）
- Cloudflare 注册商适配器
- 定时任务（域名到期检查、状态同步）
- React + TypeScript 前端（仪表盘、域名管理、申请管理页面）

