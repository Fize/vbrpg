# M4 工程门禁与运维 —— 执行计划

落地 `platform-migration-plan.md` 的 M4：让 CI 与运维能挡住回归。

## Goal

改动的代价不再靠人记：风格由格式化器和 lint 挡住，依赖告警由 CI 挡住，密钥轮换有脚本、有演练、有手册。

## Approach

1. **格式与 lint 分开**：Prettier 管格式（写死一份配置），ESLint 管对错（不引入风格规则，用 `eslint-config-prettier` 关掉与 Prettier 冲突的那些）。
   类型检查继续由 `tsc`/`vue-tsc` 三个项目负责，ESLint 不做类型感知，避免两套类型通道。
2. **一次性格式化**：仓库里的代码是手写对齐的，先跑一遍 `prettier --write`，之后由 `--check` 挡回归。
   只覆盖 `apps/**`、根配置文件与 `docs/**`；旧版 `frontend/`、`backend/`、`specsai/` 与产物目录进 ignore。
3. **依赖告警要真的挡住**：当前 `pnpm audit` 在 CI 里是 `continue-on-error`，先把它清干净，再改成硬门禁。
4. **密钥轮换用脚本 + 演练**：运行时只认一个密钥（`PLATFORM_CREDENTIAL_KEY` + 版本号），
   所以轮换不引入密钥环，而是用一个一次性脚本把库里所有密文从旧密钥重封到新密钥；
   脚本幂等、拒绝未知版本，并在真库演练里验证「旧密钥打不开新密文」。

## Impact

| 工作对象                                               | 改动                                                                              |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `apps/platform/package.json`                           | 新增 `lint`/`lint:fix`/`format`/`format:check` 与对应 devDependencies             |
| `apps/platform/eslint.config.js`                       | 新增：flat config（js + typescript-eslint + eslint-plugin-vue + prettier 兼容层） |
| `.prettierrc.json` / `.prettierignore`                 | 新增：格式规则与范围                                                              |
| 全仓（`apps/**`、根配置、`docs/**`）                   | 一次性格式化                                                                      |
| `package.json` / `pnpm-workspace.yaml`                 | `fastify` 升到 `^5.12.7`；override 钉住 `fast-uri` 补丁版本                       |
| `.github/workflows/platform-ci.yml`                    | 新增 lint/format 步骤；`pnpm audit` 从「报告」改成硬门禁                          |
| `apps/platform/scripts/rotate-credential-key.ts`       | 新增：按版本重封全部供应商凭据                                                    |
| `apps/platform/src/server/db/platform-repositories.ts` | 新增：列出待轮换凭据、写回重封后的凭据                                            |
| `apps/platform/scripts/db-integration.ts`              | 新增：真库轮换演练（旧密钥失效、新密钥可用、幂等）                                |
| `docs/operations/credential-rotation.md`               | 新增：轮换与回滚手册                                                              |

## Tasks

- [x] `H-01` 依赖告警清零：升 `fastify`、钉 `fast-uri`，`pnpm audit --prod` 归零。
- [x] `H-02` lint + 格式：配置、一次性格式化、脚本与 CI 步骤。
- [x] `H-03` 密钥轮换：脚本 + 仓库函数 + 真库演练 + 手册。
- [x] `H-04` CI 硬门禁：lint/format/audit 都不再 `continue-on-error`。
- [x] `H-05` 门禁全绿：`typecheck`、`test`、`build`、`test:db`、`test:e2e`、`lint`、`format:check`、`audit`。
- [x] `H-06` 备份恢复演练：`pnpm backup-restore-drill`（真库导出 → 临时库恢复 → 用应用读路径比对）+ 手册与记录。
- [x] `H-07` 部署手册重写：`docs/operations/deployment.md` 取代旧的英文 phase1 手册（含本地运行、升级回滚、观测、排障）。

## 完成情况

- `H-01`：`fastify` 升到 `^5.12.7`；`fast-uri` 的传递依赖补丁版本由 `pnpm-workspace.yaml` 的 override 钉住
  （`fastify` 用它解析请求 URL，受影响的是主机名混淆与 SSRF 那几条）。`pnpm audit --prod` 归零，CI 里改成硬门禁。
- `H-02`：Prettier 管格式（`printWidth 100`、双引号、`lf`），ESLint flat config 管对错
  （`js` + `typescript-eslint` + `eslint-plugin-vue` + `eslint-config-prettier`，不做类型感知 —— 类型由三个 tsc 项目负责）。
  一次性格式化 60 个文件；`docs/` 不进格式化器（Prettier 按字符数对齐中文表格只会越排越歪）。
  lint 顺手清掉 6 处死代码（未使用的导入与类型、一个未赋值的 `defineProps`）。
- `H-03`：`rotateProviderCredentials`（模块）+ `pnpm rotate-credential-key`（CLI，密钥只走环境变量）；
  真库演练覆盖 v1 → v2 明文不变、旧密钥失效、重复跑是空操作、未声明版本中止、反向转回 v1；手册见
  `docs/operations/credential-rotation.md`。
- `H-04`：CI 里 `format:check`、`lint`、`audit --prod --audit-level=high` 全部不再是 `continue-on-error`。
- `H-05`：`format:check`、`lint`、`typecheck`、`test`（160 例）、`build`、`test:db`、`test:e2e`（9 例）、
  `audit --prod` 全绿。
- `H-06`：演练脚本按「导出 → 重建演练库 → 恢复 → 逐表行数 → 用 `createMatchService().read()` 在两库各读一次
  比对状态/序号/席位/逐行事件/token」的顺序做，库名不含 `drill` 直接拒绝执行。实测（演示库，6 账号 6 局）：
  导出 0.05 MiB / 196 ms，恢复 214 ms，9 张表 208 行一致，最新一局 26 行记录逐行一致。
  明确没验证的是 PITR 与异地损坏副本，手册里写清了。
- `H-07`：旧英文手册 `phase1-platform.md` 删除，其中仍然成立的内容（角色、配置、本地运行、迁移回滚、
  供应商出网策略的指向）并入 `deployment.md`；出网与 SSRF 策略本身仍在 `docs/security/`、`docs/design/`。

## 已知边界

- 本地跑 e2e 时 Playwright 会复用已有 dev server（`reuseExistingServer: !CI`）。上一轮刚结束、进程还没退干净时
  复用会踩到刚被 `drop database` 掉的库，表现为整轮登录失败；等它退掉或杀掉 3100/5174 再跑即可。
  CI 每轮都是新库新进程（`reuseExistingServer: false`），不受影响。登录限流（每账号 5 次/分钟）也会跨轮次累积。
- `frontend/`、`backend/`、`specsai/`、根目录那几个旧脚本不在 lint/格式范围内，等清理旧世界时一并处理。
