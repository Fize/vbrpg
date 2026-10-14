# Phase 0 狼人杀黄金轨迹报告

- 记录日期：2026-08-23
- 来源：`backend/src/services/games/werewolf_engine.py`
- Fixture：[docs/fixtures/werewolf-golden-trace-suite.json](./fixtures/werewolf-golden-trace-suite.json)
- 校验脚本：`backend/scripts/verify_werewolf_golden_trace.py`

## 已生成的真实规则轨迹

当前 fixture 包含 10 条由旧 Python 狼人杀引擎实际执行得到的轨迹：

- 正常狼人夜间击杀
- 女巫使用解药
- 女巫使用毒药
- 预言家查验狼人
- 预言家查验好人
- 投票平票
- 全员弃票
- 猎人开枪
- 好人阵营胜利
- 狼人阵营胜利

轨迹中的快照排除了 UUID、玩家名称和墙上时钟，只保留阶段、角色、存活状态、死亡原因、夜间动作、投票、药剂状态和胜负结果，便于 TypeScript 运行时跨语言比较。

## 运行方式

```bash
PYTHONPATH=backend/scripts python3 backend/scripts/verify_werewolf_golden_trace.py
```

校验脚本已于 2026-10-14 失效，原因见下节复核。

## 尚未覆盖

旧 `WerewolfEngine` 本身没有统一的超时和断线恢复接口，因此以下轨迹需要从 `WerewolfGameService`/WebSocket 服务层提取：

- 真人玩家行动超时后的降级路径
- WebSocket 断线、重连和状态恢复
- AI 调用失败或超时后的 fallback

这些缺口不能用引擎单元轨迹代替，仍属于 P0-02/P0-05 后续工作。

## 复核（2026-10-14）

本 fixture 的来源已从仓库中删除，因此文档与 `package.json` 中的校验入口都已断裂：

- `source` 字段指向的 `backend/src/services/games/werewolf_engine.py` 已在 `79cf54e`（LangGraph 架构改造）中被删除。
- `PYTHONPATH=backend/scripts python3 backend/scripts/verify_werewolf_golden_trace.py` 现在直接报 `FileNotFoundError: .../backend/src/services/games/werewolf_engine.py`；根 `package.json` 的 `pnpm run test:golden:legacy` 同样不可运行。
- `backend/scripts/generate_werewolf_golden_trace.py` 与本文件描述的生成流程一并失效。

结论：这 10 条轨迹只能作为**历史快照**阅读，不再是可执行的行为基线。恢复比对能力只有两条路，且各有代价——从 `79cf54e^` 取回旧实现（与 greenfield 决策冲突），或针对 LangGraph 版重录（语义已变，达不到「冻结旧行为」的目的）。
