# ADR-008：单用户池，不设租户层

- 状态：Accepted
- 日期：2026-10-15
- 范围：数据模型、身份与授权、迁移文件

## 背景

平台从 Phase 1 起按"多租户 SaaS"建模：`tenants`、`tenant_memberships`、`tenant_secrets` 三张表，
每张业务表带 `tenant_id`，唯一键一律带租户前缀，12 张表开启 PostgreSQL RLS，仓储接口必须接收
租户上下文（`withTenantContext` + `SET LOCAL app.tenant_id`）。同期还保留了一条遗留 bearer 认证
路径（`AUTH_TOKEN_SECRET` + `x-tenant-id` + 租户角色 owner/admin/developer/player）。

支撑这一层的理由有三个：

1. 一套部署服务多个互不可见的组织（各自的用户池、模型凭据、计费）。
2. 旧数据切流：把老用户放进默认 `legacy` 租户，与新用户隔离。
3. 按租户授权游戏：`developer` 角色创建/测试/发布游戏版本，`owner` 管成员、密钥与计费。

## 决策

**删除租户层，平台是单一用户池。**

- 删表：`tenants`、`tenant_memberships`、`tenant_secrets`、`player_actions`、`outbox_events`。
- 删列与约束：所有表的 `tenant_id`、复合外键、复合唯一键；`providers.name` 改为全局唯一。
- 删 RLS：原 `0004_tenant_rls.sql` 及其策略。
- 删代码：`withTenantContext`、`platformContext`、`PLATFORM_TENANT_ID`、租户作用域仓储、worker 的按租户循环。
- 删遗留 bearer 认证路径：`server/auth.ts`、`routes/auth.ts`、`AUTH_TOKEN_SECRET`、`x-tenant-id`、
  `app.ts` 的鉴权 hook、`main.ts` 的 `sessionLookup`。平台会话（不透明 session + HttpOnly Cookie + CSRF）
  成为唯一认证路径。
- 删未使用的 `auth_sessions.refresh_token_hash`。
- 迁移文件重写为 `0001_accounts_and_models` 与 `0002_game_runtime` 两个（greenfield，不留兼容路径）。

**为什么连 `player_actions` 和 `outbox_events` 一起删**：前者与 `game_events.idempotency_key` 的幂等语义重叠，
独有价值只是保存客户端原文；后者的消费者是实时推送，而推送被 `docs/mvp-scope.md` 明确推迟，没有写入者与
消费者。

## 理由

第 2、3 条理由已经失效：旧数据切流随 greenfield 口径撤销（`P0-07`、`P4-05`、`P4-06`）；`developer`
角色的职责（作者/发布）随 DSL 撤除一并消失（主计划 §16 第六轮）。

第 1 条是商业决定而非技术必然，而当时的实现并不构成隔离：唯一租户是常量 `PLATFORM_TENANT_ID`，
`withTenantContext` 传的也是它，RLS 策略与应用过滤引用同一个值——等于自证。用户池本来就是全局的
（`users.username` 全局唯一，登录不选租户），所以当时的模型实际是"一个用户池 + 若干成员关系"，
却又让每个查询、每个唯一键、每张新表都背上一个恒定不变的 `tenant_id`。

同理，`player_actions` 与 `outbox_events` 是"设计的产物但从未被消费"：留着它们等于把未决决策
写进 schema。

## 后果

- schema 从 16 张表收敛到 11 张：账号 2、模型目录 2、对局 6、审计 1。所有唯一键改为以 `instance_id`
  或 `provider_id` 为前缀，跨对局撞号不可能发生。
- 每个查询少一个恒定参数；新表不必再考虑租户前缀与 RLS 策略。
- 攻击面缩小：少一条认证路径，少一套租户角色守卫。
- 迁移文件重写使已有本地/容器数据库必须重建（迁移名称已变，无兼容路径）。这是 greenfield 认可的代价。
- **反向代价**：若将来真要做多社群或 SaaS 隔离，需要重新引入这一层；库里有数据之后，改唯一键与
  加列的迁移成本会显著高于现在。做决定时把这条当成已知风险，而不是"以后再说"。
