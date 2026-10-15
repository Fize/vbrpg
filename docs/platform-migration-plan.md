# VBRPG 游戏平台迁移与发布计划

> 状态：提案 / 可执行基线
> 更新日期：2026-10-15
> 状态核验：2026-10-15 逐项对照代码、测试与提交核验任务状态；结论与下一步见 §16。
> 适用范围：将当前 Python + Vue 项目迁移为以 TypeScript 为主的游戏平台（游戏为代码化模块，非声明式 DSL）

> 当前执行模式：Greenfield 新项目。旧 Python/Vue 系统、数据迁移、兼容层、双轨切流、旧版本行为兼容和历史黄金轨迹不属于当前交付门槛；旧实现仅作为可选领域参考。后续验收以新 TypeScript 平台、PostgreSQL、中立运行时内核与代码化游戏模块为准（DSL 路线已于 2026-10-15 撤除，见 §16 第六轮）。

## 1. 执行摘要

游戏规则是一台**事件驱动、可持久化、可暂停和恢复的状态机**：玩家输入、计时器、随机事件与 AI 调用都是驱动它继续执行的事件或外部活动。规则本身写在 TypeScript 游戏模块里，平台不解释规则、只负责承载对局。

本计划采用以下结论：

1. 后端迁移到 TypeScript 是合理的，但应按领域边界重构，不能逐行翻译现有 Python 服务。
2. **游戏逻辑是代码，不是平台解释的 JSON**：一个游戏一个 TypeScript 模块（`apps/platform/src/server/games/<slug>.ts`），平台只提供对局底座与中立内核。原先的声明式 DSL 路线已于 2026-10-15 撤除，见 §16 第六轮。
3. 编排库（LangGraph JS 等）是游戏代码的内部选择，平台不依赖、也不暴露它们（见 §7）。
4. 生产环境只支持 PostgreSQL，避免第一版同时承担 MySQL、PostgreSQL、SQLite 三套语义差异。SQLite 只运行纯内核单元测试和轻量本地演示；所有集成测试与 CI 必须运行真实 PostgreSQL。
5. 对局在创建时固定它使用的代码版本；升级游戏代码不影响进行中的对局。
6. 所有权威状态都进入 PostgreSQL：事件、快照、待处理输入、定时任务、命令、审计。进程内存只允许作缓存，不能作为权威存储。
7. 首版由平台自己维护游戏代码，不提供作者上传代码或包的通道；第三方分发需要单独的沙箱与安全设计。

达到可邀请外部作者和玩家参与的 Beta，预计需要 **19～27 人周**；2 名全职工程师并行时约 **10～14 个日历周**，单人串行约 **5～7 个月**。该估算不含高级可视化编辑器、商业结算、移动客户端和任意代码插件沙箱。

## 2. 产品目标与非目标

### 2.1 Beta 目标

- 平台账号由管理员创建；用户登录后进入自己的对局列表。
- 平台内置的游戏可以被创建为对局、开始、并跑到结束（游戏代码在 `apps/platform/src/server/games/*` 维护）。
- 玩家可以加入对局，在断线、服务重启后继续。
- 一个对局可以同时包含真人和 AI 席位。
- 玩家只能看到自己有权看到的信息，且这一点由平台强制（投影 fail-closed），不依赖游戏代码自觉。
- 对局数据一律经过投影读取，隐藏信息不因接口扩张而泄漏。
- 每次状态变化可审计、可重放、可幂等处理。

### 2.2 Beta 非目标

- 不同时支持 PostgreSQL 和 MySQL 生产部署。
- 不提供作者上传代码、第三方 npm 包执行或沙箱插件能力。
- 不提供声明式游戏 DSL、草稿/发布生命周期与发布期静态校验（2026-10-15 撤除）。
- 不在首版完成 Steam 式商业市场、创作者分成和复杂支付结算。
- 不保证把进行中的旧 Python 对局无损迁移到新引擎；优先采用排空旧对局的切换方式。

## 3. 当前基线与主要问题

当前项目已经具备可复用的产品原型，包括 Vue 3 UI、Socket.IO 实时通信、房间流程、AI 玩家接入和一批测试。但它还不是多租户工作流平台：

- 当前后端是 Python/FastAPI/SQLAlchemy，并使用 LangChain；仓库中没有实际使用 LangGraph。
- 核心游戏行为集中在大型服务和 WebSocket 处理器中，迁移难点来自领域逻辑耦合，而不是 Python 语言本身。
- 对局服务和状态存在进程内映射，无法保证多实例部署、重启恢复和后台任务可靠性。
- 数据模型没有完整的 `tenant_id`、成员关系、租户角色和租户级唯一约束。
- 客户端可提交玩家标识；身份与租户上下文还没有成为服务端可信边界。
- 前端主要是 JavaScript/Vue SFC，尚未形成前后端共享 TypeScript 契约。
- 既有测试和工程工具存在基线债务：部分前端测试失败、ESLint 配置与版本不匹配、后端静态检查遗留较多、容器 Node 版本与当前 Vite 要求不一致，且缺少完整 CI 门禁。
- 现有文档对单人、多人、房间和游戏类型的描述有漂移，需要以新的领域术语统一。

这些问题决定了迁移必须先建立行为基线、持久化协议和可信身份边界，然后再迁移具体游戏。

## 4. 目标架构

```mermaid
flowchart LR
    Browser[Vue 3 + TypeScript] -->|REST| API[Fastify API]
    API --> Auth[身份与授权]
    API --> Games[游戏模块 apps/platform/src/server/games/*]
    Games --> Engine[中立内核：投影 / 重放 / 转换类型]
    API --> DB[(PostgreSQL)]
    Worker[TypeScript Worker] --> DB
    DB --> Outbox[Outbox / Scheduled Jobs]
    Outbox --> Worker
    Worker -->|按玩家投影广播| Browser
```

实际结构（2026-10-15 起）：**一个包、一个镜像、两种角色**。

```text
apps/platform/
  src/shared/          # 契约：Zod schema + 类型（浏览器安全，不许 import node 内建）
  src/server/          # 进程侧：Fastify 路由、鉴权、存储、worker 轮询、游戏内核
    game/              # 中立内核：GameModule 接口、注册表、投影、重放
    db/                # Kysely 类型、仓储、迁移读取
    runtime/           # 凭据加密、错误形状
  src/browser/         # Vue 3 控制台（构建成静态资源，由同一进程提供）
  migrations/          # SQL 迁移
  scripts/             # migrate / bootstrap-admin / db-integration / provider check
legacy/
  python-backend/      # 切换期保留；也可暂时保持当前 backend/ 位置
```

三种角色、同一个镜像：`--role=api`（HTTP + 静态资源）、`--role=worker`（队列消费者）、`--role=both`（本地开发）。
浏览器产物由 api 角色同源提供，因此不再需要 nginx、跨域配置或第二个服务。

推荐技术组合：

