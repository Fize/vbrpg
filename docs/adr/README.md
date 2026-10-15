# VBRPG 迁移期架构决策记录

这些 ADR 只约束迁移后的 TypeScript 平台，不改变旧 Python 服务的当前运行契约。

| 编号 | 决策 | 状态 |
| --- | --- | --- |
| [ADR-001](./ADR-001-postgresql-production.md) | 生产环境只支持 PostgreSQL | Accepted |
| [ADR-002](./ADR-002-runtime-boundary.md) | 通过 `GameRuntime` 隔离执行器 | Accepted |
| [ADR-003](./ADR-003-contract-validation-zod.md) | 使用 Zod 作为共享契约的运行时校验工具 | Accepted |
| [ADR-004](./ADR-004-data-access-kysely.md) | 使用 Kysely 作为 PostgreSQL 查询构建器 | Accepted |
| [ADR-005](./ADR-005-resource-storage.md) | Beta 首版小型二进制资源使用 PostgreSQL `bytea` | Accepted |
| [ADR-006](./ADR-006-agent-session.md) | agent 会话是事件流的确定性派生（每席位一个 agent） | Accepted |

LangGraph JS 是否作为第一版执行器仍需通过 Phase 0 技术验证；该未决项不会泄漏到平台契约或数据库模型中。
