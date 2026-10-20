# 稳定性收尾：最小席位、页面轮询、回合超时、worker 抢锁

公开 Beta 之前把「对局跑不下去」的四类问题按序修掉：废局规则、页面不自更新、无人推进的僵局、多 worker 重复调模型。

## Goal

- 3 席局不再可开：`MIN_SEATS` 提到 4，与「剩 2 人仍有卧底则卧底胜」的胜负条件配套。
- 页面自己动：对局页与房间页轮询，AI 的回合不需要人手点刷新。
- 僵局有出口：长时间没有推进的对局自动作废，记录里写清原因。
- 多 worker 安全：一个对局同时只有一个 worker 在调模型。

## Approach

1. `undercover.ts` 的 `MIN_SEATS` 3 → 4，补一条 `TOO_FEW_SEATS` 用例，文档里的席位区间同步。
2. 两个视图各自每 3 秒静默重读一次（不动 `loading`、不弹错），只在「对局/房间还开着」时轮询。
3. 新增 `MatchService.expireIdle`：按 `game_instances.updated_at` 找超时空转的对局，写一条 `timerExpired`
   记录（带等待席位与超时阈值）并把状态改成 `cancelled`，同时落审计。worker 每轮扫一次，
   阈值由 `MATCH_IDLE_TIMEOUT_MS` 控制（默认 30 分钟）。
4. `game_instances` 增加租约列 `ai_claim_until` / `ai_claim_worker`（迁移 0007）：worker 调模型前先抢租约，
   抢不到就跳过这一轮；回合结束释放。租约过期自动可被抢占，进程崩掉不会永久占坑。

## 说明

- 超时只由 worker 扫（`role=api` 不扫）：作废是运维动作，不该跟接口进程的请求量绑在一起。
- 租约长度按「一次模型调用的超时 × 每回合允许的调用次数 + 余量」算，共 210 秒；
  进程崩掉不需要清理，租约自己过期。

## Impact

- `apps/platform/src/server/games/undercover.ts`：最小席位数与说明。
- `apps/platform/src/browser/views/MatchView.vue`、`RoomView.vue`：轮询。
- `apps/platform/src/server/match/service.ts`：`expireIdle`。
- `apps/platform/src/server/db/repositories.ts`：超时查询、租约抢放。
- `apps/platform/src/server/main.ts`：worker 循环里扫描超时对局、传 `workerId`。
- `apps/platform/src/server/match/ai-seat.ts`：调用前抢租约、`finally` 释放。
- `apps/platform/migrations/0007_ai_turn_claim.sql`（含 `.down.sql`）。

## Tasks

- [x] `undercover.ts`：`MIN_SEATS = 4`；`undercover.test.ts` 补 3 席被拒用例。
- [x] `docs/platform-migration-plan.md`、`docs/room-design.md`：席位区间 3–12 → 4–12。
- [x] `MatchView.vue`：3 秒静默轮询，对局结束后停。
- [x] `RoomView.vue`：3 秒静默轮询，房间关闭后停。
- [x] `migrations/0007_ai_turn_claim.sql` + `.down.sql`：租约列。
- [x] `db/repositories.ts`：`claimAiTurn` / `releaseAiTurn` / `findIdleInstances`。
- [x] `match/service.ts`：`expireIdle`（写 `timerExpired`、改 `cancelled`、审计）。
- [x] `match/ai-seat.ts` + `main.ts`：抢租约、worker 扫超时、`MATCH_IDLE_TIMEOUT_MS`。
- [x] 测试：单个 worker 只跑一次、租约互斥与过期可抢、超时作废、轮询不打断输入。
- [x] 门禁：typecheck / 单测 / test:db / eslint / prettier / e2e。
- [x] 真机：两个 worker 同时在线跑一局，模型调用数不再冗余；挂机对局在超时后被作废。
