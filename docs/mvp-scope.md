# VBRPG MVP 范围

- 记录日期：2026-08-24（2026-10-15 重写）
- 当前目标：把游戏平台的最小可用面立起来——账号、模型配置，加上承载对局的数据底座

## 已交付（2026-10-15 现状）

- 平台账号：登录、持久化 session、CSRF、首登强制改密、管理员建号与重置、审计。
- 模型配置：Provider / Model 的增删改与连接测试，API key 用 `PLATFORM_CREDENTIAL_KEY` 加密存放。
- 对局底座：`game_instances` / `game_participants` / `game_events` / `game_snapshots` /
  `pending_commands` / `scheduled_jobs`；worker 具备 claim / lease / 重试 / 死信循环。
  2026-10-15 第八轮删除了 `player_actions` 与 `outbox_events`（见 ADR-008）。
- 中立内核：玩家视图投影（fail-closed）、事件重放、转换与错误类型。

## 已撤除（2026-10-15）

原先的 MVP 以"用 DSL 提交游戏定义并推进一次状态转换"为闭环。该路线已撤除：DSL、发布期校验、
无状态 MVP 端点（`/v1/mvp/runtime/{compile,instances,dispatch,ai-dispatch}`）与平台侧 AI 调用链
都不再存在，见主计划 §16 第六轮。游戏逻辑改为 TypeScript 模块。

## MVP 暂不做

- 旧系统迁移、数据兼容和双轨切流。
- Outbox/Worker 的生产级消费与死信观测。
- 可视化编辑器、资源市场、插件沙箱与第三方游戏分发。
- 完整 WebSocket、断线恢复、快照优化和容量工程。

## 下一步

1. `GameModule` 接口与游戏注册表。
2. 对局 HTTP 入口（创建对局、提交事件、读取自己的投影）。
3. 第一个代码化游戏（狼人杀）+ 回归夹具。
