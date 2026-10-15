# Phase 1 Auth + Provider Configuration — Secure Design

> 2026-10-15 更新（ADR-008）：本文中关于租户与行级隔离的描述已作废——租户层、租户角色与
> PostgreSQL RLS 均已删除，认证只有平台会话一条路径。其余结论（账号、会话、凭据加密、CSRF）仍然有效。

This design implements the confirmed threat model in `docs/security/phase1-auth-provider-threat-model.md`. Scope is administrator-provisioned accounts, login/session, provider/model administration and OpenAI-compatible connection tests. It does not implement game creation, agent execution, rooms or multiplayer.

## Decisions

- Login identifier: normalized username, matching the existing `users.username` model. No public registration or email delivery.
- Roles: platform `admin` and `user` only. There is no tenant layer and no RLS (ADR-008).
- Browser authentication: opaque server-side sessions in PostgreSQL; no bearer token or session identifier in localStorage.
- Password hash: Node.js built-in `crypto.scrypt` with a unique 16-byte random salt, 32-byte derived key and explicit parameters `N=32768, r=8, p=1`; store a versioned encoding. Constant-time derived-key comparison. This avoids a new native password-hashing dependency; parameters must be re-evaluated against production memory/latency before release.
- Provider secret encryption: AES-256-GCM using a 32-byte deployment master key supplied by a secret manager, 12-byte random nonce, 16-byte tag, and a key-version field. Associated data binds ciphertext to provider ID and secret purpose. Never persist plaintext; secret write/replace only, no read-back route.
- Provider type: `openai_compatible`; administrators may configure any HTTPS endpoint satisfying SSRF checks. Each provider has one credential; its models refer to provider-specific `model_id` strings.

## Authentication Flow

### Bootstrap and account provisioning

1. An operator runs a one-time admin bootstrap CLI with the database URL and an operator-supplied username/password through a no-echo prompt or protected secret input. No default password or source-controlled credential.
2. Bootstrap runs transactionally, takes an advisory lock, refuses if any active admin already exists, creates the initial admin, records an audit event, and exits without printing the password. Bootstrap credentials are not persisted outside the password hash.
3. An authenticated admin creates a user with a validated username and temporary password. The API sets `must_change_password=true`; it never returns a reusable generated secret.
4. First successful login creates a session restricted to password change and logout. A successful password change clears the flag and revokes all prior sessions for the account.
5. Admin disable/reset actions revoke all sessions. An inactive account is rejected at every authenticated request.

### Login and session

- Normalize usernames consistently; do not reveal whether a username exists. Unknown user, wrong password, disabled user and malformed credentials return the same generic 401 body.
- Apply per-IP and per-account keyed rate limits to login; enforce request size and field limits. Do not log username, password, cookie, session ID or request body.
- On login, generate 32 random bytes as an opaque session token. Store only SHA-256(token) in the session table, together with user ID, role/authorization source, creation, last-seen, absolute expiry and revocation fields. Rotate/revoke any pre-authentication identifier; do not accept a caller-chosen session ID.
- Cookie: `HttpOnly; Secure` in production; `SameSite=Lax; Path=/`; bounded `Max-Age`; no `Domain`. Development may omit `Secure` only on loopback HTTP. Session absolute lifetime 12 hours; idle expiry 30 minutes, refreshed on authenticated activity with a throttled DB update.
- Every protected request hashes the cookie token, loads a non-revoked/unexpired session, and checks the current user is active. Admin routes check current DB role, not a client-provided claim.
- Logout revokes the current session and clears the cookie. Password change, reset, disable and role change revoke all sessions for the account.
- CSRF: require exact allowed `Origin` for all state-changing cookie-authenticated requests; additionally require a random synchronizer token returned by an authenticated CSRF endpoint and echoed in `X-CSRF-Token`. Store only its hash in the session. No wildcard CORS with credentials.

### Authorization matrix

| Operation | Anonymous | User | Admin |
|---|---:|---:|---:|
| Login | allow | allow | allow |
| Read own session/profile | deny | allow | allow |
| Change own password | deny | allow | allow |
| Create/disable/reset account | deny | deny | allow |
| Read enabled provider/model catalog (public metadata only) | deny | allow | allow |
| Create/update/disable provider or model | deny | deny | allow |
| Write/replace provider credential | deny | deny | allow |
| Run provider connection test | deny | deny | allow |

All admin authorization is enforced in API pre-handlers/service boundaries. Hiding UI controls is not an authorization mechanism.

## Provider and Model Data

- `providers`: UUID, stable key, display name, `openai_compatible` type, HTTPS `base_url`, enabled flag, secret ciphertext, nonce, auth tag, key version, timestamps.
- `provider_models`: UUID, provider ID FK, provider model ID, display name, enabled flag, optional validated capability metadata, timestamps; unique `(provider_id, provider_model_id)`.
- Do not return ciphertext, nonce, tag, master-key version details beyond an opaque configured/absent status, or upstream raw errors to clients.
- Updating credentials replaces ciphertext atomically. Disabling a provider prevents catalog selection and connection tests; references are retained, not cascaded away.
- Agent binding contract is `providerModelId: UUID` (one value, not a list). A binding is valid only if the model and its provider are enabled and share the expected platform scope. Phase 1 defines/tests the Zod contract only; there is no game/agent table or game-binding UI in this phase.
- Audit records identify actor, action, resource IDs, timestamp and success/failure; never contain request bodies, credentials, cookies or upstream response bodies.

