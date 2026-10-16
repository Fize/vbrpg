# 部署与运维手册

面向 `apps/platform`（单包：`src/shared` 契约、`src/server` 进程侧、`src/browser` 控制台）。
安全边界见 `docs/security/phase1-auth-provider-threat-model.md`（供应商出网策略、SSRF 与限流都在那里），
认证与凭据设计见 `docs/design/phase1-auth-provider-secure-design.md`，HTTP 契约见 `docs/api/`。

## 1. 形态

**一个包，一个镜像，两种角色**（ADR-007）：

```bash
node apps/platform/dist/server/main.js --role=api      # HTTP + 静态控制台 + worker
node apps/platform/dist/server/main.js --role=worker   # 只跑 AI 席位扫描
node apps/platform/dist/server/main.js --role=both     # 单进程（本地演示）
```

- `api` 同时托管编译好的控制台（`dist/browser`），同源，因此 cookie 与 CSRF 都不跨站；
  `/v1/*` 之外未命中的路径回退到 `index.html`，`/v1/*` 未命中的路径返回平台错误体（探针别指向随机路径）。
- `worker` 不监听端口，只扫 `status in ('running','waiting')` 且 `waiting.participantIds` 包含某 AI 席位的对局，
  按实例行锁逐个推进。多副本安全：抢到行锁的那个才会写。
- 单包的理由与边界见 ADR-007；拆包门槛是「≥2 个消费者或需要纯度做隔离测试」。

## 2. 配置

| 变量 | 必需 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | 是 | PostgreSQL 连接串 |
| `PLATFORM_CREDENTIAL_KEY` | 生产必需 | base64 的 32 字节主密钥，用于封供应商凭据 |
| `PLATFORM_CREDENTIAL_KEY_VERSION` | 否（默认 `1`） | 与密文一起记录的密钥版本 |
| `TRUSTED_WEB_ORIGINS` | 生产必需 | 逗号分隔的精确来源，仅这些来源可发 cookie 鉴权的写请求 |
| `PORT` / `LOG_LEVEL` / `NODE_ENV` | 否 | 端口 / 日志级别 / 环境 |
| `WORKER_ID` / `WORKER_POLL_INTERVAL_MS` | 否 | worker 标识与轮询间隔（默认 1000ms） |

启动时的硬约束：生产环境缺主密钥直接拒绝启动；`TRUSTED_WEB_ORIGINS` 在生产必须全部是 `https://`；
生产环境会话 cookie 带 `Secure`。开发环境允许回环 HTTP，便于本地跑。

## 3. 本地运行

```bash
pnpm install --frozen-lockfile
pnpm build              # 服务端 tsc + 控制台 vite
pnpm migrate            # 需要 DATABASE_URL
pnpm dev                # api 角色
pnpm dev:worker         # worker 角色
pnpm dev:web            # 控制台的 vite 开发服务器（把 /v1 反代到 api，见 vite.config.ts 的 API_PROXY_TARGET）
```

整栈（PostgreSQL + 迁移 + api + worker）：

```bash
export PLATFORM_CREDENTIAL_KEY=$(node -e "console.log(require('node:crypto').randomBytes(32).toString('base64'))")
docker compose -f docker-compose.platform.yml up -d --build
docker compose -f docker-compose.platform.yml exec platform \
  pnpm bootstrap-admin -- --username admin --password '<12 位以上>'
```

宿主 3000/5433 被占用时不必改容器：compose 已把平台端口映射到 8080；本地跑 vite 时把
`API_PROXY_TARGET` 指到 api 的实际端口即可。这套 compose 刻意跑 `NODE_ENV=development`（HTTP、cookie 不带
`Secure`），是本地测试栈，不是生产配置。

## 4. 首次上线

```bash
# 1. 迁移（幂等，可重复执行）
DATABASE_URL=… pnpm migrate

# 2. 第一个管理员（无自助注册；有活跃管理员时拒绝执行，取咨询锁防并发）
DATABASE_URL=… pnpm bootstrap-admin -- --username admin --password '<12 位以上>'

# 3. 供应商与模型（管理员在控制台「模型服务」做，或走 API）
# 4. 账号（控制台「用户管理」）
```

首次配置完成后就能开局：控制台「大厅 → 新建对局」，填席位（真人留空表示自己，AI 由供应商默认模型驱动）。

## 5. 升级与回滚

升级顺序：**先迁移，再换镜像**。

```bash
DATABASE_URL=… pnpm migrate            # 只向前；`.down.sql` 只用于回滚
docker compose -f docker-compose.platform.yml up -d --build
```

回滚：迁移都是可逆的，但 `.down.sql` 会丢数据（例如 `0001` 的 down 会删账号、会话、目录与审计表），
所以回滚前先导出。回滚顺序是**先停新版本，再 down 迁移，再上旧镜像**。

```bash
DATABASE_URL=… pnpm migrate:down -- --steps=1
```

主密钥轮换不走这条路：见 `credential-rotation.md`（轮换是对库的一次性迁移，与代码版本无关）。

## 6. 备份与恢复

见 `backup-restore.md`：备份策略、恢复步骤、演练命令与验证清单都在那里。
**备份里含供应商密文，恢复后仍需主密钥才能用**，因此备份与主密钥要分开存放。

## 7. 观测

- **日志**：结构化 JSON，每行带 `reqId`（即响应体里的 `requestId`），报障时先要这个编号。
- **审计**：`audit_logs` 记录账号、供应商目录与对局运维（暂停/恢复/取消）的操作，只记标识与结果，
  不记请求体、密钥或 cookie。删账号时 `actor_user_id` 置空，审计行保留。
- **对局记录**：`game_events` 是每局的完整历史，含模型调用的思考、工具调用与 token 用量，
  控制台房间页的「详细」档可以看到。成本核算目前只能从这里加总（M5 做指标）。
- **健康检查**：`GET /health` 是唯一的探针接口。

## 8. 排障清单

| 现象 | 先看什么 |
| --- | --- |
| 登录后立刻回到登录页 | 会话过期或 cookie 被拒：`TRUSTED_WEB_ORIGINS` 是否与实际访问来源一致（含端口与协议） |
| 写操作一律 403 | CSRF：刷新页面重取 token；确认请求带 `Origin` |
| AI 席位不动 | 是否启用了供应商与模型；worker 是否在跑；`select status from game_instances` 是否为 `running`/`waiting` |
| 模型调用失败 | 控制台「模型服务 → 测试连接」；失败原因是中文的（密钥被拒绝 / 触发限流 / 超时 …） |
| 供应商连接测试 500 | 主密钥与库中 `credential_key_version` 不匹配，按 `credential-rotation.md` 核对版本与密钥 |
| 对局卡在等待 | 房间页看「等谁」，`waiting.participantIds` 指向的席位是不是真人却没刷新页面 |

## 9. 明确不做

- **不做实时推送与断线恢复**：房间页靠「刷新」取最新记录（首版范围，见平台路线图）。
- **不做队列**：worker 用实例行锁推进（ADR-009），并发到数千对局时再按实测加回来。
- **不做多区域**：单库单区。
- **探针只有 `/health`**：没有 `/ready`。
- **供应商出网只允许公网 https**：内网、回环、元数据段一律拒绝，重定向不跟随。
