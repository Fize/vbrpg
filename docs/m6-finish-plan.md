# M6 收尾：诊断、语气、规则细化

M6 剩下的三项一起做完：`M6-08(c)` 诊断缺口、`M6-06` 输出语气、`M6-05` 规则细化。
顺序是先小后大：前两项改文案与记录字段，第三项动规则引擎。

## Goal

1. AI 一次回合失败后，能从记录里查到「平台当时回了它什么」，不必再靠时间线反推。
2. 发言可以带（笑）（小声）这类语气，平台原样播出。
3. 「谁是卧底」的规则补齐到计划文档描述的样子：顺序发言、平票重投、淘汰公开身份、
   出局不再发言、结束时给出可核对的表现统计。

## Approach

### M6-08(c) 拒绝原因进记录

`recordTurn` 是在事务里先写 `aiCall` 行、再试动作的，所以行写下去时还不知道结果。
不为此调整写入顺序（会打乱时间线的因果），改为在**下一次**调用上标注原因：

- `aiCallPayloadSchema` 增 `retryReason?: string`：本次调用是因为收到这条回执才重试的。
- `aiFailed` 行的 payload 增 `lastFeedback?: string`：放弃时最后一次回执。

这样一次失败的回合在库里读出来是「回执 → 重试 → 回执 → 重试 → 失败(带最后一次回执)」。

### M6-06 语气标注

平台本来就原样存 `text`，所以这条是让模型**敢用**：`briefing` 与回合指令的「输出要求」
各说一次「可以带括号语气，平台原样播出」。不改任何存储与渲染路径。

### M6-05 规则细化

- **顺序发言**：描述阶段 `waiting` 只含顺序上的下一位（`alive` 里第一个还没说话的）。
  跳位发言被拒（`OUT_OF_ORDER`）。讨论阶段保持「本轮每人一次、顺序不限」——文档只说顺序发言，
  讨论需要自由对质才有意义。
- **平票重投**：`resolveRound` 判定平票时，若本轮还没重投过，清空 `votes` 回到投票阶段再投一次，
  并给出 `revoteStarted` 派生事件；重投仍平票则不淘汰、进入下一回合。用 `revoted: boolean` 记录
  本回合是否已重投，进入下一回合时清零。
- **淘汰后公开身份**：`summary.eliminatedRole`（`civilian` / `undercover`）。词始终不公开。
- **出局不再发言**：现有 `alive` 过滤已保证，补用例钉住。
- **表现统计**：变量 `stats`（每席 `spoke` / `votesAgainst`），结算时累计；终局写入
  `scores`（每席角色、发言数、被投票数、存活回合、是否胜方）并公开。客观统计，不调模型。

`briefing` 同步重写：顺序发言、平票重投、出局公开身份、语气允许——玩家看到的规则必须就是跑出来的规则。

## Impact

| 文件 | 改动 |
|---|---|
| `src/shared/domain.ts` | `aiCallPayloadSchema` 增 `retryReason`、`aiFailed` payload 增 `lastFeedback` |
| `src/server/match/service.ts` | `recordFailure` 落 `lastFeedback` |
| `src/server/match/ai-seat.ts` | 重试时把回执带进下一次 `recordTurn`；失败时带最后一次回执 |
| `src/server/llm/prompt.ts` | 「输出要求」加语气说明 |
| `src/server/games/undercover.ts` | 顺序发言、平票重投、公开身份、表现统计、`briefing` 重写 |
| `src/server/games/undercover.test.ts` | 上述行为的用例 |
| `src/server/llm/prompt.test.ts` | 语气说明的断言 |
| `docs/platform-migration-plan.md` | 勾选 `M6-05` / `M6-06` / `M6-08`；修 `M6-01`/`M6-02` 与代码相反的描述 |

## Tasks

- [x] `undercover.ts`：`briefing` 重写（顺序发言、平票重投、公开身份、语气）+ 顺序发言校验
- [x] `undercover.ts`：平票重投（`revoted` 变量 + `revoteStarted` 派生事件 + 结算分支）
- [x] `undercover.ts`：`summary.eliminatedRole` 与 `scores`（`stats` 累计）
- [x] `undercover.test.ts`：五条规则的对应用例
- [x] `prompt.ts`：输出要求加语气说明；`prompt.test.ts` 断言
- [x] `domain.ts` + `service.ts` + `ai-seat.ts`：`retryReason` 与 `lastFeedback`
- [x] `docs/platform-migration-plan.md`：勾选与描述修正
- [x] 门禁：typecheck / 单测 195 例 / test:db / eslint / prettier / e2e 8 例
- [x] 真机：一局跑完（31 次状态推进到 `completed`），顺序发言按席位接力；`scores` 与
  `eliminatedRole` 落库；AI 发言出现（笑）（叹气）（小声）；`scores` 在界面渲染成 4 行表格。
  平票重投在真机上不易凑出（AI 投票不可控），由 `undercover.test.ts` 两例与手工状态覆盖。

## 补充：表现统计的显示

`scores` 进公开状态后，通用渲染把它拍成一行「胜负：是、身份：平民、席位：s1、…」，重复且难读。
`PhaseCard` 现在把「形状一致的数组对象」渲染成表格——这是数据形状规则，不认识任何游戏。