- Monorepo：pnpm workspace。
- Web：Vue 3 + TypeScript，逐个模块迁移，不一次性重写 UI。
- API：Node.js LTS + Fastify。
- 契约：Zod；REST 与后台任务共用同一份 schema。
- 数据层：PostgreSQL + Kysely；迁移工具必须支持纯 SQL 审核。
- 后台任务：使用 PostgreSQL 表、行锁和 `SKIP LOCKED` 实现，不把 Redis 设为首版硬依赖。
- AI：优先使用模型提供商官方 SDK；游戏代码可以在自己的模块内部使用任意编排库（包括 LangGraph JS），平台不依赖它。
- 可观测性：结构化日志、OpenTelemetry trace、错误追踪、业务指标。

### 4.1 游戏包：代码化封装

游戏是普通 TypeScript 模块，放在 `apps/platform/src/server/games/<slug>.ts`，一个游戏一个包。平台不解释、也不发布作者上传的定义：

| 关注点 | 由谁负责 |
| --- | --- |
| 阶段、等待点、分支、结束 | 游戏模块的 `transition` |
| 动作合法性、结算、胜负 | 游戏模块自己的规则代码 |
| 不同玩家能看到什么 | 游戏模块声明可见性，内核据此投影 |
| 表现（表单、文案、资源） | 前端与游戏模块自带的元数据 |

平台只保证四件事：**对局有身份**（`instance_id` + 参与者）、**状态可回放**（事件流 + 快照）、**副作用可重试**（幂等键 + 命令队列）、**信息不越权**（投影 fail-closed）。其余都是游戏代码的事。

2026-10-15 变更：原先"作者用 JSON 描述游戏、平台校验并解释执行"的 DSL 路线已撤除，见 §16 第六轮。撤除的代价要写清楚：不再有发布期静态校验，也不再"作者零代码"。

### 4.2 中立内核契约

内核只认接口，不认识任何节点、配置或表达式（实现见 `apps/platform/src/server/game/module.ts`）：

```ts
interface GameModule {
  readonly id: string;
  readonly version: string;
  readonly engineVersion: string;
  readonly visibility?: Record<string, unknown>;   // 哪个变量谁能看；未声明=没人能看
  initialState(input: CreateInstanceInput): GameState;   // 角色、发牌、初始变量由游戏决定
  transition(state: GameState, event: GameEvent): TransitionResult;
}

class GameRegistry { get(id); require(id); list(); }   // 启动时注册，重复 id 直接拒绝
```

`transition` 内不能访问数据库、网络、系统时间或直接调用 LLM。随机数、当前时间和 AI 结果都必须作为显式输入；产生副作用时只输出命令，由 worker 在事务提交后执行。

已落地的内核：`GameModule` 接口 + `GameRegistry` + `createBaseState`（对局外壳）+ `projectPlayerView`（三档投影，fail-closed）+ `replayEvents`（事件重放）+ `EngineError`/`TransitionResult`。

### 4.3 单次动作的事务协议

每次玩家动作采用固定顺序：

1. 从认证会话解析 `actor_id`，不信任客户端提交的身份字段。
2. 锁定目标 `game_instance`，校验席位归属、实例状态和动作幂等键。
3. 读取实例记录的代码版本与当前快照。
4. 执行确定性状态转换，直到结束或进入等待点。
5. 追加领域事件，更新快照，写入待执行命令、定时任务和 Outbox。
6. 提交同一个数据库事务。
7. worker 消费 Outbox，按不同玩家生成状态投影并广播。

任何重试都必须依靠 `(instance_id, event_id)` 或 `(instance_id, command_id)` 唯一约束避免重复结算。

## 5. 游戏封装方式（代码化）

- 游戏逻辑写在 TypeScript 模块里：类型检查、单元测试、调试器、重构工具都是现成的，不需要平台自造一套 schema 语言。
- **不提供**：作者上传代码或包、草稿/测试/发布生命周期、发布期静态校验、声明式节点与白名单表达式。
- **版本固定**：代码里的 `version` 常量 + 对局行记录；对局开始时固定，升级代码不影响进行中的对局。
- **确定性**：由"`transition` 是纯函数"这条约束 + 内核测试保证；违反它属于代码缺陷，不再是发布期能拦住的问题。
- **信息隔离**：由内核投影统一执行；游戏模块只声明"哪个变量谁能看"，不能绕过投影直接下发权威状态。
- **平台内置**：首版游戏由平台自己维护；第三方游戏分发属于后续阶段，需要单独的沙箱与安全设计。

## 6. 数据模型

### 6.1 身份与权限

平台只有两种账号角色，由 `users.platform_role` 决定：

| 角色 | 权限范围 |
| --- | --- |
| `admin` | 管理账号、模型目录与凭据、查看审计、对局运维（暂停/恢复/取消） |
| `user` | 登录、加入对局、按投影读取自己可见的信息 |

对局的参与关系不在角色里，而在 `game_participants`：一张席位要么绑定 `actor_user_id`（真人），要么 `control = 'ai'`。授权判断始终回到这两处，不信任请求里出现的身份字段。

### 6.2 首版核心表

| 表 | 作用 |
| --- | --- |
| `users` | 平台账号与平台角色 |
| `auth_sessions` | 不透明会话（Cookie）、CSRF 摘要、滑动与绝对过期 |
| `providers` / `provider_models` | 模型供应商与模型目录（凭据以 AEAD 密文存列内） |
| `game_instances` | 对局、记录的代码版本、状态、当前序号 |
| `game_participants` | 对局参与者、座位、控制方式 |
| `game_events` | 只追加的领域事件 |
| `game_snapshots` | 加速恢复的状态快照 |
| `pending_commands` | AI 等外部副作用命令 |
| `scheduled_jobs` | 超时、回合计时器、重试时间 |
| `audit_logs` | 账号、模型目录与对局运维操作审计 |

2026-10-15 撤除 DSL 时删掉了 `games`、`game_versions`、`workflow_definitions`、`ai_usage_ledger` 与 `agent_model_bindings`：游戏身份与版本回到代码里，模型目录留在 `providers`/`provider_models`。`game_instances.game_version_id` 保留为纯文本（对局自报的代码版本），不再有外键。

2026-10-15 第八轮又把租户层整体删掉（ADR-008）：`tenants`、`tenant_memberships`、`tenant_secrets`、`player_actions`、`outbox_events` 五张表与所有 `tenant_id` 列、RLS 策略一并撤除——它们在当时的产品形态下不产生价值（唯一租户是常量 `PLATFORM_TENANT_ID`），却让每个查询、每个唯一键、每张新表都带着恒定成本。删除后仍是 11 张表：账号 2 张、模型目录 2 张、对局 6 张、审计 1 张。

关键唯一约束：

```text
(instance_id, sequence) on game_events        -- 顺序号不可重复
(instance_id, idempotency_key) on game_events -- 幂等重放
(instance_id, command_id) on pending_commands -- 命令不可重复入队
(provider_id, model_id) on provider_models
```

