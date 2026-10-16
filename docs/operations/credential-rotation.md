# 主密钥轮换手册

供应商凭据用 AES-256-GCM 封在 `providers` 表里，AAD 绑定 provider id，每条记录带一个 `credential_key_version`。
运行时**只认一个密钥**（`PLATFORM_CREDENTIAL_KEY` + `PLATFORM_CREDENTIAL_KEY_VERSION`），没有密钥环，
所以轮换不是「新旧并存」，而是**用两个密钥跑一次迁移**，把库里所有密文重封到新版本上。

脚本：`apps/platform/scripts/rotate-credential-key.ts`（`pnpm rotate-credential-key`）。
两个密钥只走环境变量，不走命令行 —— 命令行对同机所有进程可见。

## 什么时候要轮换

- 主密钥可能已泄漏（进过聊天记录、日志、镜像层、离职人员的环境变量）。
- 例行轮换周期到了（建议不晚于一年一次）。
- 分隔环境：把演示/测试环境的密钥换成与生产无关的。

## 前置条件

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 要轮换的库 |
| `ROTATE_FROM_KEY` | 旧密钥（base64，32 字节） |
| `ROTATE_FROM_VERSION` | 旧密钥版本号，必须与库里 `credential_key_version` 一致 |
| `ROTATE_TO_KEY` | 新密钥（base64，32 字节） |
| `ROTATE_TO_VERSION` | 新版本号，必须大于旧版本号，且随后部署时 `PLATFORM_CREDENTIAL_KEY_VERSION` 要用同一个值 |

新密钥生成：`node -e "console.log(require('node:crypto').randomBytes(32).toString('base64'))"`。

**先备份**：`pg_dump` 整库，或至少 `\copy (select * from providers) to 'providers.csv'`。
轮换本身不删数据，但写坏一个密钥就没有第二条路。

## 步骤

1. 生成新密钥与版本号，写入运维密码库（不要只放在某个人的 `.env` 里）。
2. 备份数据库。
3. 跑脚本：

   ```bash
   DATABASE_URL=postgres://… \
   ROTATE_FROM_KEY='<旧>' ROTATE_FROM_VERSION=1 \
   ROTATE_TO_KEY='<新>'   ROTATE_TO_VERSION=2 \
   pnpm rotate-credential-key
   ```

   输出形如 `Credential rotation finished: 3 rotated, 0 already on version 2.`，逐条打印 provider id 与版本迁移，
   凭据明文从不打印。
4. **校验**：用**旧**密钥跑一次该环境的 API，调用管理员接口 `POST /v1/admin/providers/:id/test`，
   应当因为版本不匹配而解密失败 —— 这证明库里已经不认旧密钥；真正的可用性由下一步证明。
5. 用新密钥（`PLATFORM_CREDENTIAL_KEY` + `PLATFORM_CREDENTIAL_KEY_VERSION=2`）滚动重启 `api` 与 `worker`，
   同一个 `POST /admin/providers/:id/test` 应返回 `ok: true`，并跑一局至少带一个 AI 席位的对局。
6. 从所有环境与部署配置里移除旧密钥。

## 回滚

脚本可反向跑，这是唯一的回滚路径：

```bash
DATABASE_URL=postgres://… \
ROTATE_FROM_KEY='<新>' ROTATE_FROM_VERSION=2 \
ROTATE_TO_KEY='<旧>'   ROTATE_TO_VERSION=1 \
pnpm rotate-credential-key
```

前提是旧密钥还在手上，因此**第 6 步之前不要销毁旧密钥**。

## 脚本的边界

- **只覆盖 `providers` 的凭据列**。账号密码是 scrypt 哈希、会话是不透明随机 token，都不经过主密钥，轮换不影响它们。
- **失败即停，不做半途回退**：遇到「版本既不是 from 也不是 to」或「旧密钥打不开」时立刻停下并报出 provider id。
  已经转过的行留在新版本上；只要旧密钥还在手上，修好原因后再跑一次即可续做（已转的行会被跳过）。
- **幂等**：重复跑报告 `0 rotated, N already on version N`。
- **不能同时改两个变量**：脚本迁移的是**密文版本**，部署改的是**运行时读哪个版本**，两者必须对齐，
  中间窗口里 api/worker 会解不开旧记录 —— 所以脚本与重启要连着做，别隔夜。

## 演练

`pnpm test:db` 里有真库轮换用例（`scripts/db-integration.ts`）：v1 → v2 后明文不变、旧密钥失效、
重复跑是空操作、未声明的版本会中止、并能反向转回 v1。这条用例在 CI 里每次都会跑。
