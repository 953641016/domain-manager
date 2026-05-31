# 域名管家 — AI 辅助开发规范（CLAUDE.md）

> 本文件由 Claude Code 在每次对话开始时自动加载，作为**强制性项目约束**。
> 人工开发者同样应当遵守。违反下列规则的 PR 不应合并。

---

## 1. 权限模型（不可绕过）

### 角色层级

| 层级 | 角色代码 | 中文名 | 说明 |
|------|----------|--------|------|
| 0 | `business` | 业务用户 | 只能提交申请，不能直接操作 |
| 1 | `domain_spec` | 域名专员 | 可查看/管理域名，不能触碰服务商/用户 |
| 2 | `admin` | 系统管理员 | 可管理用户（超管除外），不能直接写服务商配置 |
| 3 | `super_admin` | 超级管理员 | 全部权限，**关键操作需飞书二次确认** |

### 强制规则

1. **超管飞书确认不可省略**：凡涉及注册商账号、DNS 服务商账号、用户角色修改（升级为 admin/super_admin）、系统关键配置变更的操作，后端必须调用 `_make_provider_confirmation()` 或等价机制，向超管发送飞书卡片，等待确认后才执行。**禁止**直接写库绕过此流程。
2. **前端对 `pending_approval` 的处理**：后端返回 `{status: "pending_approval", message: "..."}` 时，前端必须向用户展示"已提交超管确认"的提示，**不能**假设操作已完成。
3. **新增权限字段**：在 `app/models/permission.py` 的 `ROLE_PERMISSIONS` 中添加新权限时，必须明确每个角色是否有该权限（不得省略低权限角色的声明）。
4. **API 路由鉴权**：每个写操作路由都必须带 `dependencies=[Depends(require_xxx)]` 装饰器，禁止裸路由写数据库。

---

## 2. API 设计规范

### URL 规则

```
GET    /api/v1/{resource}s           # 列表（支持 ?enabled_only=false 等查询参数）
POST   /api/v1/{resource}s           # 创建
GET    /api/v1/{resource}s/{id}      # 详情
PUT    /api/v1/{resource}s/{id}      # 更新（全量或部分字段）
DELETE /api/v1/{resource}s/{id}      # 删除
```

### 响应格式

- **列表接口**：直接返回 JSON 数组 `[...]`，不要包裹成 `{items: [...]}`（历史遗留的 `/registrar/list` 返回 `{registrars: [...]}` 是错误示范，新接口不得复制）。
- **单条操作成功**：返回操作后的完整对象，HTTP 200/201。
- **需要超管确认**：返回 `{status: "pending_approval", message: "已向超级管理员发送授权申请，审批通过后生效"}` HTTP 202。
- **错误**：`{detail: "错误原因"}` HTTP 4xx/5xx。

### 前端调用

- 所有 API 调用经由 `src/api/index.ts` 的 `api` Axios 实例，不得裸用 `fetch` 或新建 Axios 实例。
- 列表接口解析时用 `Array.isArray(res.data) ? res.data : []` 保护，避免格式变动导致崩溃。

---

## 3. 数据库变更规范

1. **新增模型**：在 `app/models/` 中新建文件，并在 `init_db.py` 的 `Base.metadata.create_all()` 之前确保 import。
2. **种子数据**：有枚举性质的基础数据（注册商类型、服务商类型、默认配置）必须在 `init_db.py` 中以幂等方式写入（先查后插，已存在则跳过）。
3. **禁止破坏性迁移**：不得 `DROP TABLE`、`ALTER COLUMN` 改类型/去非空。需要迁移时必须先评估生产数据影响，并在 `docs/CHANGELOG.md` 记录。
4. **字段命名**：统一使用 snake_case，布尔字段用 `is_xxx` 前缀，时间字段用 `_at` 后缀（`created_at`, `updated_at`, `expired_at`）。

---

## 4. 前端开发规范

### 组件结构

- 页面组件放 `src/pages/`，复用 UI 组件放 `src/components/`。
- 每个页面组件自己管理数据加载状态（`loading`, `error`），不依赖全局 store（当前项目未引入 Redux/Zustand）。

### CRUD 页面模板

新增支持增删改查的页面时，必须包含：
1. 列表展示（带 loading 骨架或转圈）
2. 新增/编辑共用一个 Modal（`editingXxx` 为 null 时是新增，否则是编辑）
3. 删除前 `window.confirm()` 二次确认
4. 对 `pending_approval` 响应的专用提示（不要用"操作成功"误导用户）
5. 错误时 `alert` 或 toast 告知失败原因

### 权限显示

- 按钮/操作的可见性遵循 `currentUser.role` 判断，`super_admin` 才能看到服务商管理的写操作入口。
- 判断逻辑统一放在组件内，不要在 CSS 用 `display:none` 隐藏（后端鉴权是真正的防线，前端只是体验）。

---

## 5. 提交与发布规范

### Commit 格式

```
<类型>: <简短描述（中文或英文均可，≤50字符）>

<可选正文：why，而不是 what>
```

| 类型 | 适用场景 |
|------|---------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 仅文档变更 |
| `refactor` | 重构（不改功能/修复） |
| `chore` | 构建、依赖、配置 |
| `test` | 测试 |

### 发版

- 每次发版前，在 `docs/CHANGELOG.md` 的 `[未发布]` 段落补充本次变更，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。
- 破坏性变更（删除 API、改权限模型）需提升 major 版本，并提前通知所有角色用户。

---

## 6. 安全红线

以下操作**任何情况下都不允许**，即使用户（或 AI）明确要求：

1. 在代码中硬编码 API Key、密码、飞书 Secret（应放 `.env`，`.env` 不进 git）
2. 关闭/绕过飞书超管确认机制（哪怕是"临时测试"）
3. 将 `ALLOWED_ORIGINS` 设为 `"*"` 推送到 main 分支
4. `git push --force` 到 main 分支
5. 在生产环境直接 `exec` SQL 或 `db.execute()` 原始 DDL

---

## 7. 对 AI 助手的特别说明

- **SSH 进生产机需用户逐次显式授权**：不得自动执行任何涉及 SSH 连接生产服务器的操作。
- **不得自动部署**：`git push` 后的生产部署（`deploy.sh`）必须由用户明确授权后才执行。
- **修改权限相关代码前**：必须先阅读 `app/models/permission.py` 和 `app/api/v1/` 中相关路由的依赖声明，确保理解现有权限意图，再修改。
- **新增 API 路由**：必须在路由文件顶部注释中说明：该路由需要哪个权限、是否需要超管确认、返回格式是数组还是对象。

---

*最后更新：2026-05-31 | 随项目演进持续维护*
