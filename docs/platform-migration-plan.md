# VBRPG 游戏平台计划与决策日志

> 状态：执行中（greenfield）
> 更新日期：2026-10-15
> 结构：§1–§7 设计与约定、§8 现状与工作计划（M1–M5）、§9–§11 边界与门槛、§12 风险、§13 下一步、§16 决策日志（按轮次，最新一轮为准）。
> 适用范围：`apps/platform`（TypeScript + PostgreSQL），游戏是代码化模块，平台不解释规则

> 当前执行模式：Greenfield 新项目。旧 Python/Vue 系统、数据迁移、兼容层、双轨切流、旧版本行为兼容和历史黄金轨迹不属于当前交付门槛；旧实现仅作为可选领域参考。后续验收以新 TypeScript 平台、PostgreSQL、中立运行时内核与代码化游戏模块为准（DSL 路线已于 2026-10-15 撤除，见 §16 第六轮）。

## 1. 执行摘要

游戏规则是一台**事件驱动、可持久化、可暂停和恢复的状态机**：玩家输入、计时器、随机事件与 AI 调用都是驱动它继续执行的事件或外部活动。规则本身写在 TypeScript 游戏模块里，平台不解释规则、只负责承载对局。

本计划采用以下结论：

1. 旧 Python/Vue 系统只作领域参考：不逐行翻译，也不做兼容层（见开头的 greenfield 口径）。
2. **游戏逻辑是代码，不是平台解释的 JSON**：一个游戏一个 TypeScript 模块（`apps/platform/src/server/games/<slug>.ts`），平台只提供对局底座与中立内核。原先的声明式 DSL 路线已于 2026-10-15 撤除，见 §16 第六轮。
3. 编排库（LangGraph JS 等）是游戏代码的内部选择，平台不依赖、也不暴露它们（见 §7）。
4. 生产环境只支持 PostgreSQL。内核单测不需要数据库；所有持久化、并发与迁移测试必须运行真实 PostgreSQL。
5. 对局在创建时固定它使用的代码版本；升级游戏代码不影响进行中的对局。
6. 所有权威数据都进入 PostgreSQL：对局状态、席位、事件记录、账号、模型目录、审计。进程内存只允许作缓存。
7. 首版由平台自己维护游戏代码，不提供作者上传代码或包的通道；第三方分发需要单独的沙箱与安全设计。

## 2. 产品目标与非目标

### 2.1 Beta 目标

- 平台账号由管理员创建；用户登录后进入自己的对局列表。
- 平台内置的游戏可以被创建为对局、开始、并跑到结束（游戏代码在 `apps/platform/src/server/games/*` 维护）。
- 玩家可以加入对局，在断线、服务重启后继续。
- 一个对局可以同时包含真人和 AI 席位。
- 玩家只能看到自己有权看到的信息，且这一点由平台强制（投影 fail-closed），不依赖游戏代码自觉。
- 对局数据一律经过投影读取，隐藏信息不因接口扩张而泄漏。
- 每次状态变化可审计、可查询、可幂等处理。

### 2.2 Beta 非目标

- 不同时支持 PostgreSQL 和 MySQL 生产部署。
- 不提供作者上传代码、第三方 npm 包执行或沙箱插件能力。
- 不提供声明式游戏 DSL、草稿/发布生命周期与发布期静态校验（2026-10-15 撤除）。
- 不在首版完成 Steam 式商业市场、创作者分成和复杂支付结算。
- 不保证把进行中的旧 Python 对局无损迁移到新引擎；优先采用排空旧对局的切换方式。

## 3. 基线

旧 Python/FastAPI + Vue 3 系统仍在仓库根目录（`backend/`、`frontend/`），**只作领域参考**：不迁移它的数据、不复刻它的接口、不保留它的运行契约。新平台是 greenfield，`apps/platform` 是唯一在维护的代码（ADR-007）。

当前实现到什么程度、还缺什么，见 §8.1。

## 4. 目标架构

```mermaid
flowchart LR
    Browser[Vue 3 + TypeScript] -->|REST| API[Fastify API]
    API --> Auth[身份与授权]
    API --> Games[游戏模块 apps/platform/src/server/games/*]
    Games --> Engine[中立内核：投影 / 转换类型]
    API --> DB[(PostgreSQL)]
    Worker[TypeScript Worker] -->|扫描待办的 running/waiting 对局| DB
```

实际结构（2026-10-15 起）：**一个包、一个镜像、两种角色**。

```text
apps/platform/
  src/shared/          # 契约：Zod schema + 类型（浏览器安全，不许 import node 内建）
  src/server/          # 进程侧：Fastify 路由、鉴权、存储、worker 扫描、游戏内核
    game/              # 中立内核：GameModule 接口、注册表、投影
    db/                # Kysely 类型、仓储、迁移读取
    runtime/           # 凭据加密、错误形状
  src/browser/         # Vue 3 控制台（构建成静态资源，由同一进程提供）
  migrations/          # SQL 迁移
  scripts/             # migrate / bootstrap-admin / db-integration / provider check
```

仓库根的 `backend/`、`frontend/` 是旧系统，不在交付门槛内。

三种角色、同一个镜像：`--role=api`（HTTP + 静态资源）、`--role=worker`（推进对局）、`--role=both`（本地开发）。
浏览器产物由 api 角色同源提供，因此不再需要 nginx、跨域配置或第二个服务。

推荐技术组合：