## Provider Endpoint and Connection-Test SSRF Controls

Connection tests make privileged outbound requests and are the highest-risk feature in this phase.

1. Parse with `URL`; require `https:`, hostname present, no username/password, no fragment, and an approved path policy. Only administrator-controlled provider records are used; request payload cannot supply an arbitrary URL, headers, method, model or body.
2. Resolve all A/AAAA records. Reject if any target is loopback, private, link-local, multicast, unspecified, reserved, IPv4-mapped private IPv6, or a known metadata range. Normalize IPv4/IPv6 forms before checks.
3. Prevent DNS rebinding/time-of-check/time-of-use: connection must use the validated DNS result (pinned lookup/connector); do not validate DNS and then let a second resolver choose the socket destination. Re-resolve and revalidate on every new connection.
4. Disable redirects. Treat 3xx as sanitized test failure; do not follow provider-controlled `Location` headers.
5. Fixed request shape: a minimal OpenAI-compatible model/list or bounded chat probe, no caller-controlled headers or prompt. Attach the decrypted provider key only as the expected authorization header; never include it in errors.
6. Enforce connect timeout 3s, total timeout 8s, response body maximum 64 KiB, concurrency limit 2 per admin and global cap, plus rate limit 5 tests/minute/admin. Abort request on limits.
7. Return only `{ok, latencyMs, checkedAt, errorCode}` from a closed error-code enum. Do not return response text, headers, URL query, stack trace or provider key. Logs record provider ID, outcome code, duration and request ID only.
8. Permit arbitrary public OpenAI-compatible HTTPS hosts as explicitly required, while blocking prohibited destination IPs at connection time. Production deployment should add egress firewall rules as defense in depth.

## Input Validation and Error Handling

- Define Zod schemas for all request/response payloads in `src/shared`; reject unknown or malformed fields and cap username/password/provider/model/URL lengths.
- Validate provider URL on create/update and again at connection-test time. Do not accept credential fields in URL.
- Use Kysely parameterized queries only. Apply FK/unique/check constraints in Postgres, not only application validation.
- Return generic authentication errors and stable application error codes. Internal logs may contain stack traces only for non-sensitive failures after redaction; never log raw request, cookies, passwords, decrypted keys or provider response bodies.
- Frontend uses text interpolation, not `innerHTML`; secrets are cleared from form state after save/test and are not persisted in browser storage.

## Database and Migrations

- Add account password hash/status/role columns to `users`; there is no tenant model to retain (ADR-008).
- Add/extend `auth_sessions` for `token_hash`, CSRF token hash, `last_seen_at`, absolute expiry, revoked time and indexes. Remove or stop using any bearer-token-only auth path for the browser.
- Add providers, provider_models and audit records with foreign keys, uniqueness and enabled-state constraints. Store encrypted credential material only.
- Authorization is enforced in application code: every protected route re-reads the role from the database. There is no RLS layer (ADR-008).
- Each migration ships a `.down.sql` sidecar. During greenfield the schema is rewritten in place rather than migrated forward, so a stale local database is rebuilt instead of upgraded.

## Security Tests / Release Gates

- Auth integration: generic failure for unknown/wrong/disabled account; no public registration; admin-only provisioning; forced initial password change; scrypt version parsing; session rotation, expiry, logout revocation, password-reset revocation and disabled-user rejection.
- Authorization: regular user receives 403 for every admin endpoint including provider test and secret replacement; tampered IDs cannot access another resource.
- CSRF/Cookie: missing/wrong Origin and CSRF token rejected; cookie flags verified; production refuses weak/missing master key and auth configuration.
- Secret handling: DB contains ciphertext rather than plaintext; secret cannot be read through API; audit/log capture contains no secret, cookie or password; AEAD tamper/wrong key fails closed.
- SSRF: reject HTTP, URL credentials, loopback/private/link-local/metadata IPv4/IPv6, mixed public/private DNS answers, redirects to private targets, DNS rebinding; enforce timeout/body-size/concurrency/rate bounds.
- Provider behavior: valid public test endpoint succeeds; invalid key/429/5xx/oversize/timeout return sanitized error codes; upstream body and headers never reach client/log.
- Dependency/security checks: inspect current lockfile before adding dependencies; run `pnpm audit` and review all high/critical findings. No new security-sensitive dependency without review.

## Dependencies and Remaining Risks

- Prefer Node built-ins and existing Fastify, Zod, Kysely, Postgres dependencies. If the HTTP client cannot safely pin DNS destinations using its current implementation, introduce a narrowly scoped connector/dispatcher only after dependency/CVE review, or use a controlled egress proxy; do not ship an unsafe fetch-based DNS check.
- Scrypt consumes memory; rate limits and bounded concurrency are required to prevent login DoS. Benchmark on deployment-sized hardware and adjust parameters while retaining a versioned hash format.
- CSRF relies on correct production origin configuration; startup must fail for missing/ambiguous trusted web origins in production.
- A compromised admin can alter provider endpoints and consume platform credentials. Mitigations are SSRF protections, audit, rate limits, and least-privilege key scopes; this feature cannot protect against a fully compromised admin account.
- Arbitrary public endpoint support increases outbound attack surface; private-network destinations remain prohibited, so private/on-prem provider endpoints are not supported in Phase 1.
