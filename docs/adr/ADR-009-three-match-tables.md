# ADR-009：对局只留三张表，不设队列与快照

- 状态：Accepted
- 日期：2026-10-15
- 范围：对局数据模型、worker 的工作来源、内核的副作用契约

## 背景

租户层删除（ADR-008）之后，对局侧还有六张表：`game_instances`、`game_participants`、`game_events`、
`game_snapshots`、`pending_commands`、`scheduled_jobs`。后三张都是"设计过但从未被使用"：

- `game_snapshots` 与 `game_instances.state_json` 保存的是同一份状态的两个副本——后者已经是当前状态的物化，
  前者只是历史点副本。只有"要看历史某点的状态"或"重放太慢"才需要它，而两者都没有实测依据。
- `pending_commands` / `scheduled_jobs` 提供"刚好执行一次、可以晚点、失败能重试"，它们唯一的生产者是
  `ExternalCommand`（内核输出的副作用），消费者是尚未存在的对局运行时与实时推送；推送本身已被
  `docs/mvp-scope.md` 列为不做。

## 决策

1. **删表**：`game_snapshots`、`pending_commands`、`scheduled_jobs`。对局侧只剩 `game_instances`、
   `game_participants`、`game_events`；全库 8 张表。
2. **删契约**：`ExternalCommand` 与 `parseExternalCommand` 随之删除，`TransitionResult` 只剩
   `{ state, events }`。内核产出的事件由平台按顺序追加，不再经过"命令"这一层间接。
3. **worker 的工作来源改为状态推导**：扫描 `running`/`waiting` 的对局，按实例取行锁，看它当前欠什么
   （玩家输入超时？AI 席位等回复？），推进它。没有队列，也就没有领取、租约与死信。
4. **排序只用序号**：`sequence` 是唯一排序键，`unique (instance_id, sequence)` 是并发写入的兜底；
   `occurred_at` 只用于展示与超时判断。
5. **时间只用等待点表达**：`waiting.deadlineMs` 加上一步事件的时间即截止时刻，平台据此产生
   `timerExpired`。不再支持"任意延迟事件"。

## 理由

队列与快照不是错的设计，是**早于需求的设计**：它们在没有生产者的情况下被写进 schema，于是每个查询、
每个新表都要背着一套领取/租约/状态机词汇。删掉之后，"谁该干活"这个问题变成一句可读的话：状态说它
在等什么，就去做什么。

## 后果

- worker 失去"领一批、去重复、失败重试"的原子原语，改为扫描 + 行锁。几十到几百个并发对局没有问题；
  数千个并发对局时需要重新引入队列（届时是按实测需求引入，而不是按想象）。
- **模型调用的退避与上限没有持久化位置**。失败后果由游戏规则定义（契约里已有 `aiFailed`）：跳过该席位、
  换人或者中止对局，都是游戏的业务决定，而不是平台的重试策略。
- 需要"任意延迟事件"的游戏不再能表达，只能用等待点加时限。这是当前游戏范围下可接受的限制。
- 回放没有快照加速，长对局每次读取都要重放。`state_json` 作为缓存仍然承担读路径，所以这条暂时不痛。

## 与 AI 席位的关系（本轮确认的存储要求）

- **prompt 不入库**：它可以从事件日志重算。
- **每次模型交互必须入库**，一次调用一行。
- **token 用量必须入库**（至少输入/输出/合计），与该次交互同一行。
- 模型回复原文与 provider 返回的签名字段一并存进该行 payload。
