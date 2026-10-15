import assert from "node:assert/strict";
import { randomBytes, randomUUID } from "node:crypto";
import { describe, it } from "vitest";
import type { PlatformStore, ProviderView, SessionRecord } from "../store.js";
import { buildApp } from "../app.js";
import { loadConfig } from "../config.js";
import { hashPassword } from "../password.js";
import { hashToken } from "../session.js";
import { hashCsrfToken } from "../csrf.js";
import { sealCredential } from "../runtime/index.js";
import type { PlatformUserRecord } from "../db/index.js";

const ORIGIN = "http://localhost:5173";
const MASTER_KEY = randomBytes(32).toString("base64");
const PASSWORD = "initial-password-1";

interface FakeState {
  store: PlatformStore;
  audits: Array<Record<string, unknown>>;
  sessions: Map<string, SessionRecord & { tokenHash: string }>;
}

function pgError(code: string): Error & { code: string } {
  const error = new Error("postgres error") as Error & { code: string };
  error.code = code;
  return error;
}

function createFakeStore(options: {
  passwordHash: string;
  users: PlatformUserRecord[];
  /** Accounts the fake database refuses to delete because a match row references them. */
  historyUserIds?: string[];
}): FakeState {
  const users = new Map(options.users.map((user) => [user.id, user]));
  const sessions = new Map<string, SessionRecord & { tokenHash: string }>();
  const providers = new Map<string, ProviderView>();
  const secrets = new Map<string, { baseUrl: string; enabled: boolean; sealed: ReturnType<typeof sealCredential> }>();
  const audits: Array<Record<string, unknown>> = [];

  const store: PlatformStore = {
    findUserByUsername: async (username) =>
      [...users.values()].find((user) => user.username === username),
    getUser: async (userId) => users.get(userId),
    listUsers: async () => [...users.values()],
    createUser: async (input) => {
      const created: PlatformUserRecord = {
        id: randomUUID(),
        username: input.username,
        passwordHash: input.passwordHash,
        role: input.role,
        active: true,
        createdAt: new Date(),
      };
      if ([...users.values()].some((user) => user.username === created.username)) {
        const error = new Error("duplicate username") as Error & { code: string };
        error.code = "23505";
        throw error;
      }
      users.set(created.id, created);
      return created;
    },
    updateUser: async (userId, patch) => {
      const existing = users.get(userId);
      if (!existing) return undefined;
      const updated: PlatformUserRecord = {
        ...existing,
        ...(patch.role === undefined ? {} : { role: patch.role }),
        ...(patch.active === undefined ? {} : { active: patch.active }),
        ...(patch.passwordHash === undefined ? {} : { passwordHash: patch.passwordHash }),
      };
      users.set(userId, updated);
      return updated;
    },
    countActiveAdmins: async () =>
      [...users.values()].filter((user) => user.role === "admin" && user.active).length,
    deleteUser: async (userId) => {
      // Mirrors the database: rows that reference the account block the delete.
      if (options.historyUserIds?.includes(userId)) {
        throw pgError("23503");
      }
      return users.delete(userId);
    },

    createSession: async (input) => {
      const id = randomUUID();
      sessions.set(id, {
        id,
        userId: input.userId,
        csrfTokenHash: input.csrfTokenHash,
        idleExpiresAt: input.idleExpiresAt,
        absoluteExpiresAt: input.absoluteExpiresAt,
        tokenHash: input.tokenHash.toString("hex"),
      });
      return id;
    },
    findSessionByTokenHash: async (tokenHash) => {
      const now = new Date();
      const match = [...sessions.values()].find((session) => session.tokenHash === tokenHash.toString("hex"));
      if (!match) return undefined;
      if (match.idleExpiresAt <= now || match.absoluteExpiresAt <= now) return undefined;
      return match;
    },
    touchSession: async (sessionId, idleExpiresAt) => {
      const session = sessions.get(sessionId);
      if (session) session.idleExpiresAt = idleExpiresAt;
    },
    rotateCsrfToken: async (sessionId, csrfTokenHash) => {
      const session = sessions.get(sessionId);
      if (session) session.csrfTokenHash = csrfTokenHash;
    },
    revokeSession: async (sessionId) => {
      sessions.delete(sessionId);
    },
    revokeUserSessions: async (userId) => {
      for (const [id, session] of sessions) {
        if (session.userId === userId) sessions.delete(id);
      }
    },

    listProviders: async ({ includeDisabled }) =>
      [...providers.values()].filter((provider) => includeDisabled || provider.enabled),
    getProviderView: async (providerId) => providers.get(providerId),
    getProviderSecret: async (providerId) => secrets.get(providerId),
    createProvider: async (input) => {
      const view: ProviderView = {
        id: input.id,
        name: input.name,
        baseUrl: input.baseUrl,
        enabled: input.enabled,
        secretConfigured: input.credential.credential_ciphertext.length > 0,
        models: [],
      };
      providers.set(view.id, view);
      secrets.set(view.id, { baseUrl: input.baseUrl, enabled: input.enabled, sealed: input.credential });
      return view;
    },
    updateProvider: async (providerId, patch) => {
      const existing = providers.get(providerId);
      if (!existing) return undefined;
      const updated: ProviderView = {
        ...existing,
        ...(patch.name === undefined ? {} : { name: patch.name }),
        ...(patch.baseUrl === undefined ? {} : { baseUrl: patch.baseUrl }),
        ...(patch.enabled === undefined ? {} : { enabled: patch.enabled }),
        ...(patch.credential === undefined ? {} : { secretConfigured: true }),
      };
      providers.set(providerId, updated);
      const secret = secrets.get(providerId);
      if (patch.credential && secret) {
        secrets.set(providerId, { ...secret, sealed: patch.credential });
      }
      return updated;
    },
    createProviderModel: async (input) => {
      const provider = providers.get(input.providerId);
      if (!provider) return undefined;
      const model = {
        id: randomUUID(),
        providerId: input.providerId,
        modelId: input.modelId,
        displayName: input.displayName,
        enabled: input.enabled,
      };
      provider.models.push(model);
      return model;
    },
    updateProviderModel: async (modelRecordId, patch) => {
      for (const provider of providers.values()) {
        const model = provider.models.find((candidate) => candidate.id === modelRecordId);
        if (model) {
          Object.assign(model, patch);
          return model;
        }
      }
      return undefined;
    },
    deleteProvider: async (providerId) => {
      const provider = providers.get(providerId);
      // Mirrors the on-delete-restrict foreign key from provider_models.
      if (provider && provider.models.length > 0) throw pgError("23503");
      const deleted = providers.delete(providerId);
      secrets.delete(providerId);
      return deleted;
    },
    deleteProviderModel: async (modelRecordId) => {
      for (const provider of providers.values()) {
        const index = provider.models.findIndex((candidate) => candidate.id === modelRecordId);
        if (index >= 0) {
          provider.models.splice(index, 1);
          return true;
        }
      }
      return false;
    },

    recordAudit: async (input) => {
      audits.push({ ...input });
    },
  };

  return { store, audits, sessions };
}

