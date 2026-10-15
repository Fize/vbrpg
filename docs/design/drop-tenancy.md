# 去掉多租户：单站、单用户池、只留三类表

> 状态：已完成（2026-10-15）。决策记录见 [ADR-008](../adr/ADR-008-single-user-pool.md)。
> 本文件保留为执行记录：删除不产生价值的租户层与未决的投递层，让库里只剩「账号与用户」「模型目录」「对局运行时」三类表。

## Goal

问题：当前 schema 有 16 张表，其中 5 张（`tenants`、`tenant_memberships`、`tenant_secrets`、`player_actions`、`outbox_events`）在当前产品形态下不产生价值：

- 租户永远是常量 `PLATFORM_TENANT_ID`（`platform-repositories.ts` 里 20+ 处硬编码），
  RLS 策略与应用过滤引用同一个值，等于自证；`tenants` 只有一行，唯一读取点是 bootstrap 的存在性校验。
- 支撑租户层的三条理由里两条已失效：旧数据切流随 greenfield 决定撤销；`tenant_memberships.role` 里的
  `developer`（游戏作者/发布）随 DSL 撤除一并消失。
- `tenant_secrets` 零使用点（provider 凭据存在 `providers` 自己的列里）；
  `player_actions` 与 `game_events.idempotency_key` 幂等语义重叠；
  `outbox_events` 没有写入者与消费者，实时推送本身被 `docs/mvp-scope.md` 明确推迟。
- 遗留 bearer 认证路径（`auth.ts`、`/v1/tenant/me`、`x-tenant-id`、`AUTH_TOKEN_SECRET`）只服务租户角色，
  与平台会话认证（opaque session + HttpOnly Cookie + CSRF）并行存在，是原型期残留。

期望终态：库里只剩账号表、模型目录表、对局运行时表；没有 `tenant_id`、没有 RLS、没有第二条认证路径；
`build` / `typecheck` / `test` / `test:db` / `test:e2e` 全绿。

## Approach

1. **迁移重写为两个**（greenfield、库中无数据，允许改写迁移历史）：
   - `0001_accounts_and_models.sql`：`users`、`auth_sessions`、`providers`、`provider_models`、`audit_logs`；
   - `0002_game_runtime.sql`：6 张对局表，全部去掉 `tenant_id`；
   - 删除原 `0004_tenant_rls.sql`；
   - 两个迁移各自带 `.down.sql` sidecar（`scripts/db-integration.ts` 会测"回滚一步再迁移"）。
   - **代价**：迁移名称变化，已有本地/容器库必须重建（drop volume 或 drop database）。
2. **删表**：`tenants`、`tenant_memberships`、`tenant_secrets`、`player_actions`、`outbox_events`。
3. **去 `tenant_id`**：复合外键降为单列外键；复合唯一键降为单列唯一
   （如 `game_events` 的 `(tenant_id, instance_id, sequence)` → `(instance_id, sequence)`）；
   `providers.name`、`provider_models` 的唯一键相应改为全局唯一。
4. **删遗留 bearer 认证路径**：`auth.ts`（210 行 JWT 风格 token + 租户角色）、`routes/auth.ts`
   （`/v1/tenant/me`、`/v1/tenant/management-check`）、`AUTH_TOKEN_SECRET` 配置项、`app.ts` 的鉴权 hook、
   `main.ts` 的 `sessionLookup` 接线、`x-tenant-id` 处理。平台会话成为唯一认证路径。
5. **仓储与 worker 简化**：删 `TenantContext`、`withTenantContext`、`platformContext`、
   `PLATFORM_TENANT_ID`、`listActiveTenantIds`、`getTenantMembership`、`recordPlayerAction`、
   `claimOutboxEvents`/`completeOutboxEvent`；worker 去掉按租户的循环，单趟处理队列。
   **保留**上一轮修的 `databaseNow` 时钟来源修复。
6. **顺带清理**：`auth_sessions.refresh_token_hash`（零使用的遗留列，刷新 token 未实现）。
7. **文档**：新增 ADR-008 记录本决策；主计划 §2.1 目标与 §6 数据模型改写；`docs/mvp-scope.md`、
   `docs/api/phase1-openapi.yaml`、`docs/operations/phase1-platform.md`、
   `docs/design/phase1-auth-provider-secure-design.md` 去掉租户表述。

不做的事：不引入替代的隔离机制（部署级隔离即自托管/独立数据库）；不为 `outbox_events` 补推送层
（推送方案未定，定下来再加表）；不迁移任何旧数据。

## Impact

