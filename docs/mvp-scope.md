# VBRPG MVP 范围

- 记录日期：2026-08-24（2026-10-15 重写）
- 当前目标：把游戏平台的最小可用面立起来——账号、模型配置，加上承载对局的数据底座

## 已交付（2026-10-15 现状）

- 平台账号：登录、持久化 session、CSRF、管理员建号/重置/删除、用户自助改密、审计。
- 模型配置：Provider / Model 的增删改与连接测试，API key 用 `PLATFORM_CREDENTIAL_KEY` 加密存放。
- 对局底座：`game_instances` / `game_participants` / `game_events`。没有队列表，没有快照表：
  worker 按实例行锁 + 扫描待办推进对局（ADR-009）。
- 中立内核：玩家视图投影（fail-closed）、转换与错误类型。

## 已撤除（2026-10-15）

原先的 MVP 以"用 DSL 提交游戏定义并推进一次状态转换"为闭环。该路线已撤除：DSL、发布期校验、
无状态 MVP 端点（`/v1/mvp/runtime/{compile,instances,dispatch,ai-dispatch}`）与平台侧 AI 调用链
都不再存在，见主计划 §16 第六轮。游戏逻辑改为 TypeScript 模块。

## MVP 暂不做

- 旧系统迁移、数据兼容和双轨切流（greenfield，已确认不做）。
- 实时推送（WebSocket/SSE）与断线恢复：当前只有请求-响应，没有广播层。
- 可视化编辑器、资源市场、插件沙箱与第三方游戏分发。
- 容量工程与压测（当前只在开发规模下验证）。

## 下一步

见主计划 §8.2 的工作计划（M1–M5）。当前里程碑是 **M1「让一局跑起来」**。