function makeUser(overrides: Partial<PlatformUserRecord> & { passwordHash: string }): PlatformUserRecord {
  return {
    id: randomUUID(),
    username: "alice",
    role: "user",
    active: true,
    createdAt: new Date(),
    ...overrides,
  };
}

async function createApp(state: FakeState) {
  return buildApp({
    config: loadConfig({
      NODE_ENV: "test",
      TRUSTED_WEB_ORIGINS: ORIGIN,
      PLATFORM_CREDENTIAL_KEY: MASTER_KEY,
    }),
    platformStore: state.store,
  });
}

async function login(
  app: Awaited<ReturnType<typeof createApp>>,
  username = "alice",
  password = PASSWORD,
) {
  const response = await app.inject({
    method: "POST",
    url: "/v1/auth/login",
    headers: { origin: ORIGIN },
    payload: { username, password },
  });
  const cookie = response.headers["set-cookie"];
  return {
    response,
    cookie: Array.isArray(cookie) ? (cookie[0] ?? "") : (cookie ?? ""),
    body: response.json() as { csrfToken?: string; user?: Record<string, unknown> },
  };
}

describe("platform login", () => {
  it("returns an identical generic failure for unknown, wrong and disabled accounts", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [
        makeUser({ passwordHash, username: "alice" }),
        makeUser({ passwordHash, username: "disabled", active: false }),
      ],
    });
    const app = await createApp(state);

    const unknown = await login(app, "nobody", PASSWORD);
    const wrong = await login(app, "alice", "wrong-password-1");
    const disabled = await login(app, "disabled", PASSWORD);

    assert.equal(unknown.response.statusCode, 401);
    assert.equal(wrong.response.statusCode, 401);
    assert.equal(disabled.response.statusCode, 401);
    // Request ids necessarily differ; the caller-visible failure must not.
    const shape = (response: { json(): Record<string, unknown> }) => {
      const { error, code, details } = response.json();
      return { error, code, details };
    };
    assert.deepEqual(shape(unknown.response), shape(wrong.response));
    assert.deepEqual(shape(wrong.response), shape(disabled.response));
    assert.equal(unknown.response.json().code, "INVALID_CREDENTIALS");
  });

  it("issues an HttpOnly session cookie and a CSRF token on success", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);

    const { response, cookie, body } = await login(app);
    assert.equal(response.statusCode, 200);
    assert.match(cookie, /^vbrpg_session=/);
    assert.match(cookie, /HttpOnly/);
    assert.match(cookie, /SameSite=Lax/);
    assert.match(cookie, /Path=\//);
    assert.ok(body.csrfToken && body.csrfToken.length > 20);
    assert.equal(body.user?.username, "alice");
    assert.ok(!("passwordHash" in (body.user ?? {})));
  });

  it("does not leak the password or session token into the audit trail", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    const { cookie } = await login(app);

    const serialized = JSON.stringify(state.audits);
    assert.ok(!serialized.includes(PASSWORD));
    assert.ok(!serialized.includes(passwordHash));
    assert.ok(!serialized.includes(cookie));
  });

  it("rate limits repeated attempts for the same account", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);

    const statuses: number[] = [];
    for (let attempt = 0; attempt < 7; attempt += 1) {
      statuses.push((await login(app, "alice", "wrong-password-1")).response.statusCode);
    }
    assert.ok(statuses.includes(429));
    assert.equal(statuses.at(-1), 429);
  });

  it("has no public registration endpoint", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    for (const url of ["/v1/auth/register", "/v1/auth/signup", "/v1/users"]) {
      const response = await app.inject({ method: "POST", url, payload: {} });
      assert.equal(response.statusCode, 404, url);
    }
  });
});

