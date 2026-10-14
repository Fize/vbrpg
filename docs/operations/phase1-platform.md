# Phase 1 Operations — Platform Accounts and Provider Configuration

Covers administrator bootstrap, account provisioning, session behaviour, provider credential
handling and rollback for the TypeScript platform (`apps/api`, `packages/db`). Security
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
| `AUTH_TOKEN_SECRET` | legacy | Only used by the legacy `/v1/tenant/*` bearer path |
| `AI_TIMEOUT_MS`, `AI_MAX_INPUT_TOKENS`, `AI_CONTEXT_WINDOW_TOKENS` | no | AI command caps for `apps/worker` (and the MVP demo client) |

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
pnpm run build:platform
pnpm run db:migrate:platform
pnpm --filter @vbrpg/api dev
pnpm --filter @vbrpg/worker dev
```

### 2.1 Docker stack (browser testing)

`docker-compose.platform.yml` can also run the whole stack — PostgreSQL, migrations, API and nginx.
Only the web port is published; the API is reachable solely through nginx inside the compose
network, so a host process on port 3000 does not conflict.

```bash
# One-time: the local master key that seals provider credentials (see section 1).
node -e "console.log(require('node:crypto').randomBytes(32).toString('base64'))"
# Store it as PLATFORM_CREDENTIAL_KEY in .env (git-ignored), optionally with PLATFORM_POSTGRES_PASSWORD.

docker compose -f docker-compose.platform.yml up -d --build
docker compose -f docker-compose.platform.yml ps     # platform-api healthy, platform-migrate exited 0

# Create the first administrator; the password is passed through and never written to disk.
docker compose -f docker-compose.platform.yml exec platform-api \
  pnpm --filter @vbrpg/api exec tsx scripts/bootstrap-admin.ts --username admin --password '<12+ chars>'
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

## 6. Agent model bindings and AI command execution

An `aiGenerate` node names an `agentId`, and that agent resolves to exactly one model through
`agent_model_bindings`, keyed by `(tenant_id, game_version_id, agent_id)`. The binding lives with the
game version, so a published version keeps the model it shipped with.

Bindings are provisioned with SQL until an admin endpoint exists:

```sql
insert into agent_model_bindings (id, tenant_id, game_version_id, agent_id, provider_model_id)
values (gen_random_uuid()::text, '<tenant-id>', '<game-version-id>', 'seer', '<provider-model-id>');
```

`apps/worker` consumes both queues: `pending_commands` (AI commands) and `scheduled_jobs` (expired
timers, which re-enter the instance as `timerExpired` events). `outbox_events` still has no handler:
its handler is the broadcast transport, which arrives with the realtime phase, so published events
are not delivered anywhere yet.

Starting the AI side:

```bash
export DATABASE_URL=postgres://vbrpg:vbrpgpassword@localhost:5433/vbrpg_platform
export PLATFORM_CREDENTIAL_KEY=<the key that sealed the provider credential>
pnpm --filter @vbrpg/worker dev
```

For each claimed command the worker resolves the binding, rejects disabled providers or models,
decrypts the provider credential with the master key, calls the OpenAI-compatible endpoint with a
timeout of `min(node timeoutMs, AI_TIMEOUT_MS)`, appends `aiResultReceived` and writes an
`ai_usage_ledger` row.

Behaviour to know before an incident:

- A provider failure below `maxAttempts` returns the command to the queue with exponential backoff.
- At `maxAttempts` the worker appends `aiFailed` and the workflow continues at the node's
  `fallbackNodeId`; an instance is never left parked on an AI node.
- A missing binding, a disabled model, or an undecryptable credential degrades immediately, with no
  retries.
- A command whose instance is no longer waiting for AI is skipped, so a redelivered command cannot
  advance an instance twice.

## 7. Driving an instance over HTTP

The runtime endpoints are session-authenticated (cookie plus `x-csrf-token`), scoped to the platform
tenant, and never accept a client-supplied sequence or event id.

```bash
# Create an instance from a workflow definition and dispatch instanceCreated.
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/instances \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -H "x-csrf-token: $CSRF" \
  -d '{"gameVersionId":"<game-version-id>","randomSeed":"seed-1"}'

# Read the authoritative state.
curl -sS -b cookies.txt http://localhost:3000/v1/instances/<instance-id>

# Submit player input. Retries are safe: reuse the same Idempotency-Key.
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/instances/<instance-id>/events \
  -H 'content-type: application/json' -H 'origin: http://localhost:5173' \
  -H "x-csrf-token: $CSRF" -H 'idempotency-key: answer-1' \
  -d '{"type":"playerInputReceived","payload":{"participantId":"p1","value":"yes"}}'
```