状态快照使用 `jsonb`；需要筛选、排序、关联和约束的数据使用普通关系列。对局相关的前缀（`instance_id`）都在每个唯一键里，所以跨对局的撞号不可能发生。

### 6.3 数据库和二进制资源决策

- PostgreSQL 是生产唯一权威数据库。
- 内核单测不需要数据库；涉及锁、事务隔离、`jsonb`、迁移和 worker 的测试一律使用 PostgreSQL。
- 本地完整开发通过 Docker Compose 启动 PostgreSQL；CI 同样运行 PostgreSQL 服务。
- 若“所有存储都进数据库”是硬要求，Beta 可用 `bytea` 保存小型资源，但必须设置单文件和总量上限。大文件会放大备份、复制和恢复成本，公开发布前应重新评估 S3 兼容对象存储；对象元数据和权限仍归 PostgreSQL 管理。

## 7. 编排库（LangGraph 等）的定位

DSL 撤除后，这个问题变简单了：**编排库是游戏代码的内部实现细节，不是平台组件**。

- 平台不依赖任何编排框架，数据库、API 和契约里不出现它们的类型。
- 游戏模块内部可以用任意方式组织逻辑：一个 `switch`、一个状态机库，或 LangGraph JS。这不影响平台能力，因为平台只通过 `GameModule` 接口与游戏交互。
- 平台的四条保证（对局身份、可回放、副作用可重试、信息不越权）由内核与数据库提供，不由游戏代码自己声明；编排库的 checkpoint 只是它自己的内部状态，永远不能成为业务真相。
- 多玩家等待：动作先写入 `player_actions`，达到全员、法定人数或超时条件后只恢复一次流程，不能让每个玩家分别恢复同一图。

Phase 0 原本用 LangGraph JS 的对照来决定"首版执行器"，随着 DSL 撤除，这个决策点不再成立；对照与书面结论见 §16。

## 8. 分阶段迁移计划

以下工期使用“人周”，实际日历时间取决于团队并行度。每个阶段只有满足出口条件后才能进入下一阶段的切流部分；非阻塞工作可以并行。

### Phase 0：决策、行为冻结与技术验证（2～3 人周）

目标：把关键不确定性前置，不在迁移中途重新设计运行时。

任务：

- [x] `P0-01`：编写 ADR，确认 PostgreSQL、Fastify、schema 工具、查询构建器和 Node LTS 版本。 — 核验 2026-10-14：`docs/adr/` 5 份 ADR 已提交
- [/] `P0-02`：冻结旧 Python 对外行为；为创建房间、加入、开始、角色分配、夜间行动、投票、胜负和断线恢复生成黄金事件轨迹。 — 核验 2026-10-14：旧引擎规则轨迹 10 条已冻结并通过校验（`docs/fixtures/werewolf-golden-trace-suite.json`）；超时/断线/AI fallback 需从服务层补录，未做。补充：来源已删除，见 §16 第二轮复核第 1 条
- [x] `P0-03`：给现有测试分类为“有效回归、过时规格、真实缺陷”，先建立可解释的测试基线。 — 核验 2026-10-14：`docs/phase0-test-baseline.md` 已完成前端分类；后端基线已于 2026-10-14 补录（`backend/.venv` 可用，571 测试全绿）
- [x] `P0-04`：定义 `GameDefinition`、`GameEvent`、`GameState`、`PlayerView` 和 `ExternalCommand` v0 schema。 — 核验 2026-10-14：`packages/contracts/src/domain.ts` 已定义 GameDefinition/GameEvent/GameState/PlayerView/ExternalCommand v0
- [x] ~~`P0-05`：完成上一节的 LangGraph JS 技术验证，并以相同测试夹具实现最小原生解释器对照~~ — 已关闭（2026-10-15）：DSL 与运行时适配器概念撤除，编排库成为游戏代码的内部选择（§7、§16 第六轮）。
- [x] `P0-06`：定义 Beta 负载模型。默认起点为 100 个活跃房间、每房 10 人、峰值每秒 20 次动作；产品数据出现后再调整。 — 核验 2026-10-14：`docs/phase0-load-and-legacy-decision.md` 已记录容量模型与旧数据处置假设
- [x] ~~`P0-07`：确定旧数据处置：创建默认 `legacy` 租户，保留历史对局，进行中房间切换时排空。~~ — 已关闭（2026-10-15）：greenfield 口径取消旧数据迁移，"legacy 租户"这一处置方式随租户层删除一并作废

交付物：ADR、领域 schema v0、黄金轨迹、技术验证报告、测试债务清单、负载与数据迁移决策。

出口条件：

- 团队能够说明平台为何不内置游戏 DSL，以及游戏模块如何满足四条平台保证（见 §16 第六轮）。
- 至少一条完整简化对局在进程重启、动作重试和并发提交场景中通过。
- 旧系统关键路径已有机器可读的黄金轨迹，后续迁移可以比较行为。

回滚：此阶段不改生产路径，删除实验代码即可。

### Phase 1：TypeScript 工程基础（2～3 人周）

目标：建立可以持续交付的新骨架，不影响旧系统继续运行。

任务：

- [x] `P1-01`：建立 pnpm workspace 和 `apps/api`、`apps/worker`、`packages/contracts`、`packages/db`。 — 核验 2026-10-14：workspace 含 `apps/api`、`apps/web`、`apps/worker`、`packages/contracts`、`packages/db`、`packages/workflow-engine`
- [x] `P1-02`：创建 Fastify 健康检查、统一错误模型、请求 ID、结构化日志和配置校验。 — 核验 2026-10-14：`app.ts` 提供 request id、结构化日志入口、统一错误响应、`/health`、`/ready`；`config.ts` 用 Zod 校验配置
- [/] `P1-03`：把前端构建逐步切到 TypeScript；先迁移 API、Socket.IO、Pinia store 边界，再迁移组件。 — 核验 2026-10-14：`apps/web` 已全 TypeScript（Vue 3 + Vite + vue-tsc 通过）；旧 `frontend/` 的 Pinia store 与 Socket.IO 仍是 JS，按 greenfield 决策不迁
- [x] `P1-04`：建立 PostgreSQL Compose、迁移命令、测试数据库隔离和种子数据。 — 核验 2026-10-14：`docker-compose.platform.yml` Compose + 迁移 up/down + 独立集成库 `vbrpg_db_integration_clean` + `bootstrap-admin` 种子脚本
- [/] `P1-05`：配置格式化、lint、单元测试、集成测试、构建和依赖审计 CI。 — 核验 2026-10-14：`platform-ci.yml` 已含 build/typecheck/unit/契约/真实 PG 集成/迁移回滚/`pnpm audit`；缺 lint、格式检查与 E2E
- [x] `P1-06`：统一 Node 开发版、CI 版和容器版，消除 Vite 与 Node 版本冲突。 — 核验 2026-10-14：`.nvmrc` 24、CI `node-version-file`、pnpm 11.22.0、Docker `node:24-alpine` 已一致
- [x] `P1-07`：从共享 schema 生成或推导前后端类型，禁止手写重复 DTO。 — 核验 2026-10-14：契约由 Zod 定义并导出 `z.infer` 类型，前后端共用 `src/shared`