describe("session enforcement", () => {
  it("rejects an unauthenticated read", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    assert.equal((await app.inject({ method: "GET", url: "/v1/me" })).statusCode, 401);
  });

  it("rejects a forged session token", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    const response = await app.inject({
      method: "GET",
      url: "/v1/me",
      headers: { cookie: `vbrpg_session=${randomBytes(32).toString("base64url")}` },
    });
    assert.equal(response.statusCode, 401);
  });

  it("does not store the raw token", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    const { cookie } = await login(app);
    const token = cookie.slice(cookie.indexOf("=") + 1, cookie.indexOf(";"));
    assert.equal([...state.sessions.values()][0]?.tokenHash, hashToken(token).toString("hex"));
  });

  it("revokes the session on logout", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const logout = await app.inject({
      method: "POST",
      url: "/v1/auth/logout",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
    });
    assert.equal(logout.statusCode, 204);
    assert.equal(
      (await app.inject({ method: "GET", url: "/v1/me", headers: { cookie } })).statusCode,
      401,
    );
  });
});

describe("CSRF and origin enforcement", () => {
  it("allows an admin read without an Origin or CSRF header", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie } = await login(app);

    // Browsers omit Origin on same-origin GET, so reads must not require CSRF.
    const users = await app.inject({ method: "GET", url: "/v1/admin/users", headers: { cookie } });
    assert.equal(users.statusCode, 200, users.body);
    const providers = await app.inject({ method: "GET", url: "/v1/admin/providers", headers: { cookie } });
    assert.equal(providers.statusCode, 200, providers.body);
  });

  it("rejects a write with no Origin", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/admin/users",
      headers: { cookie, "x-csrf-token": body.csrfToken as string },
      payload: { username: "bob", temporaryPassword: "temporary-pw-1", role: "user" },
    });
    assert.equal(response.statusCode, 403);
    assert.equal(response.json().code, "ORIGIN_REQUIRED");
  });

  it("rejects a write from an untrusted Origin", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/admin/users",
      headers: { cookie, origin: "https://evil.example.com", "x-csrf-token": body.csrfToken as string },
      payload: { username: "bob", temporaryPassword: "temporary-pw-1", role: "user" },
    });
    assert.equal(response.statusCode, 403);
    assert.equal(response.json().code, "ORIGIN_NOT_ALLOWED");
  });

  it("rejects a write with a missing or wrong CSRF token", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie } = await login(app);

    for (const headers of [
      { cookie, origin: ORIGIN },
      { cookie, origin: ORIGIN, "x-csrf-token": "not-the-token" },
    ]) {
      const response = await app.inject({
        method: "POST",
        url: "/v1/admin/users",
        headers,
        payload: { username: "bob", temporaryPassword: "temporary-pw-1", role: "user" },
      });
      assert.equal(response.statusCode, 403);
      assert.equal(response.json().code, "CSRF_TOKEN_INVALID");
    }
  });
});

