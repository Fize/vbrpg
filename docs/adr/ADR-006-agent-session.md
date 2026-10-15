# ADR-006：agent 会话是事件流的确定性派生（每席位一个 agent）

- 状态：Accepted
- 日期：2026-10-15
- 范围：AI 行为、游戏 DSL、数据模型

## 背景

旧 Python 系统的"agent 会话"是每个 agent 对象上的一个内存 list（`backend/src/games/base/agent.py` 的 `self.memory`），既没有持久化，也没有任何代码读取它；每次调用现拼 system + user 两条消息。平台要求"所有权威状态进入 PostgreSQL、进程内存只能当缓存"，因此会话不能是进程内状态。

同时需要回答：agent 的粒度是什么、会话活多久、重试算不算同一次会话。

## 决策

1. **每个席位一个 agent**：一个 role 的多个席各有独立 agent 与独立会话，不共享上下文。会话键是 `(instance_id, participant_id)`。
2. **会话不新增存储**：会话严格等于"该席位的事件流投影"。上下文由 `state` + 事件日志 + `projectPlayerView` 确定性派生，因此任何一局都能从事件日志重放出逐字节相同的 prompt，会话也随对局结束（`completed`/`cancelled`）自然结束。
3. **不允许 agent 私有笔记**：agent 不能写入平台看不到的黑盒记忆；需要跨轮保留的信息必须写成游戏变量（因此进入事件流，可审计、可回放）。
4. **重试是同一次会话**：同一条 AI 命令的重试必须重建同一份上下文；上下文不含时间与随机输入，所以这一点由确定性保证。
5. **agent 定义随游戏版本冻结**：`agents`（`id`、`roleId`、`systemPrompt`、`limits{timeoutMs,maxAttempts,tokenBudget}`）写在游戏包内；节点只声明用哪个 agent、替哪一席行动、输入与降级分支。**模型不属于定义**：租户用自己的 `agent_model_bindings` 决定这个 agent 用哪个 provider/model。
6. **AI 节点必须声明席位**：没有席位就没有会话键，因此发布期拒绝不声明 `participantId` 的 `aiGenerate`。

## 后果

- 不需要 `agent_sessions` 表，也没有"会话过期清理"任务；会话生命周期 = 实例生命周期。
- prompt 一律走投影，权威状态永不进入模型调用；事件 payload 暂不进入 prompt（其可见性需由游戏声明，见 `P4-03`）。
- agent 不能跨局积累记忆。若将来需要"同一个 role 跨局变强"，那是新的特性，需要显式的记忆表与重放一致性方案，不能用进程内存实现。
- 若将来需要"轮到谁就替谁行动"的动态席位，需要新增声明式手段（例如 `participantIdExpr`），本轮只支持固定席位。
