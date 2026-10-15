# ADR-010：`game_events` 是对局记录，不是重建状态的输入

- 状态：Accepted
- 日期：2026-10-15
- 范围：`game_events` 表、`GameEvent` 契约、读历史的语义

## 背景

`game_events` 最初是按"事件溯源"设计的：事件是真相，状态由重放推导，快照用来加速重放。ADR-009 删掉快照与队列之后，
这个定位需要重新说清楚——因为"重放"这个词在这个项目里有两种含义：

1. 用事件重算出状态（机制）；
2. 让用户看到整局的完整历史（产品）。

本项目要的是第 2 种。用户不关心状态能不能由事件重算，只关心历史能不能完整地看。**因此
`game_instances.state_json` 是当前状态的真相（写路径），`game_events` 是记录（读路径）**，两者在同一个事务里一起写。

## 决策

`game_events` 的行形状：

```text
id, instance_id, sequence, type,
participant_id, actor_user_id, step_id,
idempotency_key, occurred_at, payload,
provider_id, model_id, prompt_tokens, completion_tokens, total_tokens
```

1. **`sequence` 是对局内唯一总序**，所有行共用一套编号，历史就是"按它读"。`occurred_at` 只用于展示与超时判断，
   永远不是排序键；`unique (instance_id, sequence)` 是并发写入的兜底。
2. **行类由 `type` 表达，不设 `kind` 判别列**：没有重放要保护，多一列就是和 `type` 重叠的第二套真相。
   平台自己写的类型在契约里列出（`platformEventTypes`），列上没有 check——词表属于规则，不属于平台。
3. **一次模型调用一行**（`type = aiCall`），行里带用量与思考；回合的**结果**另写一行（`aiResultReceived`）。
   所以"每次交互必须入库"成立，历史里既有过程也有结果。
4. **用量进列**：`provider_id` / `model_id` / 三个 token 计数，并由 `num_nonnulls(...) in (0,5)` 约束保证
   要么全空、要么全填。费用统计是一次 `sum`，不需要挖 jsonb。
5. **`participant_id` 与 `actor_user_id` 分开**：席位是谁（AI 也有），背后的人是谁（AI 为空）。
   `(instance_id, participant_id)` 是复合外键，行不能挂到别的对局的席位上；`game_participants` 因此多了
   `unique (instance_id, id)`。
6. **`payload` 装该行自己的内容**：回复原文、思考（含 provider 的签名字段，因为带 tools 的请求要求原样回传）、
   工具调用与结果。**prompt 不入库**——它可由记录重算。
7. **读历史不做行级过滤**：只要能查看这个对局，就能读到全部内容（含各席位的思考）。
   唯一的过滤是"能不能看这个对局"这一层授权。AI 席位之间的"只让你看到别人的发言"是 **prompt 组装**的事，
   属于 harness，不是读接口的事。
8. **`step_id` 由平台在追加时从状态抄一份**，用于"第几回合发生了什么"；游戏不必自己往 payload 里塞回合号。

## 后果

- 没有 `kind`、没有受众列、没有快照表、没有队列表。读历史就是一条带 `order by sequence` 的查询。
- **`replayEvents` 与 `TransitionFn` 已删除**。它唯一的用途是用记录重建状态、与 `state_json` 对账；既然记录不是重建状态的
  输入，这条路径就不该存在——留着它会让"日志可以重算出状态"变成一种无人维护的承诺。`transition` 的签名留在
  `GameModule` 接口上，确定性由"它是纯函数"这条约束保证。
- 隐藏信息的保护只剩一处机制：`projectPlayerView`（状态变量的三档投影，失败关闭）。历史记录本身是全可见的，
  这一点是明确接受的取舍：**进行中的对局里，参赛者若被允许查看历史，就能读到对手的思考**。若某个游戏不能接受，
  它必须在游戏规则层面表达（例如把秘密放状态变量、由投影保护），而不是指望日志过滤。
- `game_events` 上两条索引即够：唯一键 `(instance_id, sequence)` 服务按序读，`(instance_id, participant_id, sequence)`
  服务"某席位自己的历史"（AI 席位下一次 prompt 的来源）。