describe("authorization", () => {
  it("denies every admin endpoint to a regular user", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    const { cookie, body } = await login(app);
    const headers = { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string };

    const responses = await Promise.all([
      app.inject({ method: "GET", url: "/v1/admin/users", headers }),
      app.inject({ method: "GET", url: "/v1/admin/providers", headers }),
      app.inject({
        method: "POST",
        url: "/v1/admin/users",
        headers,
        payload: { username: "bob", temporaryPassword: "temporary-pw-1", role: "user" },
      }),
      app.inject({
        method: "POST",
        url: "/v1/admin/providers",
        headers,
        payload: { name: "p", baseUrl: "https://api.example.com/v1", apiKey: "sk-x" },
      }),
      app.inject({
        method: "POST",
        url: `/v1/admin/providers/${randomUUID()}/test`,
        headers,
      }),
      app.inject({
        method: "PATCH",
        url: `/v1/admin/users/${randomUUID()}`,
        headers,
        payload: { active: false },
      }),
      app.inject({ method: "DELETE", url: `/v1/admin/users/${randomUUID()}`, headers }),
      app.inject({ method: "DELETE", url: `/v1/admin/providers/${randomUUID()}`, headers }),
      app.inject({ method: "DELETE", url: `/v1/admin/models/${randomUUID()}`, headers }),
    ]);
    for (const response of responses) {
      assert.equal(response.statusCode, 403, response.body);
      assert.equal(response.json().code, "INSUFFICIENT_ROLE");
    }
  });

  it("refuses to disable the last active administrator", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const admin = makeUser({ passwordHash, role: "admin", username: "root" });
    const state = createFakeStore({ passwordHash, users: [admin] });
    const app = await createApp(state);
    const { cookie, body } = await login(app, "root");

    const response = await app.inject({
      method: "PATCH",
      url: `/v1/admin/users/${admin.id}`,
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      payload: { active: false },
    });
    assert.equal(response.statusCode, 409);
    assert.equal(response.json().code, "LAST_ADMIN");
  });
});

describe("password change", () => {
  it("rejects a wrong current password", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/auth/password",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      payload: { currentPassword: "not-the-password", newPassword: "a-new-password-1" },
    });
    assert.equal(response.statusCode, 403);
    assert.equal(response.json().code, "CURRENT_PASSWORD_INVALID");
  });

  it("revokes prior sessions and rotates the active one", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/auth/password",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      payload: { currentPassword: PASSWORD, newPassword: "a-new-password-1" },
    });
    assert.equal(response.statusCode, 200);

    // The old cookie is dead; the rotated cookie works.
    assert.equal(
      (await app.inject({ method: "GET", url: "/v1/me", headers: { cookie } })).statusCode,
      401,
    );
    const rotated = response.headers["set-cookie"];
    const rotatedCookie = (Array.isArray(rotated) ? rotated[0] : rotated) ?? "";
    assert.equal(
      (await app.inject({ method: "GET", url: "/v1/me", headers: { cookie: rotatedCookie } })).statusCode,
      200,
    );
  });
});

