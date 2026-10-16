# M3 对局界面 —— 执行计划

落地 `platform-migration-plan.md` 的 M3：人能在浏览器里玩完一局（房间页、记录页、管理员对局运维）。
界面按 `ui-framework-spec` 规范：只用 Element Plus 组件与其主题变量，颜色与间距一律走 `styles/tokens.css` 的语义令牌，不覆盖框架 DOM。

## Goal

浏览器里能建局、能玩、能看记录。验收标准（文档原文）：**两个真人 + 一个 AI 在浏览器里跑完一局**。

## Approach

1. 先把界面缺的三样数据补上：对局列表、游戏目录、生命周期改写。前两者是「进得去房间」的前提，第三个是 M3-03。
2. 契约改动只有两处：动作参数的形态（`args` 从 `名称 → 说明` 变为 `名称 → {说明, kind}`），以及 `game_events` 行的对外类型集中到 `shared`。
3. 房间页与记录页共用一个路由 `/matches/:instanceId`，两个 `el-tab-pane`；数据来自同一次 `GET /v1/instances/:id`。
4. 动作表单按游戏目录渲染：`kind: "seat"` 的参数渲染席位下拉，其余渲染文本框。平台不写任何游戏规则。
5. E2E 用两个真人席位走浏览器；AI 席位由 worker + 真实 provider 手工跑通（回环地址被 SSRF 防护拦死，不可能有本地假 provider）。

## Impact

| 工作对象 | 改动 |
|---|---|
| `apps/platform/src/shared/domain.ts` | 新增对局详情/列表/记录的对外类型与 schema、`ActionArg`、生命周期请求 schema |
| `apps/platform/src/server/game/module.ts` | `ActionDefinition.args` 的值带 `kind` |
| `apps/platform/src/server/games/undercover.ts` | `vote.target` 声明 `kind: "seat"` |
| `apps/platform/src/server/llm/prompt.ts` | 取参数的 `description`（形态变化） |
| `apps/platform/src/server/db/repositories.ts` | 新增 `listGameInstances` |
| `apps/platform/src/server/match/service.ts` | 新增 `list` / `listGames` / `setStatus`；类型改从 `shared` 引 |
| `apps/platform/src/server/routes/matches.ts` | `GET /v1/instances`、`GET /v1/games`、`PATCH /v1/instances/:id/status` |
| `apps/platform/src/browser/services/api.ts` | 对局的 5 个客户端方法 |
| `apps/platform/src/browser/views/LobbyView.vue` | 对局列表 + 新建对局 |
| `apps/platform/src/browser/views/MatchView.vue` | 房间页 + 记录页 + 管理员运维 |
| `apps/platform/src/browser/router/index.ts` | `/matches/:instanceId` |
| `apps/platform/e2e/phase1.spec.ts` | 大厅断言随实现更新 |
| `apps/platform/e2e/m3-match.spec.ts` | 浏览器打一局的验收 |

## Tasks

- [x] `M3-A` 契约：`shared/domain.ts` 增 `MatchSummary`/`MatchSeat`/`MatchRecordRow`/`MatchDetail`/`GameAction`/`ActionArg` 与 `updateMatchStatusRequestSchema`，从 `shared/index.ts` 导出。
- [x] `M3-B` 动作参数带 `kind`：`game/module.ts`、`games/undercover.ts`、`llm/prompt.ts` 同步。
- [x] `M3-C` 查询与写入：`db/repositories.ts` 的 `listGameInstances`；`match/service.ts` 的 `list`/`listGames`/`setStatus`（`setStatus` 写 `status` + `recordAuditLog`，不成游戏事件）。
- [x] `M3-D` 路由：`GET /v1/instances`、`GET /v1/games`、`PATCH /v1/instances/:instanceId/status`，补 `platform-routes.test.ts`。
- [x] `M3-E` 客户端与路由：`services/api.ts` 方法、`router/index.ts` 的 `/matches/:instanceId`。
- [x] `M3-F` 大厅：对局列表（状态、游戏、席位、当前等待点）+ 新建对局对话框（游戏选择、席位增删、真人/ AI）。
- [x] `M3-G` 房间页：席位表、当前等待点、我的可用动作表单、本局公开记录摘要。
- [x] `M3-H` 记录页：按 `sequence` 全量展示，AI 行含思考、工具调用与 token 用量。
- [x] `M3-I` 管理员对局运维：暂停/恢复/取消，危险动作二次确认。
- [x] `M3-J` E2E：两个真人席位在浏览器里推进一局 + 记录页断言；更新 `phase1.spec.ts`。
- [x] `M3-K` 门禁：`typecheck` / `test` / `build` / `test:db` / `test:e2e` 全绿。
- [x] `M3-L` 手工验收：worker + 真实 provider，两个真人席位在浏览器里与一个 AI 席位跑完一局。

## 修订（界面职责）

第一版把运维按钮放进了大厅行内与房间页，把「管理员」当成了一个界面上的角色。改法：

- 运维独立成页 `/admin/matches`（导航「对局运维」，仅管理员可见）；大厅与房间里不再有任何运维入口。
- 管理员在别处就是一个普通玩家：占席位、行动、旁观都按同一套规则走。
- 大厅对所有人列出全部对局，标注「我的席位」或「旁观」；房间对所有人开放，非席位用户拿到的是旁观投影
  （公开状态、等待点、席位、完整记录，`privateState` 为空、`availableActions` 为空、无规则文本）。
- 代价：`GET /v1/instances/:id` 不再有 `NOT_A_PARTICIPANT`，这正是 ADR-010「能看对局就能看全部内容」的直接结果 ——
  现在「能看对局」= 任何登录账号。若以后要收紧，改的是这条授权线，不是界面。

## 完成情况

- 门禁：`typecheck`（3 个项目）、`test` 155 例、`build`、`test:db`（含 `list` 与生命周期的真库用例）、`test:e2e` 8 例，全绿。
- 浏览器验收（worker + 真实 provider，`deepseek/deepseek-flash`）：两个真人席位（admin 的 s1、`m3-player` 的 s2）加一个 AI 席位 s3 在控制台跑完一局。
  12 行记录：`instanceCreated` → 2 次真人描述 → s3 的 `aiCall` + 描述 → `describePhaseEnded` → s3 一次被拒的投票与重试（两行 `aiCall`）→ 三票 → `votesRevealed`；卧底被投出，平民胜。3 次模型调用共 5,431 token。
- 席位私有信息按 `name:<participantId>` 寻址，界面只显示 `name`；`vote` 属 `seat` 语域，不进房间发言记录。

### 顺带发现

- 演示库里的 provider 凭据是用上一轮的临时主密钥封的，换回 `.env` 的密钥后解不开（`aiCall` 失败、记录里不出行）。已用 `TOKENHUB_API_KEY` 重新封一次，演示环境现在与 `.env` 对齐。
- `PlayerView.availableActions[].input` 没有消费者（AI 自己给参数，真人的席位由 `participantKey` 决定），房间页不再把它并进 payload；是否删掉留给 M4 决定。
- 浏览器的登录限流是「每账号 5 次 / 每分钟」，套件里每多登一次就顶到限额；`phase1` 的最后一个用例改用不存在的账号。
