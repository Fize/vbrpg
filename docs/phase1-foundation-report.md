# Phase 1 TypeScript 工程基础进度

- 记录日期：2026-08-23
- 状态：骨架已建立，生产业务流量仍为零

## 已交付

- pnpm workspace：`apps/api`、`apps/worker`、`packages/contracts`、`packages/db`、`packages/workflow-engine`
- Fastify API：request id、结构化日志入口、统一错误响应、`/health`、`/ready`
- Worker：可启动的轮询骨架，未把内存作为权威状态
- Kysely PostgreSQL 客户端和 PostgreSQL 16 Compose 服务
- 首条控制面 SQL 迁移：`tenants`、`users`、`tenant_memberships`
- 数据库迁移命令：`pnpm run db:migrate:platform`
- Node 版本基线：`.nvmrc` 为 24，CI 与本地 workspace 使用 pnpm 11
- CI 工作流：构建、API/worker/共享包测试和真实 PostgreSQL 迁移

## 验证结果

- 平台 TypeScript 构建通过
- API 测试 3/3 通过
- Worker 测试 1/1 通过
- contracts 测试 5/5 通过
- NativeRuntime 测试 7/7 通过
- 旧狼人杀黄金轨迹 10 条全部通过

## 尚未完成

- API 尚未接入认证、租户上下文和数据库 readiness 查询。
- Worker 尚未实现 Outbox、scheduled jobs 和 pending commands 的 claim/lease。
- 首条迁移只建立控制面，游戏实例、事件、快照和任务表属于 Phase 2。
- CI 尚未包含真实 PostgreSQL repository 集成测试、lint、E2E 和安全测试。
- 旧前端仍是独立 legacy 路径，尚未迁移到 TypeScript API 契约。
- 本地 Compose 配置已通过解析校验；Docker PostgreSQL 容器内的 0001–0004 迁移和数据库集成测试已通过。CI 工作流同样会在 PostgreSQL service 上执行该迁移和测试。
