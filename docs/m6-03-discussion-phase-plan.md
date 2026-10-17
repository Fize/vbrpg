# M6-03 讨论阶段与轮次强制（含 M6-02 prompt 分节）

给「谁是卧底」加上讨论阶段：描述（必发言）→ 讨论（≤3 轮，可跳过）→ 投票（必投），
并把 AI 的 prompt 按节重排，让「现在在哪一步、还等谁、能做什么」一眼可读。

## Goal

现在一桌人只能各描述一句就直接投票，没有商量的余地，AI 也没有立场可以表达。
本任务把这局的下半场补上：

- 描述结束后进入讨论，最多 3 轮，每轮每个在世席位**最多发言一次**；每个席位有一次
  「这轮不说」的机会（跳过工具）。
- 讨论满 3 轮后由规则接管：允许动作收窄为只剩投票，再想发言会被拒（`NOT_DISCUSSING`）。
- 轮次只统计本轮涉及的席位：出局席位既不发言也不计入等待。
- 跳过写自己的一行记录，**不产生发言气泡**（不顶掉该席位已有的发言）。

同时补齐 `M6-02`：AI 的 system 从一坨拼串改成有节的结构（规则 / 你的角色 / 你的位置与席位表 /
其他角色与可见人格 / 你的人格 / 只有你知道的信息 / 行动约束），回合指令分节
（现在 / 现在的局面 / 允许动作 / 输出要求）。对局内逐字不变的部分仍留在 prompt 前缀里。

## Approach

1. **规则（`games/undercover.ts`）**：`phase` 增加 `discuss`，变量增加 `discussRound`（1..3）与
   `discussed`（本轮已处理的席位）；`describePhaseEnded` 改为进入讨论而不是直接投票；
   新增派生事件 `discussRoundEnded`（一轮结束）与 `discussionEnded`（讨论结束，进投票）；
   新增动作 `skipDiscussion`（无参数，`audience: "room"`）。
2. **可见性**：`discussRound`、`discussed` 公开，让席位（含 AI）看得到轮次和谁还没说话；
   `votes` 仍对所有人隐藏。
3. **prompt 分节（`llm/prompt.ts`）**：system 按节拼装；回合指令不再直接 `JSON.stringify`
   公开状态，而是把席位 id 换成席位名、把变量名换成游戏自己的词（`game.words`），
   让模型不必猜 id。人格由 `ai-seat.ts` 传入（自己看全份，别人只看 `visiblePersona` 切片）。
4. **界面**：`ActionDock` 本来就支持无参数动作，跳过会自动出现在动作区；
   `MatchView` 的气泡只认「有内容」的行，`MatchLog` 对无参数动作不再打印「（无内容）」。
5. **测试**：`undercover.test.ts` 补讨论阶段用例（第 4 次发言被拒、跳过不占发言、3 轮后只剩投票、
   出局席位不计入轮次）；`prompt.test.ts` 补分节与席位名渲染；浏览器端补「跳过不顶掉气泡」。

## Impact

| 文件 | 改动 |
| --- | --- |
| `apps/platform/src/server/games/undercover.ts` | 阶段机：描述 → 讨论（≤3 轮）→ 投票；新增 `skipDiscussion` |
| `apps/platform/src/server/games/undercover.test.ts` | 覆盖讨论阶段与轮次强制 |
| `apps/platform/src/server/llm/prompt.ts` | system 与回合指令分节；publicState 用席位名与游戏词汇渲染 |
| `apps/platform/src/server/llm/prompt.test.ts` | 分节与渲染断言 |
| `apps/platform/src/server/match/ai-seat.ts` | 把人格（自己全份、别人可见切片）传进 prompt |
| `apps/platform/src/browser/services/match-log.ts` | 无参数动作不打印「（无内容）」 |
| `apps/platform/src/browser/views/MatchView.vue` | 气泡只认有内容的行 |
| `apps/platform/src/browser/services/match-log.test.ts`、`views/MatchView.test.ts` | 上述两条的回归 |
| `docs/platform-migration-plan.md` | 勾掉 `M6-02`/`M6-03`/`M6-04` |

## Tasks

