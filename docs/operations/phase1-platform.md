# Phase 1 Operations — Platform Accounts and Provider Configuration

Covers administrator bootstrap, account provisioning, session behaviour, provider credential
handling and rollback for the TypeScript platform (`apps/platform`: `src/server`, `src/browser`, `src/shared`). Security
boundaries are defined in `docs/security/phase1-auth-provider-threat-model.md` and
`docs/design/phase1-auth-provider-secure-design.md`; the HTTP contract is frozen in
`docs/api/phase1-openapi.yaml`.

## 1. Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | PostgreSQL connection for the platform schema |
| `PLATFORM_CREDENTIAL_KEY` | yes in production | Base64-encoded 32-byte master key for provider credentials |
| `PLATFORM_CREDENTIAL_KEY_VERSION` | no (default `1`) | Key version recorded with each sealed credential |
| `TRUSTED_WEB_ORIGINS` | yes in production | Comma-separated exact origins allowed for cookie-authenticated writes |
| `PORT`, `LOG_LEVEL`, `NODE_ENV` | no | Server basics |

Startup fails when production configuration is weak:

- `PLATFORM_CREDENTIAL_KEY` missing, or not exactly 32 bytes after base64 decoding.
- `TRUSTED_WEB_ORIGINS` empty, or containing a non-`https://` origin.

Generate a master key once and store it in the deployment secret manager:

```bash
node -e "console.log(require('node:crypto').randomBytes(32).toString('base64'))"
```

Development and test default the trusted origins to `http://localhost:5173`,
`http://localhost:3000` and `http://127.0.0.1:5173`, and omit the `Secure` cookie attribute so
loopback HTTP stays usable. Never ship those defaults.

## 2. Local startup

```bash
docker compose -f docker-compose.platform.yml up -d
export DATABASE_URL=postgres://vbrpg:vbrpgpassword@localhost:5433/vbrpg_platform
export PLATFORM_CREDENTIAL_KEY=$(node -e "console.log(require('node:crypto').randomBytes(32).toString('base64'))")

pnpm install --frozen-lockfile
pnpm run build
pnpm run migrate
pnpm dev          # api role + static console
pnpm dev:worker   # worker role
pnpm dev:web      # vite dev server for the console
```

### 2.1 Docker stack (browser testing)

`docker-compose.platform.yml` can also run the whole stack — PostgreSQL, migrations, one `platform`
service (api role, which also serves the built console) and a `platform-worker` service that reuses the
same image with `--role=worker`. Only the platform port is published, so a host process on port 3000
does not conflict.

```bash
# One-time: the local master key that seals provider credentials (see section 1).
node -e "console.log(require('node:crypto').randomBytes(32).toString('base64'))"
# Store it as PLATFORM_CREDENTIAL_KEY in .env (git-ignored), optionally with PLATFORM_POSTGRES_PASSWORD.

docker compose -f docker-compose.platform.yml up -d --build
docker compose -f docker-compose.platform.yml ps     # platform healthy, platform-migrate exited 0

# Create the first administrator; the password is passed through and never written to disk.
docker compose -f docker-compose.platform.yml exec platform \
  pnpm bootstrap-admin --username admin --password '<12+ chars>'
```

Then open `http://localhost:8080`. The stack deliberately runs `NODE_ENV=development`: session
cookies omit `Secure` and `TRUSTED_WEB_ORIGINS` is `http://localhost:8080,http://127.0.0.1:8080`.
It is a local HTTP test stack, not a production profile — apply section 9 before any real release.

```bash
docker compose -f docker-compose.platform.yml down      # stop the stack
docker compose -f docker-compose.platform.yml down -v   # stop and delete the database volume
```

## 3. First administrator (one-time bootstrap)

There is no self-registration. The first administrator is created by an operator-run CLI that
takes an advisory lock, refuses to run when an active administrator already exists, and never
prints or stores the password outside the password hash:

```bash
DATABASE_URL=... pnpm run bootstrap:platform-admin
# prompts: Username: / Password: (password input is not echoed)
```

Non-interactive use (secret supplied through a protected mechanism, not a shared script):

```bash
DATABASE_URL=... pnpm run bootstrap:platform-admin -- --username root --password '<12+ chars>'
```

The created account has `must_change_password = true`, so the first login may only read the
session, read the CSRF token and change the password.

## 4. Provisioning users

An authenticated, password-changed administrator creates accounts. The API never returns the
temporary password, and the account must change it at first login.

```bash
# 1. Log in and keep the session cookie + CSRF token.
curl -sS -c cookies.txt -X POST http://localhost:3000/v1/auth/login \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -d '{"username":"root","password":"<password>"}'

# 2. Change the initial password (also rotates the session).
curl -sS -b cookies.txt -c cookies.txt -X POST http://localhost:3000/v1/auth/password \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -H "x-csrf-token: $CSRF" \
  -d '{"currentPassword":"<old>","newPassword":"<new, 12+ chars>"}'

# 3. Create a user.
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/users \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -H "x-csrf-token: $CSRF" \
  -d '{"username":"alice","temporaryPassword":"<12+ chars>","role":"user"}'
```

Disabling an account, resetting a password or changing a role revokes every session for that
account. The last active administrator cannot be demoted or disabled (`409 LAST_ADMIN`).

