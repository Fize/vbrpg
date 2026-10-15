# Phase 2 持久化底座进度

> 2026-10-15：本报告中的工作流 DSL / 运行时相关结论已随该路线撤除（见主计划 §16 第六轮）；其余内容为当时的实现记录。


- 记录日期：2026-08-24
- 状态：P2-01、P2-02 已完成 API 边界原型；P2-03、P2-04、P2-07 已完成基础实现，数据库会话/RLS/安全攻击测试尚未完成

## 已交付

- `0002_game_runtime.sql`：游戏、版本、工作流定义、实例、参与者、事件、快照、玩家动作、Outbox、待处理命令、定时任务、租户密钥、AI 用量和审计日志表。
- `0003_auth_sessions.sql`：可撤销认证会话、刷新 token 哈希、过期时间和租户成员复合外键。
- `0004_tenant_rls.sql`：对租户资源启用 PostgreSQL RLS，策略读取事务内的 `app.tenant_id`。
- 所有领域资源都携带 `tenant_id`，跨表引用使用 `(tenant_id, id)` 复合外键；游戏 slug/code、实例事件序号/idempotency key、命令和定时任务键均有租户级唯一约束。
- `packages/db/src/types.ts` 已覆盖新表，可直接由 Kysely 推导查询和写入类型。
- `packages/db/src/repositories.ts` 已提供租户作用域的实例/快照读取、玩家动作幂等写入，以及 Outbox/command/job 的 `FOR UPDATE SKIP LOCKED` claim、lease 和释放接口。
- `.github/workflows/platform-ci.yml` 已纳入版本控制例外规则，CI 会在 PostgreSQL service 上执行迁移。
- API 已支持 HMAC 签名访问令牌、Bearer 认证、租户请求头匹配和 Owner/Admin/Developer/Player 基础 RBAC 守卫。
- DB 层已提供有效会话和租户 membership 查询。
- API server 已在配置数据库连接时接入真实 session/membership 查询，并通过事务内 `SET LOCAL` 建立租户上下文。
- Worker 已提供按租户扫描、command/job/outbox claim、成功完成和指数退避失败/死信处理器接口；具体 AI、计时器和广播 handler 尚未接入。

## 已验证

- `pnpm run build:platform` 通过。
- API 12/12、worker 1/1、contracts 5/5；NativeRuntime 7/7、DSL validator 3/3、旧狼人杀黄金轨迹 10/10 通过。
- Compose 文件解析通过。

## 当前阻塞与边界

- 本轮已启动本地 Docker PostgreSQL，真实迁移 0001–0004 和集成测试均通过；CI 也复用了同一迁移/测试路径。
- 邀请流程、刷新 token 接口和跨租户 REST/WebSocket/worker 攻击测试尚未完成。
- API 在配置 `DATABASE_URL` 时会用 `auth_sessions` 和实时 membership 覆盖 token 中的角色；无数据库配置的开发环境仍允许 token-only 测试模式，生产环境会拒绝该模式。
- RLS 已由临时非 owner 角色在真实 PostgreSQL 中验证：租户 A 可读取自己的实例，租户 B 读取同一实例返回 0 行。
- lease、重试退避和死信转移基础已具备，但实际业务 handler、事务性业务动作和广播仍属于后续工作。
- Worker 进程当前仍以空轮询启动，避免在没有真实业务 handler 时误消费任务；接入 handler 后才会启用数据库队列消费。
- CI 已增加 PostgreSQL 集成测试入口，覆盖认证会话、membership、租户作用域查询、`app.tenant_id` 事务上下文和非 owner RLS 隔离。

## 复核（2026-10-14）

- `packages/db` 单测 3/3；真实 PostgreSQL 集成路径仍在（`packages/db/scripts/integration.ts`、`apps/api/scripts/game-dispatch-integration.ts`）。
- 认证现状：平台会话认证已落地（`routes/platform-auth.ts` 的 `/v1/auth/login`、`/v1/auth/logout`、`/v1/auth/csrf`、`/v1/auth/password`、`/v1/me`，HttpOnly Cookie + CSRF），与 legacy HMAC bearer 线（`routes/auth.ts` → `/v1/tenant/me`）**并存**；生产环境未配置 session store 时返回 503 `AUTH_SESSION_STORE_NOT_CONFIGURED`。
- 刷新 token 仍未实现：`auth_sessions` 只保存 session 与 CSRF 哈希，无 refresh 端点，会话到期需重新登录。
- 邀请流程、跨租户 REST/WebSocket/worker 攻击测试仍未实现；跨租户隔离目前只有 RLS 数据库层验证。
- worker 空轮询的结论仍然成立：`apps/worker/src/server.ts` 以**无依赖**调用 `createWorker`，`pending_commands`/`scheduled_jobs`/`outbox_events` 实际不被消费。