- Monorepo：pnpm workspace。
- Web：Vue 3 + TypeScript，逐个模块迁移，不一次性重写 UI。
- API：Node.js LTS + Fastify。
- 契约：Zod；REST 与后台任务共用同一份 schema。
- 数据层：PostgreSQL + Kysely；迁移工具必须支持纯 SQL 审核。
- 后台任务：不引入队列中间件与 Redis；worker 扫描 `running`/`waiting` 的对局、按实例加行锁推进（ADR-009）。
- AI：优先使用模型提供商官方 SDK；游戏代码可以在自己的模块内部使用任意编排库（包括 LangGraph JS），平台不依赖它。
- 可观测性：结构化日志、OpenTelemetry trace、错误追踪、业务指标。

### 4.1 游戏模块：代码化封装

游戏是普通 TypeScript 模块，放在 `apps/platform/src/server/games/<slug>.ts`，一个游戏一个模块。平台不解释、也不发布作者上传的定义：

| 关注点 | 由谁负责 |
| --- | --- |
| 阶段、等待点、分支、结束 | 游戏模块的 `transition` |
| 动作合法性、结算、胜负 | 游戏模块自己的规则代码 |
| 不同玩家能看到什么 | 游戏模块声明可见性，内核据此投影 |
| 表现（文案、角色卡、资源） | 前端；游戏模块可自带静态资源 |

平台只保证四件事：

1. **对局有身份**：`game_instances` + `game_participants`（席位是人还是 AI）。
2. **记录可查**：`game_events` 按 `sequence` 存下发生过的一切（ADR-010）。
3. **写入幂等**：`(instance_id, sequence)` 与 `(instance_id, idempotency_key)` 保证重试不重复结算，按实例行锁保证同一对局的写入串行。
4. **信息不越权**：`projectPlayerView` 按游戏声明的可见性投影，fail-closed。

其余都是游戏代码的事。

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

界面上的每个字都归游戏自己命名（`title`、`steps`、`words`、动作的 `label`），平台只按词表渲染：
没声明的词保持原样，平台不替游戏编中文，也不把机器名当文案给玩家看。

`visibility` 可以是状态函数（`(state) => Visibility`）：每席位的秘密变量只有在席位存在之后才可寻址，游戏据此计算规则。读接口返回的席位表给出 `key ↔ participantId` 映射；事件 payload 里的席位引用一律用 `participantId`。

`transition` 内不能访问数据库、网络、系统时间或直接调用 LLM。随机数、时间与 AI 结果都必须作为显式输入（事件）进来；它只能返回新的状态与要追加的事件，由平台在事务里落库。

已落地的内核：`GameModule` 接口 + `GameRegistry` + `createBaseState`（对局外壳）+ `projectPlayerView`（三档投影，fail-closed）+ `EngineError`/`TransitionResult`。（`replayEvents` 已于 2026-10-15 第十轮删除：记录是给人读的历史，不是重建状态的输入，见 ADR-010。）

### 4.3 单次动作的事务协议

每次玩家动作采用固定顺序：

1. 从认证会话解析调用者身份，不信任客户端提交的身份字段。
2. 校验席位归属与实例状态；按实例取行锁，串行化同一对局的写入。
3. 读取 `state_json` 与 `current_sequence`。
4. 执行确定性状态转换，直到结束或进入等待点。
5. 在同一事务里追加记录行、推进 `current_sequence` 与 `state_json`。
6. 提交事务。提交之后才做外部动作（调模型、推送）。
7. 读路径没有第二步：按 `sequence` 读记录，或按投影规则读状态。

任何重试都必须依靠 `(instance_id, sequence)` 与 `(instance_id, idempotency_key)` 唯一约束避免重复结算；
`update ... where current_sequence = N-1` 影响零行就说明别人先推进了。

### 4.4 AI 席位契约（2026-10-15 定稿，实现见 M2）

**AI 玩家是每局临时席位**：不建 `agents` 表，AI 席位的身份就是它那一行 `game_participants`（`control='ai'`、`actor_user_id` 为空）。人格、模型与角色由游戏在 `initialState` 里写进状态或席位，平台不认识它们。

**谁动手**：等待点已经指名**待办席位**，而这个席位是人还是 AI 由 `game_participants.control` 决定。因此 `waiting.kind` 不再需要 `'ai'` 这一档——同一件事只留一个真相。

**动作即事件**：

- `GameModule.actions`（静态目录）：`{ name, label, description, args, audience }`，其中 `name` 就是事件类型，`label` 是台面上怎么称呼它，`args` 是 payload 的字段、说明与形态（`kind: "seat"` 表示这是个席位选择），`audience` 决定该动作的内容是进公共转录（`room`，默认）还是只留给席位自己（`seat`，例如秘密投票）。
- `waiting.actions`：当前这一步**允许的名字子集**。
- 平台执行一次工具调用 = 用 `{ type: name, payload: args }` 走 M1 的写入路径。真人与 AI 从同一个口子进，没有第二条通道。
- `GameModule.briefing(state, participantId)`：游戏用自己的话写规则；平台再补上该席位的私有状态。两者都是对局内不变的，因此都进 `system`。
- `aiCall` 行的 payload 形状进契约（`aiCallPayloadSchema`）：回复原文、思考、provider 签名字段、`finishReason`、工具调用。带 `tools` 的 provider 要求把自己的思考原样回传，所以它是**逐字重放**的字段，不是给人看的备注。

**prompt 布局为"前缀稳定"**（缓存按前缀命中，工具表一动，后面整段转录都要重算）：

| 区块 | 内容 | 对局内变动 |
| --- | --- | --- |
| `tools` | 游戏动作**全集**（静态目录） | 不变 |
| `system` | 游戏规则 + 该席位人格 + 该席位私有状态（自己的词） | 不变 |
| `messages` | 转录 + **本轮指令**（当前回合、现在允许哪些动作） | 只有尾部 |

纪律：`tools` 与 `system` 里不放时间戳、对局序号、当前回合、剩余席位这类会变的东西，它们一律进最后一条消息。每个席位有自己的缓存，所以席位专属的 `system` 不影响他人。