## 5. Provider and model configuration

Provider credentials are write-only: they are sealed with AES-256-GCM under
`PLATFORM_CREDENTIAL_KEY`, bound to the provider id as associated data, and are never returned by
any endpoint or written to logs or audit rows.

```bash
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/providers \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -H "x-csrf-token: $CSRF" \
  -d '{"name":"primary","baseUrl":"https://api.example.com/v1","apiKey":"sk-..."}'

curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/providers/$PROVIDER_ID/models \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -H "x-csrf-token: $CSRF" \
  -d '{"modelId":"hy3","displayName":"Hy3"}'

curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/providers/$PROVIDER_ID/test \
  -H 'origin: http://localhost:5173' -H "x-csrf-token: $CSRF"
```

Endpoint rules (enforced on create, update and every connection test):

- `https:` only, no credentials in the URL, no fragment.
- All DNS answers must be public; loopback, private, link-local, multicast, reserved and metadata
  ranges are refused, including IPv4-mapped and 6to4 forms.
- The validated address is pinned into the connection, so a rebinding record cannot redirect the
  socket. Redirects are not followed; a 3xx is a sanitized failure.
- Connection tests use a fixed `GET <baseUrl>/models` probe with no caller-controlled headers or
  body, 3 s connect / 8 s total timeouts, a 64 KiB response cap, 5 tests per minute per
  administrator and at most 2 concurrent tests per administrator.
- Only `{ok, latencyMs, checkedAt, errorCode}` is returned; upstream status text, headers and
  bodies never reach the client.

Private and on-premises endpoints are intentionally unsupported in Phase 1.

## 6. Model credentials

Model providers and their models are managed through the admin endpoints in section 5. Their API keys
are sealed with `PLATFORM_CREDENTIAL_KEY` (AES-GCM, bound to the provider id) in `src/server/runtime`
and are never returned by any endpoint.

There is no platform-side AI call chain right now: the AI command queue, its retries, fallbacks and the
usage ledger went away with the declarative game DSL (see the migration plan, §16 第六轮). Game modules
that need a model resolve a provider credential themselves; usage and cost accounting come back with the
code-based game runtime.

## 7. Game instances

The match foundation is still migrated and enforced: `game_instances`, `game_participants`,
`game_events`, `game_snapshots`, `pending_commands` and `scheduled_jobs`. The worker role claims leases
from the two queues; there is no outbox table (see ADR-008) and no tenant layer.

What is gone: the HTTP surface (`POST /instances`, `GET /instances/:id`, the per-seat projection, the
admin pause/resume/cancel/timeout controls) and the state transition that drove them. They return with
the code-based game runtime, together with the `GameModule` interface and the game registry.


## 8. Master key rotation

1. Generate a new key and set `PLATFORM_CREDENTIAL_KEY` / `PLATFORM_CREDENTIAL_KEY_VERSION` to the
   new values.
2. For each provider, re-submit the API key through `PATCH /v1/admin/providers/{id}` with
   `{"apiKey": "..."}`. The row is re-sealed under the new version atomically.
3. Providers still carrying an older `credential_key_version` fail closed: decrypting them raises
   an error rather than falling back to the previous key. Run a connection test per provider to
   confirm re-sealing.

## 9. Database migration and rollback

```bash
pnpm run db:migrate:platform          # apply all `.sql` migrations
pnpm run migrate:down:platform        # roll back the last migration (use --steps=N for more)
```

`0001_accounts_and_models.down.sql` drops the account, session, catalog and audit tables, so export
the data you care about first. `.down.sql` files are never applied as forward migrations.

## 10. Troubleshooting

| Symptom | Cause |
| --- | --- |
| `PLATFORM_CREDENTIAL_KEY is required in production` | Master key not configured |
| `CREDENTIAL_KEY_NOT_CONFIGURED` on provider create | Master key absent in a non-production environment |
| `ORIGIN_REQUIRED` / `ORIGIN_NOT_ALLOWED` | `Origin` missing or not in `TRUSTED_WEB_ORIGINS` |
| `CSRF_TOKEN_INVALID` | Missing `x-csrf-token`, or the token belongs to a rotated session |
| `PASSWORD_CHANGE_REQUIRED` | Initial password not changed yet |
| `LAST_ADMIN` | Attempt to disable or demote the only active administrator |
| `dns_rejected` on a connection test | Endpoint resolves to a non-public address |
| `SESSION_INVALID` after a password or role change | Sessions are revoked by design |

## 11. Release checklist

- [ ] `pnpm run build:platform` and `pnpm run test:platform` pass.
- [ ] `pnpm run test:contracts` and `pnpm run test:db` pass.
- [ ] Migrations apply and roll back on a fresh database, then re-apply.
- [ ] `pnpm run test:db` passes against PostgreSQL.
- [ ] Browser walkthrough: bootstrap → forced password change → login → logout, plus
      administrator provider/model configuration and a connection test.
- [ ] A regular user receives 403 on every `/v1/admin/*` route.
- [ ] No secret appears in API responses, logs or `audit_logs` rows.
- [ ] scrypt parameters re-benchmarked on production-sized hardware.
- [ ] `pnpm audit --prod --audit-level=high` reviewed; findings triaged.
