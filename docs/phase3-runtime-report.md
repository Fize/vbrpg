# Phase 3 DSL v1 与确定性运行时进度

- 记录日期：2026-08-24
- 执行模式：Greenfield；不承担旧系统迁移或兼容

## 已交付

- `compileGameDefinition`：只接受当前 DSL v1，使用共享 Zod schema 解析定义。
- 编译前执行图结构校验：未知引用、不可达节点、隐式循环、无终点和非法等待/计时/AI 配置都会被拒绝。
- 编译结果生成稳定 SHA-256 definition hash；对象字段顺序变化不会改变 hash。
- `replayEvents`：按显式事件序列重放确定性状态转换并收集外部命令。
- `createInitialState` 和 `dispatchEvent`：将编译结果正式接入新实例创建和事件入口。
- API `dispatchGameEvent`：在租户事务中锁定实例、校验顺序号、幂等追加事件、更新状态并持久化外部命令。
- API `ai-dispatch`：从运行时产生 `aiGenerate` 命令，调用真实 OpenAI-compatible endpoint，再把结果作为 `aiResultReceived` 事件推进本局状态。
- AI ctxwin：只组装当前状态和调用方显式传入的本局事件；没有跨局记忆存储。
- AI ctxwin：针对 Hy3 使用 256K 上下文、192K 最大输入和 16K 输出预留；事件采用稳定追加前缀，当前状态放在 prompt 尾部，超过预算时优先丢弃最旧事件。
- 缓存策略：不在应用层复制或持久化 prompt cache，依赖 TokenHub Hy3 的自动前缀缓存；请求保持固定 system prompt、稳定事件序列和 `stream: false`，为 provider cache 命中创造稳定前缀。
- 多租户策略：模型、base URL、token 预算均为 API 进程级配置；请求体和租户上下文不提供模型覆盖字段。

## 验证结果

- workflow-engine 测试 15/15 通过。
- API 测试 18/18 通过，覆盖 AI 请求协议、JSON 结果解析、ctxwin 字符预算和 `OPENAI_API_KEY` 配置回退。
- 覆盖 v1 编译、稳定 hash、非法 DSL 拒绝和事件重放一致性。
- PostgreSQL 迁移及租户/RLS 集成测试已通过，作为运行时持久化底座验证。
- PostgreSQL dispatch 集成测试覆盖 timer command、重复事件和实例序列更新。
- Docker PostgreSQL 已健康运行；Hy3 配置和 TokenHub 真实请求返回 HTTP 200，demo 成功将游戏推进到 `completed`。

## MVP 收尾

- 已完成有效 `DEEPSEEK_API_KEY` 的 TokenHub 真实模型验收。
- 在云端凭据通过后停止扩展设计；公共视图、快照、Outbox、worker handler 和多租户增强不作为当前 MVP 门槛。

## 复核（2026-10-14）

- 测试数已变化：`apps/api` 18 → 102，`packages/contracts` 5 → 18，`packages/workflow-engine` 15 不变，新增 `apps/web` 7。
- `dispatchGameEvent` 的持久化语义（租户事务 + 实例行锁 + 顺序号校验 + idempotency key 幂等追加 + 命令同事务落库）仍然成立，但**只有集成脚本调用**（`apps/api/scripts/game-dispatch-integration.ts`），没有 HTTP 入口；已暴露的 `/v1/mvp/runtime/*` 是无状态路由。
- AI 路径现状：`POST /v1/mvp/runtime/ai-dispatch` 的 definition/state/event 全部由请求体提供，模型与密钥取进程级配置，与 `providers`/`provider_models` 表及 `agentModelBinding` 契约未接线；`ai_usage_ledger` 无写入方，无超时、重试上限、预算与 fallback 事件。
- TokenHub `hy3` 的实网验收不可复现：以当前环境可用凭据运行 `pnpm --filter @vbrpg/api demo:ai`，默认 `https://tokenhub.tencentmaas.com/v1` + `hy3` 返回 provider HTTP 401（映射为 502 `AI_PROVIDER_ERROR`）；改指向 `https://api.deepseek.com/v1` + `deepseek-chat` 后同一凭据可完整跑通 demo（`aiResult: red`）。凭据有效，失效的是默认 endpoint/model 组合。
- 快照仍无写入方；投影器（公共/角色/个人视图）与防泄漏测试未实现。
