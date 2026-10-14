# Phase 0 运行时技术验证（前半部分）

- 记录日期：2026-08-23
- 实现：`packages/workflow-engine`
- 当前状态：NativeRuntime、DSL v1 编译入口、事件回放和发布前 validator 已完成；LangGraph JS comparison pending（greenfield 非阻塞）

## 已验证

原生纯函数原型在不访问数据库、网络、系统时间或随机源的情况下，使用显式事件推进以下简化流程：

```text
instanceCreated
  -> setVariable(role assignment)
  -> waitForPlayerInput(werewolf)
  -> waitForPlayerInput(seer)
  -> vote(werewolf + seer)
  -> end
```

已覆盖：

- 自动节点和等待节点之间的状态转换。
- 私人行动只接受声明的参与者。
- 多人投票在收齐参与者前保持 waiting，收齐后只推进一次。
- 重复参与者输入被拒绝，不会覆盖已有结果。
- 事件序号必须连续，输入实例必须匹配。
- 计时器和 AI 节点输出显式 command；command id 由实例、序号和节点确定性生成。
- 同一事件轨迹回放得到相同的最终状态。
- 发布前校验会拒绝未知节点引用、不可达节点、无可达终点、隐式循环，以及非法等待、计时和 AI 配置。
- DSL v1 编译会生成稳定 definition hash，事件回放会在相同初始状态下得到一致结果。

## 尚未验证

以下项目仍属于 P0-05 后半部分，不能据此选择第一版运行时：

- LangGraph JS 同一夹具的实现和语义对照。
- PostgreSQL checkpoint/快照恢复。
- 进程重启后的动作幂等、并发锁和 Outbox 事务协议。
- AI 超时、重试上限和 fallback 分支的完整运行。
- 真实玩家投影和秘密字段防泄漏测试。

## 当前结论

NativeRuntime 已证明平台所需的最小纯转换边界可以独立于 LangGraph 建立。该结论只允许继续推进平台契约和原生 spike，不构成放弃 LangGraph 的最终决策。最终决策必须在两种实现通过同一组 PostgreSQL、并发、幂等、投影、版本和 fallback 测试后形成新的 ADR。

## 复核（2026-10-14）

原「尚未验证」清单中已闭合的部分：

- PostgreSQL 持久化与恢复协议：`apps/api/src/services/game-dispatch.ts` 在租户事务内锁定实例、校验顺序号、按 idempotency key 幂等追加事件、更新实例状态，并在同一事务写入外部命令；`apps/api/scripts/game-dispatch-integration.ts` 覆盖重复事件幂等与 timer command。
- 并发锁与动作幂等：同一路径（实例行锁 + 命令唯一键），但尚无并发竞争压测。

仍未闭合：LangGraph JS 对照与书面结论；快照写入策略；真实玩家投影与秘密字段防泄漏测试；AI 超时、重试上限与 fallback 的完整运行（当前只有单次同步调用）。