交付物：可独立部署的新 API/worker 空壳、共享契约、PostgreSQL 开发环境和绿色 CI。

出口条件：全新检出可用一条命令启动 Web、API、worker 和 PostgreSQL；CI 中 lint、类型检查、单测、PG 集成测试和构建全部通过。

回滚：新服务保持无业务流量，旧 Python 服务不变。

### Phase 2：身份与持久化底座（3～4 人周）

目标：先让所有后续业务运行在可信身份边界与可重试的持久化底座上。

任务：

- [x] `P2-01`：实现用户认证、会话或令牌刷新、密码/第三方身份策略。 — 核验 2026-10-14：平台账号 + 持久化 session（HttpOnly Cookie、CSRF、scrypt、首登强制改密、管理员重置撤销旧 session）；无公开注册
- [x] ~~`P2-02`：实现租户、邀请、成员和 Owner/Admin/Developer/Player RBAC。~~ — 撤销（2026-10-15 第八轮）：租户层与租户角色随 ADR-008 删除，权限只剩平台 `admin`/`user` 与 `game_participants` 席位 — 核验 2026-10-14：`tenants`/`tenant_memberships` 与 Owner/Admin/Developer/Player 角色守卫已实现；邀请流程未实现，产品层只暴露 admin/user
- [x] `P2-03`：创建核心表、索引、唯一约束、外键和软删除/归档策略。 — 核验 2026-10-14：控制面与运行时表、复合外键与唯一约束已建立；软删除用 status 字段。2026-10-15 第八轮：租户相关约束随租户层删除，见 ADR-008
- [x] ~~`P2-04`：建立 tenant-scoped repository；代码评审禁止无租户上下文的业务查询。~~ — 撤销（2026-10-15 第八轮）：`withTenantContext` 与租户作用域仓储已删除 — 核验 2026-10-14：`withTenantContext` + `SET LOCAL app.tenant_id` 与租户作用域仓储已实现；无禁止无租户查询的静态门禁
- [x] ~~`P2-05`：为关键表启用并测试 PostgreSQL RLS。~~ — 撤销（2026-10-15 第八轮）：策略与应用过滤引用同一个常量，等于自证；随租户层一并删除 — 核验 2026-10-14：0004 RLS 已启用，非 owner 角色跨租户隔离在真实 PostgreSQL 验证
- [/] `P2-06`：实现审计日志、凭据信封加密、密钥轮换接口和日志脱敏。 — 核验 2026-10-14：`audit_logs` 与审计写入、`secret-box` AEAD 信封加密与密钥版本已实现；密钥轮换操作流程未实现
- [/] `P2-07`：实现 `pending_commands`、`scheduled_jobs` 的 claim、lease、重试和死信状态。 — 核验 2026-10-14：claim/lease/完成/退避失败与死信已实现。2026-10-15 第八轮：`outbox_events` 与它的 handler 一同删除（推送方案未定，空表不是设计）
- [x] ~~`P2-08`：建立跨租户 REST、WebSocket、worker 和直接对象引用攻击测试。~~ — 撤销（2026-10-15 第八轮）：无租户边界；替身是"非参与者读不到对局"的投影测试 — 核验 2026-10-14：DB 层跨租户隔离测试已通过；REST/WebSocket/worker 攻击测试未做（WebSocket 未实现）

交付物：账号与模型目录控制面、首版数据库 schema、可靠任务底座、安全测试套件。

出口条件：未经认证的请求无法读写任何资源，非参与者读不到对局数据；重复任务不产生重复事件；服务重启后定时任务和待执行命令可继续。

回滚：使用 expand/contract 数据库迁移；新表只增不删，旧系统仍使用原表。

### Phase 3：中立运行时内核与对局底座（4～6 人周）

目标：让平台能可靠地承载**任意代码化游戏**——对局有身份、状态可回放、副作用可重试、信息不越权；平台不理解任何具体游戏的规则。

任务（2026-10-15 撤除 DSL 后的现状）：

- [x] ~~`P3-01` DSL schema 与版本迁移机制~~ — 撤销：随 DSL 撤除，游戏版本回到代码常量。
- [x] ~~`P3-02` 发布期静态校验（图结构/引用/循环/可见性/表达式/AI 降级）~~ — 撤销：不再有可发布定义；可见性校验改为运行时投影的 fail-closed 行为。
- [/] `P3-03`：确定性 `transition`、显式随机种子、事件回放。 — 已实现：`TransitionFn` 类型 + `replayEvents`；确定性由"游戏模块的 transition 是纯函数"这条约束保证，不再有虚拟时钟需求（超时由游戏自己用 `timerExpired` 事件表达）。
- [x] ~~`P3-04` DSL 节点集（start/end、变量、分支、等待、收集、计时、投票、随机、事件、循环）~~ — 撤销（2.8k 行解释器已删除）。
- [x] ~~`P3-05` subflow、parallel/join~~ — 撤销：并行与分支合并留给游戏代码自己表达。
- [/] `P3-06`：快照策略、并发控制、动作幂等与实例级顺序号。 — 幂等键与顺序号约束（`(instance_id, event_id)`、`(instance_id, command_id)`）保留；快照写入策略与并发竞争测试仍待做（`game_snapshots` 表与 `getLatestSnapshot` 已在）。
- [/] `P3-07`：公共/角色/个人三档投影与防泄漏测试。 — 已实现并保留为内核能力（`projectPlayerView`，fail-closed，8 项单测）；入口从"定义里的 visibility"改为"游戏模块声明的可见性映射"。
- [x] ~~`P3-08` LangGraph JS 适配器或原生解释器~~ — 撤销：编排库成为游戏代码的内部选择，平台不依赖（见 §7）。
- [x] ~~`P3-09` AI command 链（超时/重试/预算/用量/降级）~~ — 撤销：随 DSL 的 AI 节点一并删除；AI 能力回到游戏代码内部调用模型，模型目录仍由 `providers`/`provider_models` 与凭据加密（`packages/runtime` 的 secret-box）支撑。
- [x] ~~`P3-10` 管理员暂停/取消/强制超时/脱敏状态~~ — 撤销：实例 HTTP 路由已删；恢复对局的运维能力随代码化游戏的运行时一起回归。

交付物：中立内核（投影、重放、转换类型）、对局底座（实例、参与者、事件、快照、命令队列、定时任务）、审计。

出口条件：同一初始状态与事件序列总能得到字节级一致的最终状态；进程崩溃不丢失已提交事件；隐藏信息自动化测试无泄漏。

回滚：对局行记录它启动时使用的代码版本；升级游戏代码不影响进行中的对局。

### Phase 4：第一个代码化游戏（狼人杀）（3～4 人周）

