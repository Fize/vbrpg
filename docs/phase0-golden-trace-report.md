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

校验会重新执行旧引擎并与 fixture 做结构化比较；当前已通过。

## 尚未覆盖

旧 `WerewolfEngine` 本身没有统一的超时和断线恢复接口，因此以下轨迹需要从 `WerewolfGameService`/WebSocket 服务层提取：

- 真人玩家行动超时后的降级路径
- WebSocket 断线、重连和状态恢复
- AI 调用失败或超时后的 fallback

这些缺口不能用引擎单元轨迹代替，仍属于 P0-02/P0-05 后续工作。
