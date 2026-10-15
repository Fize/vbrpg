# Phase 1 Auth + Provider Configuration — Threat Model

Scope: administrator-provisioned accounts, username/password login, browser sessions, role-protected management APIs, shared LLM provider/model configuration and provider connection tests. Game execution and room participation are out of scope.

## Assets to Protect

- [ ] Passwords, password hashes, temporary credentials and session cookies.
- [ ] Administrator account and privilege to provision/deactivate accounts or alter providers/models.
- [ ] Provider API keys and encryption root key.
- [ ] Provider endpoint configuration and outbound network access during connection tests.
- [ ] Account status, roles, provider/model availability and audit records.
- [ ] Availability of login and provider management APIs.

## Threats Identified

- [ ] Brute-force/password spraying or username enumeration against login.
- [ ] Session theft, fixation, replay after logout/password reset, or CSRF against cookie-authenticated mutations.
- [ ] Privilege escalation from regular user to administrator, including IDOR in account/provider/model management.
- [ ] SQL injection or malformed payloads through account and provider/model APIs.
- [ ] Provider key disclosure through API responses, logs, errors, database dumps or frontend state.
- [ ] SSRF via administrator-configured provider URLs, including access to loopback, private, link-local or cloud metadata endpoints.
- [ ] DNS rebinding/redirects or response-body leakage during provider connection tests.
- [ ] Bootstrap credential leakage or accidental persistent default administrator credentials.
- [ ] Abuse of connection tests causing provider charges, excessive outbound requests or denial of service.
- [ ] Supply-chain vulnerability introduced by password hashing, cookie, encryption or provider-client dependencies.

## Trust Boundaries

- [ ] Browser to Fastify API: all request bodies, headers, cookies and identifiers are untrusted.
- [ ] Authenticated regular user to administrator-only routes: role checks must be enforced server-side for every operation.
- [ ] API process to PostgreSQL: DB values are sensitive; queries must remain parameterized and authorization must be enforced in application code (no RLS layer since ADR-008).
- [ ] API process to configured LLM provider: provider endpoint and response are external/untrusted; credentials must be scoped to that provider and never returned to browser.
- [ ] Deployment environment/secret manager to API process: bootstrap secret and encryption key require restricted access and rotation procedures.
- [ ] Logs/traces/error reporting: must not receive passwords, cookies, session identifiers, provider keys or raw provider response bodies.

## Mitigations (Planned)

- [ ] Use Argon2id or a reviewed password-hashing library; unique salts and parameters validated against current recommendations; no reversible password storage.
- [ ] Admin-provisioned usernames only; no public registration. One-time bootstrap requires an explicit secret and refuses to run if an administrator already exists; no fixed default credentials. New accounts must change temporary password before other use.
- [ ] Rate-limit login and provider test endpoints; return one generic login failure response; log security outcomes without identifiers/secrets where avoidable.
- [ ] Use opaque random session IDs with only a hash stored in DB; rotate on login/password change; revoke on logout, account disable and password reset; enforce idle/absolute expiry.
- [ ] Set session cookie HttpOnly, Secure in production, SameSite=Lax or stricter, Path=/; use CSRF protection (Origin/Referer validation plus CSRF token for state-changing cookie-authenticated requests).
- [ ] Require explicit server-side admin role checks for every account/provider/model mutation and connection test; fail closed if account/session is inactive.
- [ ] Validate all API payloads with shared Zod schemas; use parameterized Kysely queries; cap lengths and request sizes.
- [ ] Encrypt provider credentials at rest with authenticated encryption (AEAD); use versioned deployment key from secret manager/environment; support rotation; allow secret write/replace but never read-back.
- [ ] Provider connection tests allow only HTTPS and approved hostnames/provider types; reject loopback/private/link-local/metadata IPs after DNS resolution, revalidate on redirects, disable redirects or revalidate every hop, impose strict timeout/response-size limits, and redact upstream error content.
- [ ] Restrict connection-test frequency and concurrency; no arbitrary request headers/body/URL from user input; return only sanitized status/model validation and latency.
- [ ] Add audit events for account provisioning/disable/reset and provider/model/credential changes; audit payloads contain IDs/action metadata only, never secrets.
- [ ] Pin dependencies through lockfile and run `pnpm audit`/appropriate scanner before adding or changing security-sensitive packages; review findings before release.

## Open Decisions / Assumptions

- Login identifier: username (consistent with current `users.username` schema); no email delivery/verification in Phase 1.
- Initial administrator: one-time deployment CLI/bootstrap using an operator-supplied secret; no default password. The exact bootstrap command and secret source are finalized in secure design.
- Provider endpoints: administrators may configure arbitrary OpenAI-compatible HTTPS endpoints. Validate URL syntax; reject credentials in URL and non-HTTPS schemes; reject loopback/private/link-local/multicast/reserved IPs after DNS resolution; prevent DNS rebinding by pinning/validating resolved addresses at connect time; disable redirects or revalidate every redirect hop; apply strict connect/read timeout, response-size caps and outbound request rate limits. Custom endpoints are required in Phase 1.
- Security assumptions require HTTPS in production and protected deployment secret storage.
