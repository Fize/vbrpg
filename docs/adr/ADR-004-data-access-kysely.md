# ADR-004：使用 Kysely 作为 PostgreSQL 查询构建器

- 状态：Accepted
- 日期：2026-08-23
- 范围：`apps/platform/src/server/db` 与 repository 实现

## 背景

平台需要显式 SQL、可审计迁移、事务、行锁和 `SKIP LOCKED`。首版不需要通过 ORM 隐藏 PostgreSQL 的并发语义。

## 决策

新 TypeScript 数据访问层使用 Kysely，并以纯 SQL 迁移文件作为数据库结构的审核来源。repository 接口只暴露业务需要的操作，不提供无约束的通用查询。复杂锁语句（`FOR UPDATE SKIP LOCKED`）直接在迁移与查询里表达。

2026-10-15 更新（ADR-008）：租户上下文参数已从仓储接口移除。

## 后果

- Kysely 类型只存在于 `src/server/db`，不进入 `src/shared` 的契约，也不进入 `src/server/game` 的内核。
- 数据库迁移需要同时提供升级和回滚说明，并在 PostgreSQL 上验证。
- 不复用旧 SQLAlchemy model，也不迁移旧数据（greenfield）。