describe("provider administration", () => {
  it("creates a provider without ever returning or auditing the API key", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/admin/providers",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      payload: { name: "primary", baseUrl: "https://api.example.com/v1", apiKey: "sk-super-secret" },
    });
    assert.equal(response.statusCode, 201, response.body);
    const created = response.json() as Record<string, unknown>;
    assert.equal(created.secretConfigured, true);
    assert.ok(!response.body.includes("sk-super-secret"));
    assert.ok(!JSON.stringify(state.audits).includes("sk-super-secret"));

    const list = await app.inject({
      method: "GET",
      url: "/v1/admin/providers",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
    });
    assert.equal(list.statusCode, 200);
    assert.ok(!list.body.includes("sk-super-secret"));
    assert.ok(!list.body.includes("credential_ciphertext"));
  });

  it("rejects a non-https provider endpoint", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/admin/providers",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      payload: { name: "local", baseUrl: "http://127.0.0.1:11434/v1", apiKey: "sk-x" },
    });
    assert.equal(response.statusCode, 400);
  });

  it("reports a private destination as a sanitized test failure", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);
    const headers = { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string };

    const created = await app.inject({
      method: "POST",
      url: "/v1/admin/providers",
      headers,
      payload: { name: "metadata", baseUrl: "https://169.254.169.254/latest", apiKey: "sk-x" },
    });
    const providerId = (created.json() as { id: string }).id;

    const tested = await app.inject({
      method: "POST",
      url: `/v1/admin/providers/${providerId}/test`,
      headers,
    });
    assert.equal(tested.statusCode, 200, tested.body);
    const result = tested.json() as { ok: boolean; errorCode: string; latencyMs: number };
    assert.equal(result.ok, false);
    assert.equal(result.errorCode, "dns_rejected");
    assert.ok(result.latencyMs <= 8000);
    assert.ok(!tested.body.includes("sk-x"));
  });

  it("refuses to store a credential when the master key is missing", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin" })],
    });
    const app = buildApp({
      config: loadConfig({ NODE_ENV: "test", TRUSTED_WEB_ORIGINS: ORIGIN }),
      platformStore: state.store,
    });
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "POST",
      url: "/v1/admin/providers",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      payload: { name: "primary", baseUrl: "https://api.example.com/v1", apiKey: "sk-x" },
    });
    assert.equal(response.statusCode, 503);
    assert.equal(response.json().code, "CREDENTIAL_KEY_NOT_CONFIGURED");
  });

  it("exposes only enabled providers and models to regular users", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const admin = makeUser({ passwordHash, role: "admin" });
    const state = createFakeStore({ passwordHash, users: [admin] });
    const app = await createApp(state);
    const { cookie, body } = await login(app);
    const headers = { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string };

    const created = await app.inject({
      method: "POST",
      url: "/v1/admin/providers",
      headers,
      payload: { name: "primary", baseUrl: "https://api.example.com/v1", apiKey: "sk-x" },
    });
    const providerId = (created.json() as { id: string }).id;
    await app.inject({
      method: "POST",
      url: `/v1/admin/providers/${providerId}/models`,
      headers,
      payload: { modelId: "hy3", displayName: "Hy3" },
    });
    await app.inject({
      method: "PATCH",
      url: `/v1/admin/providers/${providerId}`,
      headers,
      payload: { enabled: false },
    });

    const catalog = await app.inject({ method: "GET", url: "/v1/providers", headers });
    assert.equal(catalog.statusCode, 200);
    assert.deepEqual(catalog.json(), { providers: [] });
  });
});