**校验发生在执行处，不靠模型自觉**：允许集来自当前等待点，越界调用以**工具结果**回给模型（`describe 现在不可用，可用：vote`），规则拒绝（如 `UNKNOWN_TARGET`）同样回灌为工具结果。任何一次拒签都不该让回合失败或对局卡住。

**记录与失败**：

- prompt 不入库。
- 每次模型调用写一行 `aiCall`（provider/model/三个 token 计数 + 回复原文 + 思考与 provider 签名字段）；回合的结果另写一行，走同一条写入路径。
- 模型不可用或超时写 `aiFailed`，**后果由游戏规则决定**；每回合有迭代上限与单次调用超时。

**模型客户端**要有可注入的传输层：平台自己的 SSRF 防护会拒掉 loopback，没有注入点就没法在不连真实 provider 的情况下测试。

**席位之间的可见性由 prompt 组装决定**，不是读取路径的过滤（ADR-010）：目前只放"发言行 + 该席位自己的行 + 投影"——秘密投票的行不得进别人的 prompt。

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
| `game_instances` | 对局、`game_id`、代码版本 `game_version`、状态、当前序号 |
| `game_participants` | 对局参与者、座位、控制方式 |
| `game_events` | 对局记录：一行一层意思，按 `sequence` 读；含 AI 每次交互与用量（ADR-010） |
| `audit_logs` | 账号、模型目录与对局运维操作审计 |

2026-10-15 撤除 DSL 时删掉了 `games`、`game_versions`、`workflow_definitions`、`ai_usage_ledger` 与 `agent_model_bindings`：游戏身份与版本回到代码里，模型目录留在 `providers`/`provider_models`。`game_instances.game_version_id` 保留为纯文本（对局自报的代码版本），不再有外键。

2026-10-15 第八轮又把租户层整体删掉（ADR-008）：`tenants`、`tenant_memberships`、`tenant_secrets`、`player_actions`、`outbox_events` 五张表与所有 `tenant_id` 列、RLS 策略一并撤除——它们在当时的产品形态下不产生价值（唯一租户是常量 `PLATFORM_TENANT_ID`），却让每个查询、每个唯一键、每张新表都带着恒定成本。删除后剩 11 张表。

2026-10-15 第九轮再删掉三张（ADR-009）：`game_snapshots`（与 `state_json` 重复的历史副本）、`pending_commands` 与 `scheduled_jobs`（唯一消费者是尚未定案的实时推送与延迟副作用），以及它们唯一的生产者契约 `ExternalCommand`。对局只剩三张表：`game_instances`、`game_participants`、`game_events`。合计 8 张表：账号 2、模型目录 2、对局 3、审计 1。

关键唯一约束：

```text
(instance_id, sequence) on game_events        -- 顺序靠序号，不靠时间
(instance_id, idempotency_key) on game_events -- 追加幂等
(instance_id, participant_key) on game_participants
(instance_id, seat) on game_participants
(provider_id, model_id) on provider_models
```

`game_events` 是**对局记录**，不是重建状态的输入：`state_json` 是当前状态的真相，两者在同一事务里一起写，
读历史就是按 `sequence` 读行（ADR-010）。行里有 `type`、`participant_id`、`actor_user_id`、`step_id`、
`payload`，模型调用行另外带 `provider_id`/`model_id`/三个 token 计数（由约束保证要么全空要么全填）。
读历史不做行级过滤：能看这个对局，就能读到全部内容（含各席位的思考）。

状态用 `jsonb` 存（`game_instances.state_json`）；需要筛选、排序、关联和约束的数据使用普通关系列。对局相关的前缀（`instance_id`）都在每个唯一键里，所以跨对局的撞号不可能发生。

排队与超时不再有表：worker 改为"扫描 `running`/`waiting` 的对局、按实例加行锁、看它现在欠什么（玩家输入超时？AI 席位等回复？）"。代价是失败的退避与上限没有持久化位置，需要由游戏规则定义后果（契约里已有 `aiFailed`），这一条列入第九轮的已知取舍。

### 6.3 数据库和二进制资源决策

- PostgreSQL 是生产唯一权威数据库。
- 内核单测不需要数据库；涉及锁、事务隔离、`jsonb`、迁移和 worker 的测试一律使用 PostgreSQL。
- 本地完整开发通过 Docker Compose 启动 PostgreSQL；CI 同样运行 PostgreSQL 服务。
- 若“所有存储都进数据库”是硬要求，Beta 可用 `bytea` 保存小型资源，但必须设置单文件和总量上限。大文件会放大备份、复制和恢复成本，公开发布前应重新评估 S3 兼容对象存储；对象元数据和权限仍归 PostgreSQL 管理。

## 7. 编排库（LangGraph 等）的定位

DSL 撤除后，这个问题变简单了：**编排库是游戏代码的内部实现细节，不是平台组件**。

- 平台不依赖任何编排框架，数据库、API 和契约里不出现它们的类型。
- 游戏模块内部可以用任意方式组织逻辑：一个 `switch`、一个状态机库，或 LangGraph JS。这不影响平台能力，因为平台只通过 `GameModule` 接口与游戏交互。
- 平台的四条保证（对局身份、记录可查、写入幂等、信息不越权）由内核与数据库提供，不由游戏代码自己声明；编排库的 checkpoint 只是它自己的内部状态，永远不能成为业务真相。
- 多玩家等待：每个玩家的动作各写一行记录；达到全员、法定人数或超时条件后只推进一步，不能让每个玩家分别推进一步。

原本要用 LangGraph JS 的对照来决定"首版执行器"；随着 DSL 撤除，这个决策点不再成立（结论见 §16 第六轮）。

## 8. 现状与工作计划

### 8.1 现状（截至 2026-10-15）