Status codes worth knowing:

- `201` on create; `200` on read and on accepted or replayed events.
- `404 GAME_VERSION_NOT_FOUND` when the version has no workflow definition; `404 INSTANCE_NOT_FOUND`
  otherwise.
- `409` with the engine code (`UNEXPECTED_INPUT`, `SEQUENCE_MISMATCH`, `NOT_ALLOWED`, …) when the
  event does not fit the current state. A retry carrying a recorded idempotency key still returns
  `200` with `replayed: true`, even after the instance finished.
- `429 RATE_LIMITED` after 30 created instances per account per minute.
- Client-submittable events are limited to `playerInputReceived`: timers and AI results come from
  `apps/worker`, and admin controls arrive with `P3-10`.

### 7.1 Administrative controls

Administrators can pause, resume, cancel an instance, force the current wait to expire and read a
redacted operational status. Lifecycle changes are platform state, not game events: they are audited
in `audit_logs` and never enter the game event log.

```bash
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/instances/<id>/pause \
  -H 'origin: http://localhost:5173' -H "x-csrf-token: $CSRF"
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/instances/<id>/resume  -H 'origin: ...' -H "x-csrf-token: $CSRF"
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/instances/<id>/cancel  -H 'origin: ...' -H "x-csrf-token: $CSRF"
curl -sS -b cookies.txt -X POST http://localhost:3000/v1/admin/instances/<id>/timeout -H 'origin: ...' -H "x-csrf-token: $CSRF"
curl -sS -b cookies.txt http://localhost:3000/v1/admin/instances/<id>
```

Behaviour worth knowing during an incident:

- A paused or cancelled instance rejects new events with `409 INSTANCE_PAUSED` / `INSTANCE_CANCELLED`,
  and the worker stops claiming its queued commands and jobs — nothing is consumed, nothing is lost, so
  resuming makes the same rows claimable again with no re-arming step.
- `timeout` ends the current wait immediately: a timer fires now, an AI node takes its declared
  `fallbackNodeId`. Player-input waits return `409 NOT_TIMEOUTABLE` (there is no input-timeout
  semantics yet).
- The status endpoint returns structure without values: lifecycle status, sequence, current node,
  what it is waiting for, participant counts by role and status, variable *names*, and queue counts.
  It never returns variable values, so it is safe to paste into an incident ticket.

### 7.2 What a player is allowed to see

`GET /v1/instances/:instanceId` returns the **authoritative** state, hidden information included, and
is therefore administrator-only. Participants read their own projection instead:

```bash
curl -sS -b cookies.txt "http://localhost:3000/v1/instances/<instance-id>/view?participantId=p1"
```

`view` is rejected with `403 NOT_YOUR_PARTICIPANT` unless the seat's `actorId` is the signed-in
account (administrators may read any seat), and with `404 PARTICIPANT_NOT_FOUND` for a participant
that is not in the instance. The projection follows the definition's `visibility` map and is
**fail-closed** — a variable the definition does not declare never appears:

| `visibility` entry | Who sees it | Bucket |
| --- | --- | --- |
| *(key absent)* | nobody | — |
| `"public"` | everyone, including spectators | `publicState` |
| `{ "role": "<roleId>" }` | participants whose `roleId` matches | `privateState` |
| `{ "participant": "<participantId>" }` | that participant only | `privateState` |

Any other shape is rejected at publish time by the definition validator and again by the runtime, so
a typo cannot silently widen visibility. `availableActions` is non-empty only while the instance
waits on that participant (`playerInput`/`collectInput`); it carries the waiting node id and the
`participantId` to submit.

Instance state is authoritative in `game_instances.state_json`; this path does not write
`game_participants` yet.

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

`0005_phase1_auth_providers.down.sql` refuses to run while provider rows exist, so export and
delete provider data first. The `platform` tenant row seeded by `0005` is intentionally left in
place on rollback. `.down.sql` files are never applied as forward migrations.

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
- [ ] `packages/db/scripts/integration.ts` passes against PostgreSQL.
- [ ] Browser walkthrough: bootstrap → forced password change → login → logout, plus
      administrator provider/model configuration and a connection test.
- [ ] A regular user receives 403 on every `/v1/admin/*` route.
- [ ] No secret appears in API responses, logs or `audit_logs` rows.
- [ ] scrypt parameters re-benchmarked on production-sized hardware.
- [ ] `pnpm audit --prod --audit-level=high` reviewed; findings triaged.
