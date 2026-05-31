# CHANGELOG

本文档记录域名管家的主要功能变更和修复历史。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

（下次发版前的变更在此追加）

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
