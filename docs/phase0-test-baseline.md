# Phase 0 测试基线

- 记录日期：2026-08-23
- 目的：冻结旧系统迁移前的可解释基线，不把旧测试债务误认为新引擎回归

## 前端

运行命令：`npm test -- --run`（目录：`frontend/`）

结果：27 个测试文件中 16 个通过、10 个失败、1 个跳过；594 个测试中 483 个通过、71 个失败、40 个跳过。

初步分类：

| 分类 | 数量/范围 | 证据与处置 |
| --- | --- | --- |
| 有效回归基线 | 483 通过、40 跳过 | 保留，迁移后的黄金轨迹和契约测试不能低于此行为基线；跳过项需在 Phase 0 另行确认原因 |
| 过时规格 | Lobby store 6 项、旧 LobbyView 13 项 | 测试仍要求 `isOwner`/`transferOwnership` 和房间详情，但当前 store 已移除这些 API，当前 LobbyView 已改为游戏目录；迁移前需决定删除旧规格或补兼容层 |
| 测试基础设施缺陷 | GameLog 11 项、imageOptimization 5 项 | GameLog 测试未挂载 Pinia；IntersectionObserver 测试用 `vi.fn` 覆盖了需要 `new` 的构造器。先修测试夹具，再判断业务行为 |
| 真实缺陷候选 | JoinRoomForm 7 项、WebSocket/重连及 AI 控制相关失败 | 测试期望 `roomsApi.joinRoom`，当前实现调用 `roomsApi.getRoom`；其余失败需要按当前 API 契约和组件生命周期重新确认，暂不直接标记为新平台回归 |

失败测试不是本次 TypeScript 契约包的失败；它们属于旧前端基线债务，后续迁移时应逐项关闭、标记为过时，或转成新契约测试。

## 后端

本环境未提供 `pytest` 命令，也未发现仓库内的 Python 虚拟环境，因此本次不能产生后端通过/失败基线。后续在安装 `backend/requirements.txt` 的隔离环境后运行 `backend/run_tests.sh all`，并将结果补录本文件。该环境问题不改变旧后端代码。

## 当前基线结论

旧系统没有绿色的全量前端门禁，且后端测试尚未具备可运行环境。Phase 0 的新测试门禁应从共享契约包开始，随后补充真实 PostgreSQL 集成测试；不能以旧前端全量测试的当前失败数作为新引擎质量结论。
