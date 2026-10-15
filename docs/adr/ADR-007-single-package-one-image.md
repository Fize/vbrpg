# ADR-007：单包、单镜像、两种角色

- 状态：Accepted
- 日期：2026-10-15
- 范围：仓库结构、构建与部署

## 背景

平台在 Phase 1–3 期间拆成了 4 个共享包（contracts、db、runtime、workflow-engine）与 3 个应用
（api、worker、web），理由是"两个可部署进程共用代码、前端共享契约、纯内核可独立测试"。

撤除 DSL 后重新评估：全部代码约 7,000 行（源码），却背着 20 个配置文件、跨包符号链接、构建顺序
依赖（必须先构建 contracts 才能类型检查下游）以及 nginx + 两个镜像 + 跨域/CSRF 配置。同样的目标
（"前端不能打进 node 代码"、"多进程复用同一份实现"）用更轻的手段就能达到。

## 决策

1. **一个包**：`apps/platform`，源码分三个 tsconfig project：
   - `src/shared`：契约（Zod schema + 类型），浏览器安全，不许 import node 内建；
   - `src/server`：Fastify 路由、鉴权、存储、worker 轮询、游戏内核；
   - `src/browser`：Vue 控制台。
2. **一个镜像，两种角色**：`node dist/server/main.js --role=api|worker|both`。api 角色同时提供
   浏览器静态资源，因此控制台与 API 同源。
3. **模块之间用相对路径 + `.js` 后缀导入**，不用别名、不用 Node subpath imports：tsc、Vite、tsx
   和 node 对相对路径的解析一致，避免"开发能跑、构建后解析失败"的分歧。
4. **边界靠 project 而不是包**：浏览器 project 只包含 `src/browser` 与 `src/shared`；把 server 代码
   拉进浏览器产物的代价是构建直接失败。

## 后果

- 部署面变小：一个镜像、一个端口、同源（不再需要 nginx 与 `TRUSTED_WEB_ORIGINS` 之外的跨域处理）；
  worker 用同一镜像换角色启动，仍然独立进程、独立生命周期。
- 失去包边界强制的无环依赖图：现在靠 tsconfig project 与代码评审保证。若将来出现第二个真正的部署
  目标（独立 agent 服务、需要单独扩缩容的实时网关）或团队扩大，再按那时的边界拆包。
- 升级路径明确：拆包就是把 `src/shared`、`src/server/db`、`src/server/game` 各自提取成 workspace 包，
  并把相对导入换回包名——机械操作，风险低。
