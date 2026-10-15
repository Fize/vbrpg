# VBRPG 游戏平台

多人桌游平台：真人与 AI 席位同桌。**游戏规则写成 TypeScript 模块**（`apps/platform/src/server/games/<slug>.ts`），平台只管承载对局——身份、存储、投影、记录与调度，不解释任何游戏规则。

## 现状（截至 2026-10-15）

已交付：

- **账号与会话**：管理员建号/重置/删除、不透明会话（HttpOnly Cookie + 滑动/绝对过期）、CSRF、限流、审计；用户可自行修改密码（修改后撤销其他会话）。
- **模型目录**：Provider / Model 的增删改与连接测试（含 SSRF 防护），API Key 用 AES-256-GCM 加密存列内，任何接口都不回读密文。
- **中立内核**：`GameModule` 接口 + `GameRegistry` + `createBaseState` + `projectPlayerView`（三档投影，fail-closed）+ `EngineError`/`TransitionResult`。
- **数据底座**：8 张表——账号 2、模型目录 2、对局 3（`game_instances`/`game_participants`/`game_events`）、审计 1。

未实现：对局 HTTP 入口、worker 的实例扫描、第一个游戏模块、AI 席位、任何对局界面。缺口清单与后续计划见 `docs/platform-migration-plan.md` §8。

## 结构

```text
apps/platform/
  src/shared/     # 契约：Zod schema + 类型（浏览器安全，不许 import node 内建）
  src/server/     # Fastify 路由、鉴权、存储、worker、游戏内核
    game/         # 中立内核：GameModule、注册表、投影
    db/           # Kysely 类型、仓储、迁移读取
    runtime/      # 凭据加密、错误形状
  src/browser/    # Vue 3 控制台（构建成静态资源，由同一进程同源提供）
  migrations/     # SQL 迁移（0001 账号与模型目录、0002 对局运行时）
  scripts/        # migrate / bootstrap-admin / db-integration / provider check
  e2e/            # Playwright
```

一个镜像两种角色：`node dist/server/main.js --role=api|worker|both`。

## 快速开始

```bash
pnpm install
docker compose -f docker-compose.platform.yml up -d platform-postgres
export DATABASE_URL="postgres://vbrpg:vbrpgpassword@localhost:5433/vbrpg_platform"
export PLATFORM_CREDENTIAL_KEY="$(openssl rand -base64 32)"   # 生产必填

pnpm migrate
pnpm bootstrap-admin -- --username admin --password 'ChangeMe-123456'

pnpm dev          # api + 静态控制台（3000）
pnpm dev:worker   # worker 角色
pnpm dev:web      # 前端热更新（5173，代理 /v1 到 3000）
```

## 验证

```bash
pnpm build        # tsc + vite build
pnpm typecheck    # shared / server / browser 三个 project
pnpm test         # 单元与契约测试
pnpm test:db      # 真实 PostgreSQL 集成测试（需要 DATABASE_URL）
pnpm test:e2e     # Playwright（需要 E2E_DATABASE_URL 与 E2E_CREDENTIAL_KEY，且该库已迁移并 bootstrap-admin）
```

CI 里这些都跑：构建、类型检查、单测、真实 PostgreSQL 集成、迁移与回滚、Playwright。健康检查只有 `GET /health`。


## 文档

| 文档 | 内容 |
| --- | --- |
| `docs/platform-migration-plan.md` | 现状与工作计划（§8，M1–M5）、发布门槛（§10）、决策日志（§16，按轮次） |
| `docs/adr/` | 架构决策记录（001 起，008/009/010 是最近的收敛） |
| `docs/mvp-scope.md` | MVP 范围与下一步 |
| `docs/operations/phase1-platform.md` | 运维手册：环境变量、迁移、回滚、排障 |
| `docs/api/phase1-openapi.yaml` | 控制面 API 契约 |
| `docs/design/`、`docs/security/` | 认证与凭据的安全设计、威胁模型 |

## 旧系统

仓库根的 `backend/`（Python/FastAPI + Socket.IO）与 `frontend/`（Vue 2）是旧实现，**只作领域参考**：不迁移它的数据、不复刻它的接口、不维护它的运行契约。新平台是 greenfield，`apps/platform` 是唯一在维护的代码。