| 文件 | 变更 |
| --- | --- |
| `apps/platform/migrations/0001_platform_control_plane.sql` | 重写为账号与模型目录（含原 0003/0005 的内容） |
| `apps/platform/migrations/0002_game_runtime.sql` | 去掉全部 `tenant_id`、复合外键与复合唯一键 |
| `apps/platform/migrations/0001_platform_control_plane.sql`、`0003_auth_sessions.sql`、`0004_tenant_rls.sql`、`0005_*`、`0005_*.down.sql` | 删除（内容并入 0001/0002） |
| `apps/platform/src/server/db/types.ts` | 删 5 张表的类型；去掉各表 `tenant_id`；删 `PLATFORM_TENANT_ID` |
| `apps/platform/src/server/db/repositories.ts` | 删租户上下文与 outbox/player_actions 函数；队列与实例函数去掉租户过滤 |
| `apps/platform/src/server/db/platform-repositories.ts` | 用户/会话/provider/model/审计查询去掉租户上下文 |
| `apps/platform/src/server/db/index.ts` | 同步导出面 |
| `apps/platform/src/server/auth.ts`、`routes/auth.ts` | 删除 |
| `apps/platform/src/server/app.ts`、`main.ts`、`config.ts` | 删鉴权 hook、sessionLookup、`AUTH_TOKEN_SECRET`、`x-tenant-id` |
| `apps/platform/src/server/worker.ts` | 去掉按租户循环与 outbox handler |
| `apps/platform/src/server/store.ts`、`platform-auth.ts`、`routes/platform-auth.ts`、`routes/platform-admin.ts` | 去租户参数 |
| `apps/platform/src/shared/domain.ts` | `actorRefSchema` 去掉 `tenantId` |
| 测试：`app.test.ts`、`auth.test.ts`、`worker.test.ts`、`platform-routes.test.ts`、`scripts/db-integration.ts` | 删租户相关用例，补回归 |
| `docs/adr/ADR-008-*.md`、`docs/adr/README.md`、主计划、`docs/mvp-scope.md` 等 | 决策与文档同步 |

## Tasks

- [x] T1 重写 `migrations/0001_accounts_and_models.sql` + `0001_accounts_and_models.down.sql`（users、auth_sessions、providers、provider_models、audit_logs，无 tenant_id、无 RLS）
- [x] T2 重写 `migrations/0002_game_runtime.sql` + `.down.sql`（8 张对局表，去 tenant_id、复合键降为单列）
- [x] T3 删除 `migrations/{0001_platform_control_plane,0003_auth_sessions,0004_tenant_rls,0005_phase1_auth_providers,0005_phase1_auth_providers.down}.sql`
- [x] T4 `db/types.ts`：删 5 张表类型、去各表 `tenant_id`、删 `PLATFORM_TENANT_ID`
- [x] T5 `db/repositories.ts`：删 `TenantContext`/`withTenantContext`/`recordPlayerAction`/outbox/`listActiveTenantIds`/`getTenantMembership`，队列函数去租户过滤，保留 `databaseNow`
- [x] T6 `db/platform-repositories.ts` + `db/index.ts`：去 `platformContext` 与租户参数，同步导出
- [x] T7 删 `server/auth.ts` 与 `routes/auth.ts`；`app.ts`/`main.ts`/`config.ts` 去鉴权 hook、`sessionLookup`、`AUTH_TOKEN_SECRET`、`x-tenant-id`
- [x] T8 `worker.ts`：单趟队列处理（commands + scheduled jobs），删租户循环与 outbox handler
- [x] T9 `store.ts`/`platform-auth.ts`/`routes/*`/`shared/domain.ts`：去租户参数与 `actorRef.tenantId`
- [x] T10 测试同步：删 `auth.test.ts` 与 `app.test.ts` 中的租户用例、更新 `worker.test.ts`、`scripts/db-integration.ts` 改测队列 claim/lease + 迁移回滚（去掉跨租户隔离用例）
- [x] T11 新增 `docs/adr/ADR-008-single-tenant.md` + 更新 `docs/adr/README.md`
- [x] T12 主计划 §2.1/§6 改写 + `docs/mvp-scope.md` + `docs/api/phase1-openapi.yaml` + `docs/operations/phase1-platform.md` + `docs/design/phase1-auth-provider-secure-design.md` 去租户表述

## 验收

1. `pnpm build && pnpm typecheck && pnpm test` 全绿。
2. 全新库：`migrate` → `test:db` → `migrate:down` 回滚一步 → 再 `migrate` 全部通过。
3. 实机：`--role=api` 起服务，`/health` 200、`/` 返回控制台、`/v1/nope` 返回统一 404、登录 → 改密 → 建 provider/model 全链路可用。
4. `pnpm test:e2e` 4 个场景通过。
5. `grep -ri tenant apps/platform/src apps/platform/migrations` 只剩必要的注释，无代码引用。

## 回滚

代码层 `git revert` 即可；数据库层重建本地库（迁移名称已变，无兼容路径，符合 greenfield 口径）。
