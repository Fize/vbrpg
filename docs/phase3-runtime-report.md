# 阶段 3 报告（已撤销）

> 2026-10-15：本报告描述的"工作流 DSL + 编译器 + 解释器运行时"路线已撤除（见主计划 §16 第六轮）。
> 游戏逻辑改为 TypeScript 模块（`apps/platform/src/server/games/<slug>.ts`），平台只保留对局底座与中立内核
> （投影、重放、转换类型）。本文件保留为历史记录，其中的接口、测试数与验收结论均已失效。

## 当时的内容（历史）

- DSL v1 的 schema、图结构校验、稳定 definition hash 与纯 `transition`。
- `POST /v1/mvp/runtime/{compile,instances,dispatch,ai-dispatch}` 无状态运行时端点。
- 发布期静态校验：节点、引用、循环、可见性、白名单表达式、AI 降级分支。

## 现在的对应物

| 当时的概念 | 现在 |
| --- | --- |
| DSL 定义与编译 | 无（游戏是代码） |
| 发布期校验 | 无（由类型检查、代码评审与游戏回归夹具替代） |
| 无状态 `/v1/mvp/runtime/*` | 无（随撤除一并删除） |
| 玩家视图投影 | 保留：`packages/workflow-engine` 的 `projectPlayerView`（fail-closed） |
| 事件回放 | 保留：`replayEvents` |