目标：用真实复杂游戏证明平台抽象足够——游戏逻辑写在 `apps/platform/src/server/games/werewolf.ts`，**平台代码里没有一行狼人杀规则**。

任务（2026-10-15 撤除 DSL 后的现状）：

- [/] `P4-01`：从现有 Python 逻辑提取角色、阶段、动作、胜负、超时和可见性规格。 — 角色/阶段/动作/胜负说明已提取；超时与可见性规格未提取。
- [ ] `P4-02`：把狼人杀写成代码化游戏模块，而不是在平台里增加狼人杀专用分支。 — 未开始：DSL 版本（多回合夹具）已随 DSL 撤除一并删除；新的验收目标是 `apps/platform/src/server/games/werewolf.ts` 模块 + 对局端到端跑通。
- [x] ~~`P4-03` 让 prompt、模型参数与输出 schema 随游戏版本保存~~ — 撤销：AI 行为现由游戏代码自己组织，平台只提供模型目录与凭据。
- [ ] `P4-04`：用 Phase 0 黄金轨迹比较旧系统和新游戏模块；差异必须归类为缺陷修复或经批准的规则变更。 — 未实现（旧 Python 引擎已在 `79cf54e` 删除，黄金轨迹 fixture 降级为历史快照）。
- [x] ~~`P4-05`：实现旧用户、历史对局和默认 `legacy` 租户的数据回填脚本，并提供 dry-run 报告。~~ — 撤销（2026-10-15）：greenfield 不迁移旧数据。
- [x] ~~`P4-06`：让内部测试租户创建新引擎房间，旧生产路径继续服务其他用户。~~ — 撤销（2026-10-15）：没有租户，也没有双轨切流；新平台直接对外。
- [ ] `P4-07`：完成断线重连、多设备、并发投票、AI 失败、worker 重启和版本升级 E2E。 — 未实现。

交付物：第一个代码化游戏模块、兼容性报告、数据回填工具、内部灰度环境。

出口条件：对局端到端跑通且无状态丢失、重复结算和秘密泄漏；旧版已发布游戏仍能继续完成。

回滚：停止创建新对局；已创建的对局继续固定在它们启动时的代码版本。

### Phase 5：游戏模块的工程化与内部工具（3～4 人周）

目标：让平台团队能高效地写、测、发布游戏模块——**不再有面向外部作者的工作台**（DSL 撤除后，"作者分发"整体退出首版范围）。

任务：

- [ ] `P5-01`：实现游戏模块清单（内置游戏列表、可用版本）与对局创建入口。 — 未实现。
- [x] ~~`P5-02` 结构化编辑器、JSON schema 补全、只读流程图~~ — 撤销：游戏是代码，用 IDE 与类型系统即可。
- [ ] `P5-03`：实现测试控制台：注入事件、查看不同玩家投影、重放事件序列。 — 未实现（内核已有 `replayEvents` 与 `projectPlayerView`，缺 HTTP/UI 入口）。
- [ ] `P5-04`：实现游戏模块的回归夹具：标准对局脚本 + 期望事件序列。 — 未实现。
- [ ] `P5-05`：游戏自带静态资源（角色卡、文案）的打包与版本校验。 — 未实现。
- [ ] `P5-06`：实现内部发布流程：代码评审、版本号、变更记录与对局可见性控制。 — 未实现。
- [ ] `P5-07`：提供游戏模块开发文档与示例模块。 — 未实现。
- [x] ~~`P5-08` 可移植游戏包格式（导入/导出/许可/署名）~~ — 撤销：首版由平台自己维护游戏代码。

交付物：内置游戏清单、测试控制台、回归夹具、模块开发文档。

出口条件：平台开发者可以在不改动平台代码的前提下新增一个游戏模块，并用回归夹具证明标准对局跑通、信息不漏。

回滚：移除新增游戏模块；进行中的对局继续固定在它们启动时的代码版本。

### Phase 6：生产切换与公开 Beta（2～3 人周）

目标：在可观测、可恢复、可回退的条件下结束 Python 主路径。

任务：

- [ ] `P6-01`：完成容量测试、长时间稳定性测试、并发动作测试和故障注入。 — 核验 2026-10-14：未开始
- [ ] `P6-02`：建立 API、worker、队列积压、动作延迟、AI 成功率/成本、对局卡住率和未授权访问拒绝指标。 — 核验 2026-10-14：未开始
- [ ] `P6-03`：验证备份、时间点恢复、迁移回滚、密钥轮换和灾难恢复手册。 — 核验 2026-10-14：未开始
- [ ] `P6-04`：执行安全评审：认证、授权、提示词注入、文件上传、日志隐私和供应链。 — 核验 2026-10-14：未开始
- [ ] `P6-05`：先按内部测试账号、小比例新对局逐级放量。 — 核验 2026-10-14：未开始
- [ ] `P6-06`：冻结 Python 新房间创建，等待短期对局自然结束；长期历史数据保持只读。 — 核验 2026-10-14：未开始
- [ ] `P6-07`：更新部署、用户、作者、运维、故障处理和数据保留文档。 — 核验 2026-10-14：未开始
- [ ] `P6-08`：达到发布门槛后删除流量依赖，但至少保留一个发布周期的 Python 镜像和只读数据访问能力。 — 核验 2026-10-14：未开始
- [ ] `P6-09`：完成服务条款、隐私说明、内容许可、数据导出/删除和侵权/举报处理流程的发布评审。 — 核验 2026-10-14：未开始

交付物：公开 Beta、监控面板、告警、备份恢复证据、切换记录和运行手册。

出口条件：满足第 10 节全部发布门槛，并完成一次真实备份恢复演练和一次应用回滚演练。

回滚：只回滚“新对局路由”，不把新引擎实例转换为 Python 实例；数据库使用向后兼容迁移，保留新事件和审计记录。

### Phase 7：Beta 后增强

- 更完整的对局调试器与可观测面板。
- 第三方游戏分发：需要单独的沙箱、资源限额与安全评审，属于独立阶段，不在首版承诺内。
- 创作者商业化、支付、结算、退款和税务流程。
- 评分、推荐、内容审核工作流和版权申诉。
- 多区域部署、更严格的 SLO 和大规模队列系统。
- 在有真实需求时评估 MySQL 适配；在此之前不承诺兼容。

## 9. 数据迁移与切流方案

采用 Strangler 方式，新旧后端并存，按对局实例路由，避免对同一实例双写两个引擎。

### 9.1 数据迁移步骤

1. 新 schema 先以新增表和可空列上线，不删除旧列。
2. ~~创建 `legacy` 租户，把现有用户、游戏和历史记录映射到该租户。~~ 已在 2026-10-15 作废：greenfield 不迁移旧数据。
3. 回填脚本必须支持 dry-run、分批、断点续传、校验摘要和重复执行。
4. 比较迁移前后行数、外键、关键聚合、事件序列和抽样玩家历史。
5. 新写入切到 TypeScript 后，进入观察期；确认无回退需要再执行 contract migration。
6. 删除旧表或旧列属于 Beta 稳定后的独立变更，不能与首次切流同时执行。