- [x] `M6-03-A` `undercover.ts`：阶段与变量、`skipDiscussion` 动作、派生事件、`briefing` 与 `words` 更新
- [x] `M6-03-B` `undercover.test.ts`：讨论阶段用例（必发言/必投、可跳过、第 4 次发言被拒、出局席位不计轮次）
- [x] `M6-03-C` `prompt.ts`：system 分节 + 回合指令分节 + 公开状态按席位名/游戏词汇渲染
- [x] `M6-03-D` `ai-seat.ts`：把人格传进 prompt；`prompt.test.ts` 断言分节
- [x] `M6-03-E` 浏览器端：跳过不进气泡、无参数动作不打印「（无内容）」及其测试
- [x] `M6-03-F` `docs/platform-migration-plan.md` 勾选 `M6-02`/`M6-03`/`M6-04`
- [x] `M6-03-G` 门禁：`pnpm typecheck`、`pnpm test`（186）、`pnpm lint`、`pnpm format:check`、`pnpm build`、
      `pnpm test:db`、`pnpm test:e2e`（8）
- [x] `M6-03-H` 演示环境重建 + 真机跑一局（见下）

## 真机结果（演示环境，1 个真人 + 3 个 AI，分类「三国人物」）

规则本身跑通了：描述 4 席 → 讨论三轮（第 1、2 轮结束各留一行派生事件）→ 投票 → 结算，玩家席
跳过 3 次、投出一票，对局结束；`skipDiscussion` 写进记录但不产生发言气泡；公开状态里能看到
`discussRound` 与 `discussed`；词对由模型按分类生成（「关羽」），AI 的推理与投票都落在记录里。

但这一局也暴露了一个**真问题**：30 次模型调用 / 63,562 token、其中 **6 次 `aiFailed`**
（`ITERATION_LIMIT`），全部集中在讨论阶段与投票阶段。失败形态：

1. **讨论阶段调用 `vote`**：模型的推理写「轮数满了，该投票了」，不信任回合指令里的允许动作，
   然后连续两次调用同一个被拒的动作，第三次触发上限。
2. **投票目标不合法后重复同一个被拒动作**，同样烧满 3 次调用。

失败原因**不在平台**：`allowed` 判断与写入路径都正确（每次被拒都如实记录在 `aiCall` 行里）。
问题在（a）回合指令的形式让模型可以「自己推断阶段」，以及（b）`maxCallsPerTurn=3` 下每次失败
要白烧 3 次调用。诊断过程中我先怀疑「回合内允许动作列表过期」，做了修复与回归用例，但用例反过来
证明这个场景当前**不可达**（每个待办席位不行动，轮次就不会结束），于是回退，没有把无用的复杂度留在
`ai-seat.ts`。结论落进 `M6-08`（见 `platform-migration-plan.md`），并建议顺带把工具返回的拒绝原因
写进 `aiCall` 行——这次诊断最大的障碍就是记录里查不到「模型被告知了什么」。

## 复测（同形态，2 回合 / 30 次调用 / 89,146 token）

`M6-08` 的 (a) 实施后重跑一局（分类「当代职业」）：**0 次 `aiFailed`**，30 次调用全部一次命中，
两回合打完到 `completed`。改动是让硬性上限和越界后果进入规则的同一处（system「行动约束」：
最多 3 次、用尽即这一步作废），只有「现在是第几次、还剩几次」留在最后一条消息，
三条重试分支共用 `retryInstruction()` 重念允许动作。代价是 prompt token 涨到 80,105（单次均值约 2.7k），
其中人格四段占了新增的绝大部分。

同一局顺带修掉一个漏接：`ai-seat.ts` 从未把人格切片传给 `buildSeatPrompt`，导致「你的人格」
「其他席位与可见人格」两段恒为空。接通后 `aiCall` 的 `reasoning` 里直接出现「ENFJ柔软风格」，
四席的发言风格也按 `persona.style` 分开了（连续追问 / 先夸后驳 / 比喻加感叹）。

## 决定（按默认，见对话记录）

- 一轮 = 每个在世席位最多行动一次；本轮在世席位全部「发言或跳过」后进入下一轮。
- 跳过只放弃自己本轮这次发言，不影响别人。
- 满 3 轮由规则自动进投票，中途谁也结束不了；投票阶段不再接受发言。
- 跳过写独立事件行（`skipDiscussion`），`audience: "room"` 但仍不渲染成发言气泡。
