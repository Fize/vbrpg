# 备份与恢复手册

平台的状态只在一个地方：PostgreSQL。代码与镜像可以重新构建，**库不能**。

## 1. 目标与实话

| 指标 | 当前能做到 | 需要什么才能更好 |
| --- | --- | --- |
| RPO（最多丢多少） | 上次逻辑备份到现在的写入 | WAL 归档 + PITR（`archive_mode` + pgBackRest / wal-g） |
| RTO（多久恢复） | 一次 `pg_restore` 的时间（实测见 §5） | 同上的基础备份 + 持续归档 |

也就是说：**当前是「按周期做逻辑备份」，不是「任意时间点恢复」**。要 PITR 就得开归档，那不在首版范围内。

## 2. 备份

用 `pg_dump` 的逻辑备份（custom 格式，可并行恢复）：

```bash
# 每天一次，落到与数据库不同的机器/对象存储上
pg_dump --format=custom --no-owner \
  --dbname="$DATABASE_URL" \
  --file="/backups/vbrpg-$(date +%Y%m%dT%H%M%S).pgc"
```

- **保留策略**：日备留 14 天，周备留 12 周，月备留 12 个月；陈旧备份在验证过新备份之后才删。
- **异地**：备份与数据库不在同一台机器、同一个卷、同一个故障域。
- **加密**：`pg_dump` 出来的文件里含**供应商凭据密文**。密文本身需要主密钥才能解开，因此
  **备份与主密钥分开存放**（密钥在密码库，备份在对象存储）；任何一方单独泄漏都不足以用。
- **校验**：每次备份后跑一次 `pg_restore --list` 确认文件可读；定期做完整演练（§4）。

## 3. 恢复

```bash
# 1. 新库（名字随意，别是正在用的那个）
createdb -h <host> -U <user> vbrpg_restore

# 2. 恢复
pg_restore --no-owner --exit-on-error \
  --dbname="postgres://…/vbrpg_restore" /backups/vbrpg-20261016T030000.pgc

# 3. 指向恢复出来的库启动 api/worker（同一个 PLATFORM_CREDENTIAL_KEY）
```

恢复后必须满足两条：

1. **迁移状态一致**：`kysely_migration` 表里的记录与当时部署的代码版本匹配；不一致就先 `pnpm migrate`。
2. **主密钥一致**：`providers.credential_key_version` 指向的密钥必须在手里（否则 AI 席位用不了，
   控制台的连接测试会报解密失败）。密钥换过而备份是换之前的话，按 `credential-rotation.md` 先轮换再上线。

## 4. 演练

`pnpm backup-restore-drill` 做一次真实的备份 → 恢复到临时库 → **用应用的读路径把数据读一遍**：

```bash
DATABASE_URL='postgres://…/<源库>' \
DRILL_DATABASE_URL='postgres://…/<名字里必须含 drill>' \
pnpm backup-restore-drill
```

脚本做的事：

1. 用维护连接（同一主机、库名换成 `postgres`）`drop database … with (force)` + `create database` 重建演练库；
   **库名不含 `drill` 直接拒绝执行**，避免指到真库上。
2. `pg_dump --format=custom` 导出源库，报告大小与耗时。
3. `pg_restore --exit-on-error` 恢复到演练库，报告耗时。
4. 逐表比对行数（`users`、`auth_sessions`、`providers`、`provider_models`、`game_instances`、
   `game_participants`、`game_events`、`audit_logs`、`kysely_migration`）。
5. 取最新一局，用 `createMatchService(...).read()` 在**两个库**上各读一次，比对
   状态、序号、步骤、席位、逐行事件序列与 token 合计。
6. 结束删除演练库（`DRILL_KEEP=1` 保留，便于人工翻看）。

`pg_dump`/`pg_restore` 可以在别处（例如容器里）执行，此时用 `PG_DUMP`/`PG_RESTORE` 传命令前缀、
用 `PG_DUMP_URL`/`PG_RESTORE_URL` 传**工具自己可达**的连接串：

```bash
PG_DUMP='docker exec -i vbrpg-demo-db pg_dump' \
PG_RESTORE='docker exec -i vbrpg-demo-db pg_restore' \
PG_DUMP_URL='postgres://vbrpg:***@127.0.0.1:5432/vbrpg_demo' \
PG_RESTORE_URL='postgres://vbrpg:***@127.0.0.1:5432/vbrpg_demo_drill' \
DATABASE_URL='postgres://vbrpg:***@127.0.0.1:5546/vbrpg_demo' \
DRILL_DATABASE_URL='postgres://vbrpg:***@127.0.0.1:5546/vbrpg_demo_drill' \
pnpm backup-restore-drill
```

### 演练记录

2026-10-16，演示库（6 个账号、6 局对局、含一局三个 AI 席位跑完的完整记录）：

```
Drill: /vbrpg_demo -> /vbrpg_demo_drill
Dump: 0.05 MiB in 196 ms
Restore: 214 ms
Row counts match across 9 tables (208 rows).
Sample match bf6617df-cb8c-4ab2-beaf-fdd5cb96c683 reads back identically: 26 rows, sequence 26, 25183 tokens.
Drill passed: the backup restores into a usable database, and the application reads it.
```

这组数字说明的是**数据量小时的样子**（0.05 MiB / 214 ms），不能当容量承诺；库变大后要重新量，
并且那时 `pg_restore --jobs=4` 之类的并行恢复才有意义。

## 5. 它验证了什么、没验证什么

**验证了**：逻辑备份可用、恢复到空库后迁移状态完整、应用能读、行数与对局逐行一致、密文仍可用（同一主密钥下）。

**没验证**：WAL 归档与时间点恢复；备份介质损坏时的异地副本；恢复期间的服务降级策略。
这几项要等真正的生产环境（PITR + 对象存储 + 恢复演练排期）才有意义。

## 6. 演练频率

- 每次改动**表结构**（新增迁移）之后跑一次。
- 每个发布周期至少一次。
- 恢复步骤每次演练都要照着 §3 走一遍，不要只跑脚本——脚本验证数据，人验证流程。
