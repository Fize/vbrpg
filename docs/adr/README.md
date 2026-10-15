# VBRPG 迁移期架构决策记录

这些 ADR 只约束迁移后的 TypeScript 平台，不改变旧 Python 服务的当前运行契约。

| 编号 | 决策 | 状态 |
| --- | --- | --- |
| [ADR-001](./ADR-001-postgresql-production.md) | 生产环境只支持 PostgreSQL | Accepted |
| [ADR-003](./ADR-003-contract-validation-zod.md) | 使用 Zod 作为共享契约的运行时校验工具 | Accepted |
| [ADR-004](./ADR-004-data-access-kysely.md) | 使用 Kysely 作为 PostgreSQL 查询构建器 | Accepted |
| [ADR-005](./ADR-005-resource-storage.md) | Beta 首版小型二进制资源使用 PostgreSQL `bytea` | Accepted |
| [ADR-007](./ADR-007-single-package-one-image.md) | 单包、单镜像、两种角色 | Accepted |
| [ADR-008](./ADR-008-single-user-pool.md) | 单用户池：删除租户层与 RLS | Accepted |
| [ADR-009](./ADR-009-three-match-tables.md) | 对局只留三张表：不设队列与快照 | Accepted |

已撤除：ADR-002（执行器边界）与 ADR-006（agent 会话）随 2026-10-15 的 DSL 撤除一并下线——平台不再内置游戏 DSL 或编排运行时，游戏逻辑是代码化模块（见主计划 §4/§5 与 §16 第六轮）。

被推翻：ADR-008 推翻了主计划早期关于多租户与租户角色的设定，`tenants`/`tenant_memberships`/`tenant_secrets` 与 RLS 已删除，平台是单一用户池。
