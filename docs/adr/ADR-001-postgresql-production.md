# ADR-001：生产环境只支持 PostgreSQL

- 状态：Accepted
- 日期：2026-08-23
- 范围：迁移后的 API、worker、数据库迁移和集成测试

## 背景

现有服务使用 SQLAlchemy，并且本地 Compose 仍以 MySQL 为主。迁移计划要求事件、快照、任务、Outbox、租户隔离和 RLS 进入同一个权威数据库。首版若同时支持 MySQL、PostgreSQL 和 SQLite，会把 JSON、锁、事务隔离和行级安全的差异带入每个业务路径。

## 决策

迁移后的生产部署和所有持久化集成测试只支持 PostgreSQL。SQLite 仅允许用于无数据库的纯引擎单元测试或轻量演示；旧 Python 服务继续按现有方式运行，直到切流完成。

新数据库设计使用 PostgreSQL 原生能力，包括 `jsonb`、事务行锁、`FOR UPDATE SKIP LOCKED` 和 Row-Level Security。应用层租户授权仍是第一道边界，RLS 作为纵深防御。

## 后果

- 新 Compose、CI 和运行手册必须提供同一主版本的 PostgreSQL。
- 所有锁、并发、迁移、RLS 和 worker 测试必须连接真实 PostgreSQL。
- 不再为新代码设计 MySQL 兼容分支；旧数据库迁移通过独立回填/切流工具处理。
- 若未来需要 MySQL，必须新增独立 ADR 和兼容性测试，不得隐式扩展本决策。