### 9.2 对局切流

- 网关或 API 根据 `game_instances.engine_version` 路由，不能根据当前部署版本猜测。
- ~~新租户先使用新引擎，旧租户逐批开启。~~ 已作废：新平台直接对外。
- 短生命周期旧对局自然排空；只有确有业务价值的长期对局才编写显式导入器。
- 切换期禁止跨引擎继续同一个实例，也禁止没有事件一致性协议的双写。

## 10. 发布门槛（Definition of Release Ready）

以下条件全部满足才进入公开 Beta：

### 正确性与恢复

- 所有有效旧行为黄金轨迹通过；规则差异有版本化说明。
- 重复动作、重复 WebSocket 包和 worker 重试不会重复结算。
- 任意服务进程重启后，已提交动作不丢失，等待和计时器可恢复。
- 从事件重放得到的状态与最新快照一致。
- AI 超时、结构化输出错误和供应商不可用不会让实例永久卡住。

### 安全

- REST、后台任务和管理入口都有未认证与非管理员访问的自动化测试。
- 没有由客户端直接决定的可信 `user_id` 或角色。
- 玩家投影、日志、trace、错误响应和 AI prompt 不泄露无权查看的隐藏状态。
- 凭据加密存储，日志脱敏，敏感操作有审计记录。
- 发布时没有未处置的 P0/P1 安全缺陷。

### 工程质量

- CI 的 lint、类型检查、单元、PostgreSQL 集成、契约、E2E 和构建全部绿色。
- 迁移在生产数据副本上验证，升级和回滚路径均演练。
- 容器、CI 和本地支持的 Node/PostgreSQL 版本一致并有明确生命周期。
- API、事件与运行时契约都有版本策略及兼容性测试。

### 运维与容量

- 达到 Phase 0 确认的负载目标，并保留容量余量；AI 时间不计入同步 API 延迟。
- 对动作处理延迟、错误率、卡住实例、任务积压、AI 成本和数据库连接设有指标及告警。
- 完成一次备份恢复演练，记录 RPO/RTO 实测结果。
- 有部署、回滚、卡局处置、密钥轮换和数据导出/删除手册。

## 11. 测试矩阵

| 层级 | 运行数据库 | 重点 |
| --- | --- | --- |
| 内核单测 | 无数据库或 SQLite | 投影、重放、确定性、属性测试 |
| 游戏模块单测 | 无数据库 | 角色、阶段、动作合法性、胜负、隐藏信息 |
| Repository 合约测试 | PostgreSQL | 约束、事务、锁、队列 claim/lease、迁移与回滚 |
| Runtime 集成测试 | PostgreSQL | 幂等、并发、事件/快照、Outbox、定时任务 |
| API 契约测试 | PostgreSQL | 身份、错误模型、幂等与重复提交 |
| 对局端到端测试 | PostgreSQL | 完整对局、隐藏信息、断线恢复、AI 席位 |
| E2E | 完整 Compose | 创建对局、加入、完整对局、重启恢复 |
| 安全测试 | 完整 Compose | IDOR、未授权读写、prompt 注入、权限提升 |
| 容量与故障测试 | 类生产 PostgreSQL | 峰值动作、worker 崩溃、数据库抖动、AI 超时 |

SQLite 测试通过不能替代 PostgreSQL 集成测试通过。

## 12. 风险与缓解措施

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 逐行翻译大型 Python 服务 | 把旧耦合复制到 TS | 先定义领域 schema、纯 transition 和黄金轨迹，再重写游戏包 |
| 游戏代码绕过平台保证（直接写库、泄漏隐藏状态） | 泄漏、脏状态、无法回放 | 游戏模块只拿到状态与事件、只能返回命令；投影由内核统一执行；代码评审与回归夹具 |
| 游戏代码不确定（时间/随机/网络） | 回放不一致 | `transition` 纯函数约束 + 内核测试；随机种子与时间作为显式事件输入 |
| SQLite 掩盖生产差异 | CI 绿但 PG 故障 | 所有持久化和并发测试强制真实 PostgreSQL |
| 隐藏信息泄漏 | 严重作弊和隐私事故 | 权威状态与玩家投影分离；按角色属性测试；日志和 prompt 脱敏 |
| AI 调用拖垮对局或成本 | 卡局、费用不可控 | 平台只提供模型目录与凭据；游戏代码负责超时与降级，用量与成本指标随后续阶段补齐 |
| 双写造成状态分叉 | 无法恢复和审计 | 按实例固定执行器；迁移期只路由，不对同一实例跨引擎双写 |
| 大资源存入 PG | 备份和复制膨胀 | 首版大小/配额限制；公开发布前评估对象存储 |
| 一次性重写前后端 | 交付周期失控 | 按新实例灰度 |

## 13. 前两个迭代的具体安排

### Iteration 1（第 1～2 周）

- [x] `P0-01` 提交 5 份 ADR：数据库、运行时边界、schema 工具、数据访问层、资源存储。
- [/] `P0-02` 录制至少 8 条旧系统黄金轨迹，覆盖正常、超时、断线和胜负。
- [x] `P0-03` 给当前失败测试建立分类清单，确定真正的阻塞测试集。
- [x] `P0-04` 在 `packages/contracts` 原型中定义 v0 领域事件和状态 schema。
- [x] ~~`P0-05` 完成 LangGraph JS 与最小解释器对照验证~~ — 已关闭（2026-10-15）：DSL 与运行时适配器概念撤除，编排库退化为游戏代码内部选择。
- [x] `P0-06` 评审 Beta 负载、租户角色和旧数据处置假设。
- [/] `P0-07` 确定旧数据处置：创建默认 `legacy` 租户，保留历史对局，进行中房间切换时排空。

核验 2026-10-14：`P0-01`、`P0-03`、`P0-04`、`P0-06` 已完成；`P0-07` 的处置决策已完成、回填脚本仍属 Phase 4。原迭代进度记录如下：`P0-01`、`P0-03`、`P0-04`、`P0-06` 和 `P0-07` 已完成；`P0-03` 的后端基线需在安装 Python 测试环境后补录。`P0-02` 已生成 10 条旧引擎规则轨迹，但超时、断线和 AI fallback 仍需从服务层补录，因此尚未完成。`P0-05` 已于 2026-10-15 关闭（对照对象消失），书面结论见 §7 与 §16 第六轮。

迭代验收：可以用同一份测试夹具驱动旧 Python 行为记录和至少一个 TS 内核原型；关键 ADR 已评审，无悬而未决的数据库选择。

### Iteration 2（第 3～4 周）

