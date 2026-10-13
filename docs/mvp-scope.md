# VBRPG MVP 范围

- 记录日期：2026-08-24
- 当前目标：验证“定义一个游戏并推进一次状态转换”的最小闭环

## MVP 必须完成

- 用 DSL v1 提交一个游戏定义。
- 校验并编译定义，返回稳定 definition hash。
- 创建一个初始状态。
- 提交一个事件，返回新状态和外部命令。
- API 有最小的 compile/instances/dispatch 端点和自动化测试。
- 至少有一个 AI 节点能通过真实 OpenAI-compatible API 完成一次 demo。

## MVP 暂不做

- 旧系统迁移、数据兼容和双轨切流。
- 多租户高级治理、邀请、复杂 RBAC、RLS 攻击测试。
- Outbox/Worker 的生产级消费、AI 供应商、计费和用量系统。
- 可视化编辑器、资源市场、插件沙箱和 LangGraph 适配器。
- 完整 WebSocket、断线恢复、快照优化和容量工程。

## AI Demo

配置平台级 `DEEPSEEK_API_KEY` 后运行 `pnpm --filter @vbrpg/api demo:ai`。默认使用腾讯云 TokenHub `https://tokenhub.tencentmaas.com/v1/chat/completions` 和模型 `hy3`。本局上下文只包含当前状态和显式传入的本局事件，不保存跨局记忆；`AI_CONTEXT_WINDOW_TOKENS` 为 256K 窗口，`AI_MAX_INPUT_TOKENS` 限制 Hy3 的 192K 最大输入，`AI_RESERVE_OUTPUT_TOKENS` 为思考和回答预留 16K token。历史事件采用稳定的追加顺序放在变化中的当前状态之前，利用 provider 的自动前缀缓存；超过预算时优先淘汰最旧事件。

模型、TokenHub 地址和 ctxwin 策略是平台级配置，不从租户、用户或单局请求读取；所有租户统一使用 `hy3`。

当前实现已通过 OpenAI-compatible 请求协议测试；重新加载 `~/.zshrc` 后，TokenHub 直连和完整游戏 AI demo 均返回 HTTP 200，云端 AI 验收通过。

这些能力可以保留为后续扩展的底层代码，但不能阻塞 MVP 验收。