describe("audit trail", () => {
  it("records actor, action and resource for a failed login", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({ passwordHash, users: [makeUser({ passwordHash })] });
    const app = await createApp(state);
    await login(app, "alice", "wrong-password-1");
    assert.equal(state.audits.length, 1);
    assert.equal(state.audits[0]?.action, "auth.login");
    assert.equal(state.audits[0]?.succeeded, false);
  });

  it("hashes CSRF tokens before comparison", () => {
    assert.equal(hashCsrfToken("abc").length, 32);
  });
});

describe("deletion", () => {
  async function adminApp(extra: Partial<Parameters<typeof createFakeStore>[0]> = {}) {
    const passwordHash = await hashPassword(PASSWORD);
    const admin = makeUser({ passwordHash, role: "admin", username: "root" });
    const state = createFakeStore({
      passwordHash,
      users: [admin, ...(extra.users ?? [])],
      ...(extra.historyUserIds === undefined ? {} : { historyUserIds: extra.historyUserIds }),
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app, "root");
    return {
      state,
      admin,
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
      app,
    };
  }

  it("deletes an account and records who did it", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const victim = makeUser({ passwordHash, username: "bob" });
    const { app, headers, state } = await adminApp({ users: [victim] });

    const response = await app.inject({
      method: "DELETE",
      url: `/v1/admin/users/${victim.id}`,
      headers,
    });
    assert.equal(response.statusCode, 204, response.body);
    assert.equal(await state.store.getUser(victim.id), undefined);
    assert.ok(
      state.audits.some(
        (audit) => audit.action === "admin.user.delete" && audit.resourceId === victim.id,
      ),
    );
  });

  it("refuses to delete its own account", async () => {
    const { app, headers, admin, state } = await adminApp();
    const response = await app.inject({
      method: "DELETE",
      url: `/v1/admin/users/${admin.id}`,
      headers,
    });
    assert.equal(response.statusCode, 409);
    assert.equal(response.json().code, "CANNOT_DELETE_SELF");
    assert.ok((await state.store.getUser(admin.id)) !== undefined);
  });

  it("refuses to delete an account that a match row references", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const victim = makeUser({ passwordHash, username: "bob" });
    const { app, headers } = await adminApp({ users: [victim], historyUserIds: [victim.id] });

    const response = await app.inject({
      method: "DELETE",
      url: `/v1/admin/users/${victim.id}`,
      headers,
    });
    assert.equal(response.statusCode, 409);
    assert.equal(response.json().code, "USER_HAS_HISTORY");
  });

  it("deletes a model before its provider, and answers 404 for unknown ids", async () => {
    const { app, headers } = await adminApp();
    const created = await app.inject({
      method: "POST",
      url: "/v1/admin/providers",
      headers,
      payload: { name: "primary", baseUrl: "https://api.example.com/v1", apiKey: "sk-x" },
    });
    const providerId = (created.json() as { id: string }).id;
    const model = await app.inject({
      method: "POST",
      url: `/v1/admin/providers/${providerId}/models`,
      headers,
      payload: { modelId: "gpt-test", displayName: "Test Model" },
    });
    const modelId = (model.json() as { id: string }).id;

    // The provider owns a model, so the foreign key keeps it alive.
    const blocked = await app.inject({
      method: "DELETE",
      url: `/v1/admin/providers/${providerId}`,
      headers,
    });
    assert.equal(blocked.statusCode, 409);
    assert.equal(blocked.json().code, "PROVIDER_HAS_MODELS");

    const removedModel = await app.inject({
      method: "DELETE",
      url: `/v1/admin/models/${modelId}`,
      headers,
    });
    assert.equal(removedModel.statusCode, 204, removedModel.body);

    const removedProvider = await app.inject({
      method: "DELETE",
      url: `/v1/admin/providers/${providerId}`,
      headers,
    });
    assert.equal(removedProvider.statusCode, 204, removedProvider.body);

    const missing = await Promise.all([
      app.inject({ method: "DELETE", url: `/v1/admin/providers/${randomUUID()}`, headers }),
      app.inject({ method: "DELETE", url: `/v1/admin/models/${randomUUID()}`, headers }),
      app.inject({ method: "DELETE", url: `/v1/admin/users/${randomUUID()}`, headers }),
    ]);
    for (const response of missing) {
      assert.equal(response.statusCode, 404, response.body);
    }
  });
});
