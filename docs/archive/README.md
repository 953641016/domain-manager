# docs/archive — 历史存档

本目录存放已归档的文档。这些文档因**过时、误导性内容或被更好的文档取代**而不再作为活跃参考，但保留以备历史查阅。

> **⚠️ 请勿将本目录中的文档作为操作参考。**
> 所有现行操作文档位于 `docs/` 根目录。

---

## 存档文件清单

| 文件 | 归档原因 |
|------|---------|
| `deployment.md` | 已被 `服务器部署维护文档.md` 取代（Docker Compose 方式） |
| `server_deployment.md` | 同上；含明文 App Secret（历史遗留）|
| `subdirectory-deployment.md` | 同上 |
| `SECURITY_REVIEW.md` | 实现前的预审文档，将已实现功能标注为"❌ 未实现"，严重误导；整体安全评分 1/5 已完全过时 |
| `PROJECT_COMPLETION.md` | 将已完成的飞书集成列为"下一步"，文件路径描述错误 |
| `PROJECT_STRUCTURE.md` | 描述了不存在的目录结构（`adapters/namecheap.py` 等） |
| `FEISHU_INTEGRATION_GUIDE.md` | 代码示例有 Bug，Webhook URL 错误；已由 `feishu-ops-manual.md` 取代 |
| `feishu_setup_guide.md` | Webhook URL 错误；内容已被 `feishu-ops-manual.md` §1-2 覆盖 |
| `feishu-permission-config.md` | 角色名称已过时（缺 `super_admin`）；1000+ 行设计草稿；权限现由 `权限与流程设计.md` 定义 |
| `registrar-permission-config.md` | 核心内容（最小权限速查表）已并入 `REGISTRAR_CONFIG_GUIDE.md §7.4` |
| `ssl-certificate-management.md` | 理论性说明；实操命令已在 `服务器部署维护文档.md §6` |

---

## 当前权威文档（请转至 docs/ 根目录）

| 主题 | 权威文档 |
|------|---------|
| 服务器部署、运维、SSL | `docs/服务器部署维护文档.md` |
| 飞书平台配置、Webhook | `docs/feishu-ops-manual.md` |
| 角色权限、安全加固 | `docs/SECURITY_GUIDE.md` |
| 审批流、通知设计 | `docs/权限与流程设计.md` |
| 注册商 API Key 配置 | `docs/REGISTRAR_CONFIG_GUIDE.md` |
