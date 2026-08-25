# ADR-002：通过 GameRuntime 隔离工作流执行器

- 状态：Accepted
- 日期：2026-08-23
- 范围：工作流执行、API、worker 和回放

## 背景

LangGraph JS 的节点、边、interrupt 和 checkpoint 与游戏流程有重叠，但平台还需要租户授权、多人输入聚合、动作幂等、版本固定、玩家投影和业务事件回放。这些能力不能依赖某个 Agent 编排框架的内部类型。

## 决策

平台只依赖稳定的 `GameRuntime` 边界。运行时至少提供编译定义、创建实例、分发事件和生成玩家视图的能力。平台事件、快照和命令是权威数据；任何具体执行器的 checkpoint 只能是实现细节。

Phase 0 通过同一组夹具验证 LangGraph JS 和原生解释器。只有在重启恢复、并发提交、重复动作、投影隔离、版本固定、AI fallback 和回放全部通过后，才决定第一版默认执行器。

## 后果

- `packages/contracts` 不导出 LangGraph 专有类型。
- 旧版本实例必须记录 `engine_version`，一个实例不能混用执行器。
- interrupt 或 worker 重试产生的副作用必须转成幂等 command，经事务提交后的 Outbox 执行。
- 更换执行器不会要求变更游戏包 DSL 或平台 API。