- [x] ~~完成 LangGraph JS 技术验证的重启、并发、幂等、投影、版本和 AI fallback 测试~~ — 已撤销（2026-10-15）。
- [x] ~~形成保留或放弃 LangGraph 作为第一版运行时的书面结论~~ — 已关闭：平台不内置编排运行时，游戏代码自行选择（§7）。
- [x] 建立 pnpm workspace、Fastify API、worker 和共享契约包。
- [x] 建立 PostgreSQL Compose 与第一条迁移。
- [/] 建立 CI：lint、typecheck、unit、PG integration、build。 — 核验 2026-10-14：除 lint 外均已落地（`.github/workflows/platform-ci.yml`）
- [/] 修正 Node/Vite/ESLint 基线，使新骨架全绿。 — 核验 2026-10-14：Node/pnpm 已统一；仓库无 ESLint 配置，lint 门禁仍缺

核验 2026-10-14：workspace、API、worker、契约、Kysely、Compose、控制面与运行时迁移、租户仓储、Outbox/command/job claim-lease、session/membership 与 RLS 均已落地并通过真实 PostgreSQL 测试；仍缺 lint、刷新 token、跨租户 REST/WebSocket/worker 攻击测试、一键启动脚本和生产 handler。原迭代进度记录如下：已建立 workspace、Fastify API、worker、共享契约包、Kysely PostgreSQL 客户端、PostgreSQL Compose、控制面与游戏运行时核心表迁移、租户作用域仓储、Outbox/command/job claim-lease 基础、签名访问令牌/RBAC 原型、数据库 session/membership 查询接线、RLS 迁移和基础 CI。真实 PostgreSQL 迁移、重复迁移和非 owner RLS 集成测试均已通过；lint、刷新 token、跨租户 REST/WebSocket/worker 攻击测试、前端 TypeScript 边界和一键启动仍未完成。

迭代验收：新 TS 骨架可在全新环境一键启动；CI 全绿；尚未把生产流量切入新系统。

## 14. 项目管理约定

- 每项任务进入开发前必须写明输入、输出、测试和数据库影响。
- 每个数据库变更使用 expand/contract，迁移脚本可重复验证并包含回滚说明。
- 每个游戏模块必须带回归夹具（标准对局 + 期望事件序列），并证明隐藏信息不漏。
- 每个外部副作用必须经过 command/outbox，不允许从纯引擎直接执行。
- 每个实时事件必须有共享 schema、身份来源和幂等策略。
- 每个阶段结束进行一次出口评审，不以“代码已合并”代替验收结果。
- 工作看板建议使用任务编号 `P{phase}-{sequence}`，缺陷使用 `BUG-{sequence}`，架构决策使用 `ADR-{sequence}`。

## 15. 需要在 Phase 0 最终确认的决策

| 决策 | 当前建议 | 截止点 | 2026-10-14 状态 |
| --- | --- | --- | --- |
| 生产数据库 | PostgreSQL only | `P0-01` | 已落地（ADR-001） |
| API 框架 | Fastify | `P0-01` | 已落地（`apps/api`） |
| Schema 工具 | Zod 或 TypeBox 二选一 | `P0-01` | 已落地：Zod（ADR-003） |
| 数据访问层 | Drizzle 或 Kysely 二选一 | `P0-01` | 已落地：Kysely（ADR-004） |
| 首版运行时 | ~~由 LangGraph JS spike 决定~~ | `P0-05` | 已关闭：DSL 与适配器概念随 2026-10-15 撤除消失；编排库退化为游戏代码的内部选择（§7） |
| 二进制资源 | PG `bytea` + 严格上限；发布前复审对象存储 | `P0-01` | 已落地（ADR-005）；发布前复审未做 |
| 身份方案 | 自建会话还是托管 IdP | `P2-01` 前 | 已落地：自建会话 + 平台账号（`routes/platform-auth.ts`） |
| 旧进行中对局 | 默认排空，不自动迁移 | `P0-07` | 已决策；greenfield 下旧线不在门槛内，回填工具未实现 |
| Beta 容量目标 | 默认 100 房间 / 1000 在线 / 20 动作每秒 | `P0-06` | 已记录（`docs/phase0-load-and-legacy-decision.md`）；容量测试未做 |

## 16. 核验结论与下一步

核验方式：对照 `apps/`、`packages/` 源码、迁移文件、测试与已提交历史逐项判定，不采信进度报告的自我描述。§8 的任务勾选状态随时间变化，以下结论以最新一轮为准。

### 已完成的主干（截至 2026-10-15）

- 工程骨架与 CI：pnpm workspace、Fastify API、worker、`packages/{contracts,db,runtime,workflow-engine}`、真实 PostgreSQL 集成与迁移回滚门禁（`P1-01`、`P1-02`、`P1-04`、`P1-06`、`P1-07`）。
- 控制面与认证：平台账号、持久化 session、首登强制改密、管理员建号与重置、Provider/Model 管理、AEAD 凭据加密、审计（`P2-01`、`P2-03`、`P2-05`）。
- 中立内核：玩家视图投影（fail-closed）、事件重放、转换与错误类型（`packages/workflow-engine`）。
- 对局底座：`game_instances`/`game_participants`/`game_events`/`game_snapshots`/`player_actions`/`pending_commands`/`scheduled_jobs`/`outbox_events` + 租户 RLS + 队列 claim/lease/重试。

### 关键断点（比任务勾选更重要）

1. **没有游戏运行时**：DSL 撤除后（§16 第六轮），创建与推进对局的 HTTP 入口、游戏模块接口与注册表都不存在，平台目前只能做账号、租户与模型管理。
2. **worker 空转**：claim/lease/outbox 循环在位，但没有 handler，因为没有生产者。
3. **AI 能力只剩目录与凭据**：`providers`/`provider_models` 与 `secret-box` 保留，调用链（命令、重试、降级、用量）随 DSL 的 AI 节点一并删除。
4. **`outbox_events` 无 handler**：它的 handler 是广播传输层，属实时阶段。
5. **前端只有账号与模型配置页面**（`apps/web` 的 Login/Users/Providers/Lobby），没有对局界面。

### 历史复核记录

- **第一轮（2026-10-14）**：逐项核验 §8 任务并标注证据。
- **第二轮（2026-10-14）**：复核全部进度文档与实现的不一致项——黄金轨迹门禁断链（`werewolf_engine.py` 已删除）、旧后端基线过期（`backend/.venv` 571 测试全绿）、测试数与报告过期、AI 实网验收不可复现（TokenHub+`hy3` 现返 401，可用组合为 `api.deepseek.com`+`deepseek-chat`）、契约未覆盖并存端点、一键启动缺 worker 服务。
- **第三轮（2026-10-15，已随第六轮撤除）**：显式循环节点（`loop`）与发布期环规则；狼人杀包升级为多回合；修复 worker 领取查询的时钟来源缺陷（`pending_commands.available_at` 改为与数据库时钟比较，该修复保留）。
- **第四轮（2026-10-15，已随第六轮撤除）**：AI prompt 改为按席位投影（不再序列化权威状态与事件 payload）。其中"prompt 不得泄漏"这条原则仍然成立，代码化游戏沿用同一套投影。
- **第五轮（2026-10-15，已随第六轮撤除）**：agent 定义随版本保存（`agents[]`）、每席位一个 agent 的会话模型。

