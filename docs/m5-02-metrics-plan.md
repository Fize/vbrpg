# 指标与告警（M5-02）

放量前先能看见：动作延迟、错误率、卡住的对局、AI 成功率与 token 用量。不引入 Prometheus，
指标端点从进程内计数与既有记录里算，告警先落在 `warn` 日志里。

## Goal

- 一个管理员可读的端点，回答「现在这套东西跑得怎么样」。
- 卡局与模型失联自己冒出来，不用人去猜。

## 口径

| 指标 | 来源 | 说明 |
| --- | --- | --- |
| `actions.count` / `latencyMs` | 进程内直方图 | 只统计 `POST /v1/instances/:id/events`，从请求进来到回复落地的毫秒数，分桶 5/10/25/50/100/250/500/1s/2.5s/5s/10s。分位取所在桶的上界，超出最后一桶报 `null`（不编造）。 |
| `http.responses` / `serverErrors` / `errorRate` | 进程内计数 | 每个回复算一次，5xx 计为错误。 |
| `matches.stuck` | `game_instances.updated_at` | 超过 `MATCH_IDLE_TIMEOUT_MS` 没有推进的活动对局数，与作废扫描同一判据；上限 500。 |
| `ai.calls` / `failures` / `failureRate` | `game_events` | 窗口默认 24 小时：`aiCall` 与 `aiFailed` 行数。不从计数器来，所以不会与记录漂移。 |
| `ai.tokens` | `game_events` | 同窗口内 `prompt/completion/total_tokens` 求和，模型调用行本来就带用量。 |

进程内计数是**每进程**的：多副本部署时每个副本只看得到自己。这是刻意的取舍——接外部聚合
（Prometheus / OTLP）是后续一步，届时进程内计数器原样导出即可。

## 告警

worker 每 60 秒读一次最近一小时的模型健康度：调用次数 ≥ 5 且失败率 ≥ 20% 时打 `warn`
（附带窗口内的调用数、失败数与 token 用量）。卡局不作废时会另有 `idle matches cancelled`
的 `warn`。两者都只是日志，接外部告警通道是后续工作。

## Tasks

- [x] `src/server/metrics.ts`：进程内计数 + 直方图 + 两个入库聚合（`readAiHealth`、卡局数）。
- [x] `src/server/routes/platform-metrics.ts` + `app.ts`：`GET /v1/admin/metrics`，管理员只读；
      `onResponse` 钩子喂计数，动作路由单独计时。
- [x] `main.ts`：API 侧创建 metrics；worker 每 60 秒的健康检查与 `warn`。
- [x] 测试：`metrics.test.ts`（分位、空样本、超出最后一桶）与 `platform-routes.test.ts`
      （管理员 200、普通账号 403、无数据库时 `matches`/`ai` 为 null）。
- [x] 门禁：typecheck / 单测 202 例 / test:db / eslint / prettier / e2e。
- [x] 真机：提交一次动作后 `actions.count=1`、`latency p50=25ms`、`responses` 3→8、`ai.calls` 261→267、
      token 906k→915k、`matches.stuck=0`。

## 不做的

- 不引入 Prometheus 客户端、不做看板、不建时序表：先把口径钉住，导出方式是下一步的事。
- 不统计每个游戏自己的业务指标（发言数、票型等）：那是游戏的事，不是平台的事。
