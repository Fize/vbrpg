# ADR-003：使用 Zod 作为共享契约的运行时校验工具

- 状态：Accepted
- 日期：2026-08-23
- 范围：REST、Socket.IO、工作流定义和 worker 消息

## 背景

迁移计划要求前后端共享 API、事件、WebSocket 和 DSL 契约。仅使用 TypeScript 接口无法校验来自网络、数据库或旧系统的运行时数据，也容易重新产生重复 DTO。

## 决策

共享契约包使用 Zod 定义运行时 schema，并从 schema 推导 TypeScript 类型。API、WebSocket 和 worker 边界先解析未知输入，再将已验证的类型交给领域代码。契约变更必须增加兼容性测试；工作流 DSL 的发布校验仍由独立 `workflow-schema` 包负责。

v0 契约保持平台中立：只描述身份引用、事件、状态、玩家视图和外部命令，不包含 Fastify、Socket.IO、LangGraph 或数据库 ORM 类型。

## 后果

- 新边界禁止手写与共享 schema 重复的 DTO。
- Zod 错误需要转换为平台统一错误模型，不能直接把内部堆栈返回给客户端。
- schema 包可以被 Web 和 Node worker 同时使用；未来若选择 TypeBox，必须提供等价的运行时校验和迁移方案。