### 第六轮（2026-10-15）：撤除 DSL，改为代码化游戏封装

**决策**：放弃"作者用 JSON 描述游戏、平台校验并解释执行"的路线。游戏逻辑改为 TypeScript 模块（`apps/platform/src/server/games/<slug>.ts`），平台只保留对局底座与中立内核。理由：DSL 的维护面（schema、校验器、表达式、解释器、发布流程）远大于它带来的收益，而代码化游戏直接获得类型检查、单元测试与调试器。

**删除**（提交 `refactor: drop the declarative game DSL, keep the neutral kernel`，60 个文件、-6881 行）：

- `packages/workflow-engine`：编译、发布期校验、表达式 AST、节点解释器、狼人杀夹具（内核的投影/重放/类型保留）。
- 契约：游戏定义、节点、agent 定义、实例/事件请求 schema（状态、事件、参与者、等待点、命令、玩家视图保留）。
- `packages/runtime`：AI 命令链、实例执行、管理员控制（凭据加密与错误类型保留）。
- `apps/api`：实例、管理员实例、MVP 无状态路由与其脚本、AI provider 配置项。
- `apps/worker`：游戏 handler 接线（claim/lease 循环保留）。
- 迁移：`games`、`game_versions`、`workflow_definitions`、`ai_usage_ledger`、`agent_model_bindings` 五张表；`game_instances.game_version_id` 降为纯文本。
- ADR-002（执行器边界）与 ADR-006（agent 会话）随之下线。

**保留**：租户、账号、会话、Provider/Model 与凭据加密、审计、对局底座与队列、投影与重放内核、前端账号与模型页面、CI 门禁。

**代价（明确记录）**：不再有发布期静态校验；不再"作者零代码"；游戏代码必须自己遵守"`transition` 是纯函数"这条约束；隐藏信息只能通过内核投影保证，游戏代码不得绕过。

### 第七轮（2026-10-15）：收敛为单包单镜像（ADR-007）

**决策**：`packages/{contracts,db,runtime,workflow-engine}` + `apps/{api,worker,web}` 合并为一个 `apps/platform`：

- `src/shared`（契约）、`src/server`（进程侧 + 游戏内核）、`src/browser`（控制台）三个 tsconfig project；
- 一个镜像两种角色：`--role=api|worker|both`，api 角色同源提供浏览器产物（不再需要 nginx、第二个镜像与跨域配置）；
- 内核从包变成 `src/server/game/`，`workflow-engine` 这个名字与它的 DSL 词汇一起消失（`currentNodeId`/`waiting.nodeId` 改为 `stepId`）；
- 契约的 `aiGenerate` 外部命令一并删除（平台当下只能执行 `schedule` 与 `emit`，AI 命令随 AI 工作回归）。

**新增能力**：`GameModule` 接口 + `GameRegistry` + `createBaseState`（§4.2），内核首次有明确的消费者契约。

**代价**：失去包边界强制的无环依赖图，改由 tsconfig project 与评审保证；真要拆包时是机械操作（ADR-007 记录了升级路径）。

**下一步建议顺序**：

1. **对局 HTTP 入口**：创建对局、提交事件、读取自己的投影，复用已保留的对局底座与幂等约束（`GameRegistry` 已就位）。
2. **第一个代码化游戏（狼人杀）**：`apps/platform/src/server/games/werewolf.ts` + 回归夹具（标准对局脚本 + 期望事件序列 + 隐藏信息断言）。
3. **AI 席位与 mailbox**：游戏代码内部调用模型，平台提供模型目录与凭据解析；消息/会话设计见 §16 第六轮的 mailbox 讨论记录。
4. **工程门禁**：CI 增加 lint 与格式检查（`P1-05` 未收口，边界现在依赖 lint）；密钥轮换流程（`P2-06`）；处置 `pnpm audit` 的 15 high。

### 第八轮（2026-10-15）：删掉租户层与未决的投递层（ADR-008）

**决策**：整体删除租户层与三张不产生价值的表，schema 从 16 张收敛到 11 张，并把 schema 直接改到位（greenfield、库中无数据，不留 expand/contract 兼容路径）。

**删除**：

- 表：`tenants`、`tenant_memberships`、`tenant_secrets`、`player_actions`、`outbox_events`。
- 列与约束：所有表的 `tenant_id`、复合外键与复合唯一键、`providers.name` 的租户内唯一；`auth_sessions.refresh_token_hash`（零使用的遗留列）。
- RLS：原 `0004_tenant_rls.sql` 及其 12 张表的策略。
- 代码：`withTenantContext`、`platformContext`、`PLATFORM_TENANT_ID`、租户作用域仓储、`recordPlayerAction`、Outbox 的 claim/complete、worker 的按租户循环。
- 遗留 bearer 认证路径：`server/auth.ts`（JWT 风格 token + 租户角色）、`routes/auth.ts`（`/v1/tenant/me`、`/v1/tenant/management-check`）、`AUTH_TOKEN_SECRET`、`x-tenant-id`、`app.ts` 的鉴权 hook 与 `main.ts` 的 `sessionLookup`。平台会话（不透明 session + HttpOnly Cookie + CSRF）成为唯一认证路径。
- 迁移文件：原 0001/0003/0004/0005 合并重写为 `0001_accounts_and_models`（账号、会话、模型目录、审计）与 `0002_game_runtime`（6 张对局表），两者各带 `.down.sql`。

**理由**：支撑租户层的三条理由里两条已失效——旧数据切流随 greenfield 撤销（`P0-07`、`P4-05`、`P4-06`），`tenant_memberships.developer`（游戏作者/发布）随 DSL 撤除（§16 第六轮）消失；剩下的一条（多客户 SaaS 隔离）是商业决定而非技术必然，且当时唯一租户是常量，RLS 与应用过滤引用同一个值，等于自证。`outbox_events` 的消费者是实时推送，而推送被 `docs/mvp-scope.md` 明确推迟，空表不是设计。

**代价**：迁移文件重写使已有本地/容器数据库必须重建（无兼容路径）；若将来真的需要多社群或 SaaS 隔离，要重新引入这一层（有数据后成本会显著上升）。这一条作为已知风险记录在此。

**保留**：账号与平台角色、不透明会话与 CSRF、模型目录与凭据 AEAD 加密、审计、6 张对局表与两条队列、投影与重放内核、前端账号与模型页面、CI 门禁。

## 17. 参考资料

- [LangGraph JS Overview](https://docs.langchain.com/oss/javascript/langgraph/overview)
- [LangGraph JS Persistence](https://docs.langchain.com/oss/javascript/langgraph/persistence)
- [LangGraph JS Interrupts](https://docs.langchain.com/oss/javascript/langgraph/interrupts)
- [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)