平台目前只有**账号 + 模型配置**这一半，对局那一半还是空的：

| 能力 | 状态 |
| --- | --- |
| 账号与会话 | 可用：管理员建号/重置/**删除**、自助改密、不透明会话 + CSRF、审计 |
| 模型目录 | 可用：Provider/Model 增删改/**删除**与连接测试（供应商有模型时拒绝删除）、凭据 AEAD 加密、密文不回读 |
| 控制台 | 账号与模型页面：登录、改密、大厅、用户（建/停/角色/重置/删除）、模型（增删改/测试/删除） |
| 中立内核 | 有接口没消费者：`GameModule`/`GameRegistry`/`projectPlayerView` 都还没有调用方 |
| 对局数据 | 三张表在，但 `game_participants` 与 `game_events` **零代码引用**（没有写入/读取函数） |
| worker | 空转：循环在位，没有"该推进哪一局"的扫描 |
| 对局 HTTP | 不存在 |
| 游戏模块 | 不存在（`games/` 目录未建，运行时注册表是空的） |
| AI 席位 | 只剩模型目录与凭据，没有调用链与用量记录 |
| 实时推送 | 没有 |

一句话：**现在能做的是"建账号、配模型"，做不了"开一局"。**

### 8.2 工作计划

按依赖顺序分五个里程碑，每个里程碑结束都能演示一个闭环。编号 `M{里程碑}-{序号}`。

#### M1 让一局跑起来（无 AI）

目标：两个真人席位能跑完一整局。

- [x] `M1-01` **写入路径**（`src/server/match/service.ts`）：按实例取行锁 → 跑 `transition` → 追加记录行（平台分配 `sequence`，游戏产出派生事件）→ 收敛固定席位状态 → 按 `current_sequence` 乐观推进，全部在同一事务内。创建对局同路：先落实例与席位，再把 `instanceCreated` 当一次普通写入应用。
- [x] `M1-02` **三个 HTTP 接口**（`src/server/routes/matches.ts`）：`POST /v1/instances`、`POST /v1/instances/:id/events`（要求 `Idempotency-Key`）、`GET /v1/instances/:id`（自己席位的投影 + 完整记录；管理员可读但无投影）。
- [x] `M1-03` **第一个游戏模块**：`src/server/games/undercover.ts`（「谁是卧底」，4 席起步，轮流描述 + 投票淘汰）+ 回归夹具（`undercover.test.ts`：确定性发牌、阶段推进、隐藏信息断言、非法动作、未知事件类型被忽略）。狼人杀随后。
- [x] `M1-04` **worker 的实例扫描**：当时判断「等待点还没有时限时不需要它」，并入 `M2-04` 交付 —— 扫描 `running`/`waiting`、按实例取行锁、替待办席位里的 AI 走一步（`src/server/worker.ts` + `match/ai-seat.ts`）。
- [x] `M1-05` **并发与幂等测试**：同键重复提交（单元 + 集成 + 实机）、两个请求同时提交（行锁串行化、`sequence` 不重不漏）、同一 key 并发只落一行。

验收（已通过）：创建一局 → 席位轮流提交 → 跑到结束；重复提交不产生重复记录；隐藏信息断言通过；两个并发提交被行锁串行化、`sequence` 不重不漏；同一 `Idempotency-Key` 并发只落一行。

#### M2 AI 席位

目标：AI 坐进席位，和真人走**同一条写入路径**，并且 prompt 前缀在对局内保持稳定。

- [x] `M2-01` **动作契约**：`waiting.actions`（允许的名字子集）+ `GameModule.actions`（静态目录）；删掉 `waiting.kind` 的 `'ai'`；`undercover` 填目录（`seatMessage` / `vote`）并在每个等待点声明子集。
- [x] `M2-02` **模型客户端**：OpenAI 兼容的 `chat/completions`（支持 `tools`），复用 SSRF 防护与超时/体积上限，解析 `content` / `tool_calls` / `usage`；传输层可注入，便于测试。
- [x] `M2-03` **prompt 组装（前缀稳定）**：`tools` 全量目录、`system` 规则 + 人格 + 私有状态、尾部指令写当前回合与允许动作；跨回合逐字保持稳定部分不变。
- [x] `M2-04` **worker 扫描 + 席位执行器**（并入原 `M1-04`）：扫 `running`/`waiting` 的对局 → 按实例取行锁 → 待办席位里是 AI 的就替它走一步：组装 prompt → 调模型 → 按允许集校验工具调用 → 拒绝以工具结果回灌 → 走 `submit` 写入路径 → 写 `aiCall` 行（一次调用一行）。
- [x] `M2-05` **失败与上限**：单次调用超时、每回合迭代上限、模型不可用 → `aiFailed`，后果由游戏规则定义。

验收：一个 AI 席位在「谁是卧底」里跑完整局（描述 + 投票）；每次调用都有行与用量；越界工具调用被纠正且回合不中断；模型连续失败不会让对局卡死。

#### M3 对局界面

目标：人能在浏览器里玩完一局。

- [x] `M3-01` **房间页**：席位圆桌、当前等待点、自己的可用动作（三栏单屏，见 `m3-room-redesign-plan.md`）。
- [x] `M3-02` **记录页**：按 `sequence` 的完整记录，做成右栏日志（基本/详细两档，含 AI 的思考与用量）。
- [x] `M3-03` **管理员对局运维**：暂停/恢复/取消（写 `status` + 审计，不写成游戏事件）。
  运维是**独立页面** `/admin/matches`，不进玩家页面；管理员在别处就是普通玩家，能占席位也能旁观。
  大厅与房间对所有登录用户开放：占席位的行动，没席位的旁观（公开状态 + 完整记录，拿不到私有信息与动作）。

验收：两个真人 + 一个 AI 在浏览器里跑完一局。

#### M4 工程门禁与运维

目标：让 CI 与运维能挡住回归。

- [x] `M4-01` **lint 与格式检查进 CI**：Prettier 管格式、ESLint 管对错（不做类型感知），CI 硬门禁。
- [x] `M4-02` **密钥轮换流程**：`pnpm rotate-credential-key` + 真库演练 + `docs/operations/credential-rotation.md`。
- [x] `M4-03` **处置依赖告警**：`fastify` 升级 + `fast-uri` override，`pnpm audit --prod` 归零并进 CI 硬门禁。
- [x] `M4-04` ~~E2E 进 CI；删除根脚本 `test:golden:legacy`~~ — 已完成：CI 装了 chromium、bootstrap 了 e2e-root 管理员并跑 Playwright；断链脚本已删。
- [x] `M4-05` **备份恢复演练**（`pnpm backup-restore-drill` + 演练记录）与部署手册重写（`docs/operations/deployment.md`、`backup-restore.md`）。

验收：CI 全绿且包含 lint；密钥轮换演练过一次。

#### M6 谁是卧底成为正式游戏（核心，优先于 M5）

目标：把平台的第一个正式游戏做扎实 —— 有顺序、有讨论、有身份公开、有 AI 表现规范；M5 的外围工程（容量、指标、
安全评审、合规）按「只考虑核心功能」的决定推后。

- [x] `M6-01` **席位人格**：平台内置人格池，每局开始时按种子随机发放（与角色无关），局内不变。
  `game_participants.persona jsonb` + `game_instances.persona_public boolean`（迁移 `0003`）。
  可见性：**MBTI 永远隐藏**、**性别永远公开**、其余字段由创建对局时的开关决定。
- [ ] `M6-02` **prompt 结构化**：system 分节（规则 / 你的角色 / 你的位置与席位表 / 其他角色与可见人格 / 你的人格 /
  只有你知道的信息 / 行动约束），回合消息分节（现在 / 上轮各席位结算状态 / 本轮进展 / 其他人的发言 /
  允许动作 / 输出要求）。前缀仍在局内逐字不变。
- [ ] `M6-03` **阶段机与轮次强制**：描述（必发言，无跳过）→ 讨论（≤3 轮，可调跳过工具）→ 投票（必投，无跳过）。
  第 3 轮结束由规则接管：允许动作收窄为只有投票，第 4 次发言被拒。轮次只统计本轮涉及的席位。
- [ ] `M6-04` **席位引用统一**：动作参数里声明为席位的字段，平台同时接受席位名与 participantId；
  席位表进 system，AI 不再靠猜 id 投票。
- [ ] `M6-05` **规则细化**：顺序发言、平票重投、淘汰后公开身份、出局不再发言、每局结束给出 AI 评分（公开 `summary`）。
- [x] `M6-07` **词对来自分类**：游戏不再内置词库；`setup` 声明一个 `kind: "category"` 字段与两个 `from: "pair.*"`
  字段，创建时由平台的模型按分类生成词对（工具调用返回结构化结果）并**直接发牌**——建局的人看不到词，
  所以知道答案的问题不存在。生成失败就拒绝开局并说清原因；创建对局按账号限流（每分钟 10 次，因为一次建局
  可能花一次模型调用）。真机验证走 `pnpm check:model-call` 与演示环境；e2e 里用 API 建局并显式给词
  （测试环境没有模型，回环供应商被 SSRF 规则拒绝，无法打桩）。
- [ ] `M6-06` **输出风格**：规则与回合指令里允许发言带（笑）（小声）这类语气，用于误导与计策；平台原样透传。

验收：同一局两次调用的 system 哈希一致；MBTI 从不进别人的 prompt、性别总在、其余字段随开关；人格与角色分布无相关；
描述与投票阶段没有跳过工具且不处理就推不动；讨论第 4 次发言被拒、投票不能空过；跳过不顶掉发言气泡；
投票一次命中；括号语气进记录不影响判定；两个真人 + 两个 AI 在浏览器里跑完一局。

#### M7 房间是对局前的全局概念（方案见 `room-design.md`）

目标：把「建房」与「开局」分开。房间先存在（定游戏、定时人数与席位布局），人来了占位、准备，
房主开局才生成对局；**AI 在房间里只是占位，不生成、不消耗模型调用**。

- [ ] `M7-01` 迁移 `rooms` + `room_members`；房间状态 `open → started/closed/cancelled`。
- [ ] `M7-02` 游戏声明 `minSeats` / `maxSeats`，建房时按区间校验（谁是卧底 3–12）。
- [ ] `M7-03` 房间接口：建房 / 列表 / 详情 / 加入 / 准备 / 离开（房主移交）/ 开局 / 取消。
- [ ] `M7-04` 开局：校验真人席位全占且全部准备 → 生成词对 → 建实例与席位（AI 此时才生成）→ 房间转 `started`；
  限流从创建对局挪到开局。
- [ ] `M7-05` 界面：`/rooms/:id` 未开局为席位表与准备，开局后即对局房间；大厅分「开放中的房间」与「我的对局」。
- [ ] `M7-06` 测试与验收：占位不生成、准备门槛、单人开局、房主移交、席位越界被拒；
  e2e 走完 建房 → 加入 → 准备 → 开局 → 对局。

#### M5 公开 Beta（推后）

目标：可观测、可放量。

- [ ] `M5-01` **容量与稳定性**：目标 100 个活跃对局 / 1000 在线 / 每秒 20 次动作。
- [ ] `M5-02` **指标与告警**：延迟、错误率、卡住的对局、AI 成功率与 token 用量。
- [ ] `M5-03` **安全评审**：认证、授权、提示词注入、日志隐私、供应链。
- [ ] `M5-04` **条款与合规**：隐私说明、数据导出与删除流程。

验收：满足 §10 全部门槛。

#### 首版明确不做

实时推送与断线恢复、多区域部署、支付与结算、第三方游戏分发与沙箱、可视化编辑器。并发对局到数千时再按实测把队列加回来（ADR-009）。

## 9. 旧数据与切流（不适用）

Greenfield：**不迁移旧数据、不做双轨切流、不引入兼容层**（2026-10-15 决定）。旧系统（`backend/`、`frontend/`）只作领域参考，新平台直接对外提供。

若将来确有必须保留的历史数据，那是一次独立的数据导入任务，不是平台架构的一部分。

## 10. 发布门槛（Definition of Release Ready）

以下条件全部满足才进入公开 Beta：

### 正确性与恢复

- 重复提交与重试不会重复结算（幂等键与顺序号唯一约束承担）。
- 任意服务进程重启后，已提交的写入不丢失；进程重启只影响正在进行的模型调用。
- 任何时刻都能按 `sequence` 读到该对局的完整记录。
- AI 超时、结构化输出错误和供应商不可用不会让实例永久卡住。

### 安全

- REST、后台任务和管理入口都有未认证与非管理员访问的自动化测试。
- 没有由客户端直接决定的可信 `user_id` 或角色。
- 玩家投影与 AI prompt 不泄露无权查看的隐藏状态（投影由内核 fail-closed 执行；prompt 由 harness 按席位组装）。
- 凭据加密存储，日志脱敏，敏感操作有审计记录。
- 发布时没有未处置的 P0/P1 安全缺陷。

### 工程质量

- CI 的 lint、类型检查、单元、PostgreSQL 集成、契约、E2E 和构建全部绿色。
- 迁移在生产数据副本上验证，升级与回滚路径均演练（含 `.down.sql`）。
- 容器、CI 和本地支持的 Node/PostgreSQL 版本一致并有明确生命周期。
- 契约（契约 schema 与事件类型词表）有版本策略；游戏代码的 `gameVersionId` 与对局行绑定。

### 运维与容量

- 达到 §8.2 M5-01 的容量目标并保留余量；AI 时间不计入同步 API 延迟。
- 对动作处理延迟、错误率、卡住的对局、AI 成功率与 token 用量、数据库连接设有指标及告警。
- 完成一次备份恢复演练，记录 RPO/RTO 实测结果。
- 有部署、回滚、卡局处置、密钥轮换和数据导出/删除手册。

## 11. 测试矩阵

| 层级 | 运行数据库 | 重点 |
| --- | --- | --- |
| 内核单测 | 无数据库 | 投影、转换、确定性 |
| 游戏模块单测 | 无数据库 | 角色、阶段、动作合法性、胜负、隐藏信息 |
| Repository 合约测试 | PostgreSQL | 约束、事务、行锁、迁移与回滚 |
| 对局写入集成测试 | PostgreSQL | 幂等、并发、乐观推进、记录顺序 |
| API 契约测试 | PostgreSQL | 身份、错误模型、幂等与重复提交 |
| 对局端到端测试 | PostgreSQL | 完整对局、隐藏信息、AI 席位 |
| E2E | 完整 Compose | 登录、建 provider/model、创建并跑完一局 |
| 安全测试 | 完整 Compose | IDOR、未授权读写、prompt 注入、权限提升 |
| 容量与故障测试 | 类生产 PostgreSQL | 峰值动作、worker 崩溃、数据库抖动、AI 超时 |

集成测试必须运行真实 PostgreSQL；内存或内存库通过不算过关。

## 12. 风险与缓解措施

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 游戏代码绕过平台保证（直接写库、泄漏隐藏状态） | 泄漏、脏状态 | 游戏模块只拿到状态与事件、只能返回状态与事件；投影由内核统一执行（fail-closed）；代码评审与隐藏信息断言 |
| 游戏代码不确定（时间/随机/网络） | 同一事件序列得到不同状态，记录与状态对不上 | `transition` 纯函数约束 + 内核测试；随机种子与时间作为显式事件输入 |
| 隐藏信息泄漏 | 严重作弊和隐私事故 | 权威状态与玩家投影分离；按角色属性测试；日志和 prompt 脱敏 |
| AI 调用拖垮对局或成本 | 卡局、费用不可控 | 平台提供模型目录与凭据；失败后果由游戏规则定义（`aiFailed`）；每次调用的用量随行入库（ADR-010），成本报表待做 |
| 大资源存入 PG | 备份和复制膨胀 | 首版大小/配额限制；公开发布前评估对象存储 |
| 一次性重写前后端 | 交付周期失控 | 按新实例灰度 |

## 13. 下一步

见 §8.2：M1 已完成（其中 `M1-04` worker 扫描并入 M2），当前在做 **M2「AI 席位」**。

## 14. 项目管理约定

- 每项任务进入开发前必须写明输入、输出、测试和数据库影响。
- 每个数据库变更必须可重复执行并带 `.down.sql` 回滚体；greenfield 阶段允许直接重写迁移，不留兼容路径。
- 每个游戏模块必须带回归夹具（标准对局 + 期望记录序列），并证明隐藏信息不漏。
- 每个写入必须能回答三件事：谁触发的、幂等键是什么、失败重试会不会重复。
- 每个阶段结束进行一次出口评审，不以“代码已合并”代替验收结果。
- 工作看板建议使用任务编号 `P{phase}-{sequence}`，缺陷使用 `BUG-{sequence}`，架构决策使用 `ADR-{sequence}`。

## 15. 技术决策与当前状态

| 决策 | 结论 | 依据 | 当前状态 |
| --- | --- | --- | --- |
| 生产数据库 | PostgreSQL only | `P0-01` | 已落地（ADR-001） |
| API 框架 | Fastify | `P0-01` | 已落地（`apps/platform`） |
| Schema 工具 | Zod 或 TypeBox 二选一 | `P0-01` | 已落地：Zod（ADR-003） |
| 数据访问层 | Drizzle 或 Kysely 二选一 | `P0-01` | 已落地：Kysely（ADR-004） |
| 首版运行时 | 无编排运行时 | `P0-05` | 已关闭：编排库是游戏代码的内部选择（§7） |
| 二进制资源 | PG `bytea` + 严格上限；发布前复审对象存储 | ADR-005 | 决策保留；尚无使用点 |
| 身份方案 | 自建账号 + 不透明会话 | `P2-01` 前 | 已落地（`routes/platform-auth.ts`） |
| 旧数据与切流 | 不迁移、不双轨 | 2026-10-15 | 已作废（见 §9） |
| Beta 容量目标 | 默认 100 房间 / 1000 在线 / 20 动作每秒 | `P0-06` | 目标保留；容量测试未做 |

## 16. 决策日志

> 本文按轮次记录决策与当时的核验结论，**最新一轮为准**。现状与工作计划在 §8。
> 早期任务编号（`P0`–`P7`）属于已废止的"迁移式"分解，只在本节的轮次记录里出现。

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

### 第九轮（2026-10-15）：对局只剩三张表（ADR-009）

**决策**：删除 `game_snapshots`、`pending_commands`、`scheduled_jobs`，以及唯一会给后两张表生产数据的契约 `ExternalCommand`（`transition` 的输出只剩 `events`）。对局侧只留 `game_instances`、`game_participants`、`game_events`；全库 8 张表。

**理由**：快照与 `instances.state_json` 是同一份状态的两次存储；队列表提供的是"刚好执行一次、可以晚点、失败能重试"，而它当前既没有生产者也没有消费者，实时推送本身还被 `docs/mvp-scope.md` 推迟。没有队列之后，外部命令通道没有目的地，留着就是死代码。

**连带改动**：

- worker 不再领取队列，改为"扫描 `running`/`waiting` 的对局 → 按实例取行锁 → 看它现在欠什么"。扫描本身随对局运行时一起落地，当前循环无事可做。
- 排序只由 `sequence` 决定（`occurred_at` 只用于展示与超时判断）；`unique (instance_id, sequence)` 是并发写入的兜底。
- 时间只通过等待点表达：`waiting.deadlineMs` 加上一步事件的时间就是截止时刻，平台据此产生 `timerExpired`。

**本轮确认的存储要求**（留给 AI 席位实现时执行）：

- **prompt 不入库**（它可由事件日志重算）。
- **每次模型交互必须入库**，一次调用一行。
- **token 用量必须入库**（至少输入/输出/合计），与那次交互同一行。
- 模型回复原文与 provider 返回的签名字段一并存进该行 payload（带 tools 的请求要求原样回传）。

**已知取舍**（接受并记录）：模型调用的退避与上限没有持久化位置，失败后果由游戏规则定义（契约里已有 `aiFailed`）；需要"任意延迟事件"的游戏不能再表达，只能用等待点加时限；对局规模到数千并发时需要重新引入队列。

### 第十轮（2026-10-15）：`game_events` 定型为对局记录（ADR-010）

**决策**：把"重放"的两种含义分开——本项目要的是"让用户看到整局完整历史"，不是"用事件重算状态"。因此
`state_json` 是当前状态的真相（写路径），`game_events` 是记录（读路径），两者同事务写入。

**行形状**：`sequence`（对局内唯一总序）、`type`、`participant_id`、`actor_user_id`、`step_id`、
`idempotency_key`、`occurred_at`、`payload`，加模型调用行的 `provider_id`/`model_id`/三个 token 计数。
不设 `kind` 判别列（没有重放要保护），不设受众列（能看对局就能看全部）。

**其它确认**：`replayEvents` 与 `TransitionFn` 删除（`transition` 的签名留在 `GameModule` 接口上）；一次模型调用一行、回合结果另写一行；用量由 `num_nonnulls(...) in (0,5)` 保证要么全空要么全填；
`participant_id` 用复合外键绑到同一对局的席位；`game_participants` 因此补 `unique (instance_id, id)`；
按序读由唯一键承担，不再另建索引。

**`replayEvents` 的处置**：**删除**。它唯一的用途是用记录重建状态并与 `state_json` 对账；既然记录不是重建状态的输入，
这条路径就不该存在——留着它会让"日志可以重算出状态"变成一种无人维护的承诺。

### 第十一轮（2026-10-15）：账号与模型这半边收口（ADR-008/009/010 之后）

**做的事**：删掉只检查"有没有配 DATABASE_URL"的假 `/health` 探针（保留 `/health` 一个真路由）；补齐 admin-only 的删除接口（账号、供应商、模型）并接进控制台；CI 里跑 Playwright；前端任何 401 回登录页；删掉零调用的 `getProviderModelWithProvider` 与断链的 `test:golden:legacy`。

**发现并修掉的真实缺陷**：`audit_logs.actor_user_id` 原本是严格外键，而任何登录过的账号都有审计行——于是"删除账号"实际上永远会被拒。改成 `on delete set null`：审计行保留（失去 actor 链接），而对局记录（`game_participants`/`game_events`）仍然阻止删除。策略因此是：**出现在对局里的账号不能删，只能停用**。

**为什么删 `/ready` 而不是修它**：探针要的是"这个进程能不能服务"，而配置检查不回答这个问题；宁可没有，也不要一个永远说健康的信号。健康检查只有 `GET /health`。

### 第十二轮（2026-10-15）：去掉强制改密

**决策**：删除首登强制改密。`users.must_change_password` 列、`PASSWORD_CHANGE_REQUIRED` 门禁、`requirePasswordChanged` preHandler、前端的强制跳转与"需改密"列全部移除；改密页保留为自助功能（页头加了入口），管理员重置密码仍然可用且会撤销该账号的全部会话。

**理由**：强制改密属于"给不信任的初始密码加一道闸"，而这个平台的账号全部由管理员创建、且没有自助注册，闸门只带来额外一次交互和一条需要维护的状态位。安全性不因此下降：初始密码仍然只经管理员渠道传递、不落日志、不可回读；改密本身仍会撤销所有旧会话。

**连带**：`users` 表少一列；登录后直接进大厅；e2e 首个用例改为"登录后落地大厅"，并新增一条"用户自助改密 → 改完进大厅 → 访问管理页被弹回"。

### 第十三轮（2026-10-15）：M1 完成，一局真的能跑

**交付**：写入路径（事务 + 行锁 + 平台分配序号 + 派生事件）、三个接口、第一个游戏模块「谁是卧底」、以及与它配套的回归夹具；并发与幂等都有测试。实机验证：4 个账号在 `POST /v1/instances` 建局、各自读到（且只读到）自己的词、轮流描述、投票淘汰卧底、对局收尾；`Idempotency-Key` 重复提交返回 `replayed: true` 且不新增行。

**过程中被现实纠正的两个设计**：

1. **`visibility` 必须是状态的函数**。原先它是模块级的静态映射，但"只给某席位看得见的变量名"里带着运行期才生成的 `participantId`，静态写法根本表达不出来。改成 `Visibility | ((state) => Visibility)`，内核多十行，AI 席位将来靠它拿到自己的秘密。
2. **席位状态要跟着状态走**。`game_participants.status` 是给查询和写入前检查用的冗余副本，原先只在创建时写一次，淘汰后就成了谎话。现在每次写入结束会把变化的席位状态收敛回表里（实测：被投出的卧底在表里是 `eliminated`）。

**同时定下的两件小事**：`game_instances` 拆成 `game_id` + `game_version`（按 id 找模块，按 version 钉代码版本）；`TransitionResult.events` 明确是"额外事件"，入站事件由平台追加，游戏不得回显。

**还没做**：worker 的实例扫描（等 M2 的 AI 席位一起）、狼人杀、对局界面。

### 第十四轮（2026-10-15）：AI 席位的 prompt 布局按"前缀稳定"定稿

**背景**：原先打算"工具集跟着等待点走"，好处是结构上不可能阶段越界，但代价是每次换阶段都会改写 `tools` 区块。缓存顺序是 `tools → system → messages`，工具表一动，后面整段转录全部失效——对局越长亏得越多。

**决策**：

1. `tools` 固定为**游戏动作全集**，`system` 固定为**规则 + 人格 + 该席位私有状态**，两者在对局内逐字不变；**当前回合与允许动作写进最后一条消息**（尾部变化不影响前缀命中）。
2. 阶段越界改为**在执行处校验**：允许集来自等待点，越界调用以工具结果回给模型，让它在本回合内改正；规则拒绝同样回灌为工具结果。
3. **动作即事件**：工具名 = 事件类型，参数 = payload，执行走 M1 的写入路径。真人与 AI 同一个入口。
4. 删掉 `waiting.kind` 的 `'ai'` 档：待办席位由等待点指名，是人还是 AI 看 `game_participants.control`。

**因此新增两处契约**：`GameModule.actions`（静态目录）与 `waiting.actions`（允许子集）；`M1-04`（worker 扫描）并入 `M2-04`。

### 第十五轮（2026-10-15）：M2 完成，四个 AI 席位真打完了一局

**交付**：worker 扫描（jsonb 包含检查，只挑"等待点里还欠 AI 席位"的对局）、席位执行器、以及一次回合的原子写入（`recordTurn`：`aiCall` 行必落，它请求的动作除非被规则拒绝否则同事务落；`recordFailure`：无动作写成 `aiFailed`）。模型绑定暂时取目录里第一个可用组合——游戏自己声明席位绑定的接缝就在 `chooseBinding` 这一个函数里。

**实机证据**（tokenhub / `deepseek/deepseek-flash`，4 个 AI 席位无人类）：

- 19 行记录走完全程：4 次描述 → `describePhaseEnded` → 4 次投票 → `votesRevealed` → 卧底（拿到"老虎"的 ai3）被 3 票投出，平民胜。
- 8 次模型调用全部落行，合计 **13,043 token**（prompt 8,014 + completion 5,029），每次调用 1.0–2.7k token。
- 隐藏信息没泄漏：ai1/ai2 的思考里只有自己的词与他人发言，最后两人都投中了卧底。
- 拒绝回灌、空动作失败、`TOKEN_BUDGET_EXHAUSTED` 三条路径由集成测试（真库 + 假模型）覆盖。

**实测得到的两条实现约束**（都已落地）：

1. **`max_tokens` 对推理模型是陷阱**：400 token 会全被思考吃掉、返回空动作（`finishReason=length`）。默认给 2048，并且把"没有工具调用"当成失败回合（`finishReason=length` 立即 `aiFailed`，纯文字回答先提示一次再重试）。
2. **思考必须跨轮原样回传**：provider 要求（带 tools 时）把 `reasoning_content` 在后续所有请求里带上，实测 8 次调用都没有 400。代价是 **prompt 会随对局的思考历史增长**（每次调用约 1.0–2.7k token），所以"前缀逐字稳定"这条不只是省钱技巧，是长局能跑下去的前提。

**尚未验证**：provider 是否真的对稳定前缀给了折扣（用量里没有 cached token 字段，"省了多少"目前无法从数据看出来）；成本指标属于 M5。

## 17. 参考资料

- [PostgreSQL JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Zod](https://zod.dev/)、[Kysely](https://kysely.dev/)
