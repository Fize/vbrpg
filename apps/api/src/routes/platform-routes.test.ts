import assert from "node:assert/strict";
import { randomBytes, randomUUID } from "node:crypto";
import { describe, it } from "vitest";
import type { PlatformStore, ProviderView, SessionRecord } from "../store.js";
import type { ExternalCommand, GameEvent, GameState } from "@vbrpg/contracts";
import { EngineError } from "@vbrpg/workflow-engine";
import { buildApp } from "../app.js";
import { loadConfig } from "../config.js";
import { hashPassword } from "../password.js";
import { hashToken } from "../session.js";
import { hashCsrfToken } from "../csrf.js";
import { sealCredential } from "@vbrpg/runtime";
import type { PlatformUserRecord } from "@vbrpg/db";

const ORIGIN = "http://localhost:5173";
const MASTER_KEY = randomBytes(32).toString("base64");
const PASSWORD = "initial-password-1";

interface FakeState {
  store: PlatformStore;
  audits: Array<Record<string, unknown>>;
  sessions: Map<string, SessionRecord & { tokenHash: string }>;
}

interface FakeInstance {
  state: GameState;
  sequence: number;
  seenKeys: Set<string>;
}

function createFakeStore(options: {
  passwordHash: string;
  users: PlatformUserRecord[];
  gameVersions?: string[];
  appendError?: Error;
}): FakeState {
  const users = new Map(options.users.map((user) => [user.id, user]));
  const sessions = new Map<string, SessionRecord & { tokenHash: string }>();
  const providers = new Map<string, ProviderView>();
  const secrets = new Map<string, { baseUrl: string; enabled: boolean; sealed: ReturnType<typeof sealCredential> }>();
  const audits: Array<Record<string, unknown>> = [];
  const gameVersions = new Set(options.gameVersions ?? ["version-1"]);
  const instances = new Map<string, FakeInstance>();

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
        mustChangePassword: input.mustChangePassword,
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
        ...(patch.mustChangePassword === undefined ? {} : { mustChangePassword: patch.mustChangePassword }),
      };
      users.set(userId, updated);
      return updated;
    },
    countActiveAdmins: async () =>
      [...users.values()].filter((user) => user.role === "admin" && user.active).length,

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

    createInstance: async (input) => {
      if (!gameVersions.has(input.gameVersionId)) return undefined;
      const state: GameState = {
        instanceId: input.instanceId,
        gameVersionId: input.gameVersionId,
        engineVersion: "native-test",
        sequence: 0,
        status: "created",
        currentNodeId: "start",
        variables: input.variables ?? {},
        participants: input.participants,
        waiting: null,
        randomSeed: input.randomSeed,
      };
      instances.set(input.instanceId, { state, sequence: 0, seenKeys: new Set() });
      return state;
    },
    getInstanceState: async (instanceId) => {
      const entry = instances.get(instanceId);
      if (!entry) return undefined;
      return {
        instanceId,
        status: entry.state.status,
        currentSequence: entry.sequence,
        state: entry.state,
      };
    },
    appendEvent: async (instanceId, event: GameEvent) => {
      if (options.appendError) throw options.appendError;
      const entry = instances.get(instanceId);
      if (!entry) return undefined;
      if (entry.seenKeys.has(event.idempotencyKey)) {
        return { state: entry.state, commands: [] as ExternalCommand[], replayed: true };
      }
      entry.seenKeys.add(event.idempotencyKey);
      if (entry.state.status === "paused") {
        throw new EngineError("INSTANCE_PAUSED", "The instance is paused by an administrator");
      }
      if (entry.state.status === "completed" || entry.state.status === "cancelled") {
        throw new EngineError("UNEXPECTED_INPUT", "The instance is not waiting for player input");
      }
      entry.sequence = event.sequence;
      entry.state = {
        ...entry.state,
        sequence: event.sequence,
        status: event.type === "instanceCreated" ? "waiting" : "completed",
      };
      const commands: ExternalCommand[] =
        event.type === "instanceCreated"
          ? [{ commandId: "command-1", instanceId, type: "emit", eventName: "started", payload: {} }]
          : [];
      return { state: entry.state, commands, replayed: false };
    },

    projectInstanceView: async (instanceId, viewer) => {
      const entry = instances.get(instanceId);
      if (!entry) return undefined;
      const participant =
        viewer.kind === "participant"
          ? entry.state.participants.find((item) => item.participantId === viewer.participantId)
          : undefined;
      if (viewer.kind === "participant" && !participant) {
        throw new EngineError("UNKNOWN_PARTICIPANT", "Participant is not part of the instance");
      }
      return {
        instanceId,
        gameVersionId: entry.state.gameVersionId,
        sequence: entry.sequence,
        status: entry.state.status,
        publicState: { dayNumber: 2 },
        privateState: participant?.roleId === "werewolf" ? { wolfTeam: ["p1"] } : {},
        availableActions: [],
      };
    },

    pauseInstance: async (instanceId) => {
      const entry = instances.get(instanceId);
      if (!entry || entry.state.status === "completed" || entry.state.status === "cancelled") {
        return "rejected";
      }
      entry.state = { ...entry.state, status: "paused" };
      return "paused";
    },
    resumeInstance: async (instanceId) => {
      const entry = instances.get(instanceId);
      if (!entry || entry.state.status !== "paused") return "rejected";
      entry.state = { ...entry.state, status: entry.state.waiting === null ? "running" : "waiting" };
      return "resumed";
    },
    cancelInstance: async (instanceId) => {
      const entry = instances.get(instanceId);
      if (!entry || entry.state.status === "completed" || entry.state.status === "cancelled") {
        return "rejected";
      }
      entry.state = { ...entry.state, status: "cancelled" };
      return "cancelled";
    },
    forceInstanceTimeout: async (instanceId) => {
      const entry = instances.get(instanceId);
      if (!entry) return { outcome: "skipped", reason: "INSTANCE_NOT_FOUND" };
      const waiting = entry.state.waiting;
      if (!waiting) return { outcome: "skipped", reason: "INSTANCE_NOT_WAITING" };
      if (waiting.kind !== "timer" && waiting.kind !== "ai") {
        return { outcome: "skipped", reason: `NOT_TIMEOUTABLE: ${waiting.kind}` };
      }
      entry.sequence += 1;
      entry.state = { ...entry.state, sequence: entry.sequence, status: "completed" };
      return { outcome: "completed" };
    },
    describeInstance: async (instanceId) => {
      const entry = instances.get(instanceId);
      if (!entry) return undefined;
      return {
        instanceId,
        gameVersionId: entry.state.gameVersionId,
        engineVersion: entry.state.engineVersion,
        status: entry.state.status,
        currentSequence: entry.sequence,
        currentNodeId: entry.state.currentNodeId,
        waiting: entry.state.waiting === null
          ? null
          : {
            kind: entry.state.waiting.kind,
            nodeId: entry.state.waiting.nodeId,
            participantIds: entry.state.waiting.participantIds,
          },
        participants: {
          total: entry.state.participants.length,
          byRole: {},
          byStatus: {},
        },
        variableKeys: Object.keys(entry.state.variables).sort(),
        counts: { events: entry.seenKeys.size, pendingCommands: 0, scheduledJobs: 0 },
      };
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
    mustChangePassword: false,
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
        makeUser({ passwordHash, username: "initial", mustChangePassword: true }),
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
    ]);
    for (const response of responses) {
      assert.equal(response.statusCode, 403, response.body);
      assert.equal(response.json().code, "INSUFFICIENT_ROLE");
    }
  });

  it("blocks admin endpoints until the initial password is changed", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, role: "admin", mustChangePassword: true })],
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);

    const response = await app.inject({
      method: "GET",
      url: "/v1/admin/users",
      headers: { cookie, origin: ORIGIN, "x-csrf-token": body.csrfToken as string },
    });
    assert.equal(response.statusCode, 403);
    assert.equal(response.json().code, "PASSWORD_CHANGE_REQUIRED");
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
      users: [makeUser({ passwordHash, mustChangePassword: true })],
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

  it("clears the flag, revokes prior sessions and rotates the session", async () => {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [makeUser({ passwordHash, mustChangePassword: true })],
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
    assert.equal(response.json().user.mustChangePassword, false);

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

describe("game instances", () => {
  async function signedIn(
    options: { gameVersions?: string[]; appendError?: Error; role?: "admin" | "user" } = {},
  ) {
    const passwordHash = await hashPassword(PASSWORD);
    const user = makeUser({
      passwordHash,
      ...(options.role === undefined ? {} : { role: options.role }),
    });
    const state = createFakeStore({
      passwordHash,
      users: [user],
      ...(options.gameVersions === undefined ? {} : { gameVersions: options.gameVersions }),
      ...(options.appendError === undefined ? {} : { appendError: options.appendError }),
    });
    const app = await createApp(state);
    const { cookie, body } = await login(app);
    return { app, cookie, csrf: body.csrfToken ?? "", userId: user.id };
  }

  it("rejects unauthenticated and cross-origin instance writes", async () => {
    const { app, cookie, csrf } = await signedIn();

    const anonymous = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN },
      payload: { gameVersionId: "version-1" },
    });
    assert.equal(anonymous.statusCode, 401);

    const crossOrigin = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: "https://evil.example.com", cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-1" },
    });
    assert.equal(crossOrigin.statusCode, 403);
    assert.equal(crossOrigin.json().code, "ORIGIN_NOT_ALLOWED");
  });

  it("creates an instance, dispatches instanceCreated and returns the commands", async () => {
    const { app, cookie, csrf } = await signedIn();

    const response = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-1", randomSeed: "seed-1" },
    });

    assert.equal(response.statusCode, 201);
    const body = response.json() as { instanceId: string; state: GameState; commands: ExternalCommand[] };
    assert.equal(body.state.status, "waiting");
    assert.equal(body.state.sequence, 1);
    assert.equal(body.state.randomSeed, "seed-1");
    assert.equal(body.commands.length, 1);
    assert.equal(body.commands[0]?.type, "emit");
  });

  it("hides the authoritative state from ordinary accounts", async () => {
    // One store, two accounts: the read is rejected regardless of who created the instance.
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [
        makeUser({ passwordHash, username: "player-account" }),
        makeUser({ passwordHash, username: "admin-account", role: "admin" }),
      ],
    });
    const app = await createApp(state);
    const player = await login(app, "player-account");
    const admin = await login(app, "admin-account");

    const created = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie: player.cookie, "x-csrf-token": player.body.csrfToken ?? "" },
      payload: { gameVersionId: "version-1" },
    });
    const { instanceId } = created.json() as { instanceId: string };

    const asUser = await app.inject({
      method: "GET",
      url: `/v1/instances/${instanceId}`,
      headers: { cookie: player.cookie },
    });
    assert.equal(asUser.statusCode, 403);
    assert.equal(asUser.json().code, "INSUFFICIENT_ROLE");

    const asAdmin = await app.inject({
      method: "GET",
      url: `/v1/instances/${instanceId}`,
      headers: { cookie: admin.cookie },
    });
    assert.equal(asAdmin.statusCode, 200);
    assert.equal((asAdmin.json() as { currentSequence: number }).currentSequence, 1);
  });

  it("projects a view for the account that controls the seat only", async () => {
    const { app, cookie, csrf, userId } = await signedIn();
    const created = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: {
        gameVersionId: "version-1",
        participants: [
          { participantId: "p1", actorId: userId, roleId: "werewolf", control: "human", status: "active" },
          { participantId: "p2", actorId: "someone-else", roleId: "villager", control: "human", status: "active" },
        ],
      },
    });
    const { instanceId } = created.json() as { instanceId: string };

    const own = await app.inject({
      method: "GET",
      url: `/v1/instances/${instanceId}/view?participantId=p1`,
      headers: { cookie },
    });
    assert.equal(own.statusCode, 200);
    assert.deepEqual(own.json().publicState, { dayNumber: 2 });
    assert.deepEqual(own.json().privateState, { wolfTeam: ["p1"] });
    assert.ok(!JSON.stringify(own.json()).includes("actorId"));

    const other = await app.inject({
      method: "GET",
      url: `/v1/instances/${instanceId}/view?participantId=p2`,
      headers: { cookie },
    });
    assert.equal(other.statusCode, 403);
    assert.equal(other.json().code, "NOT_YOUR_PARTICIPANT");

    const unknown = await app.inject({
      method: "GET",
      url: `/v1/instances/${instanceId}/view?participantId=p9`,
      headers: { cookie },
    });
    assert.equal(unknown.statusCode, 404);
    assert.equal(unknown.json().code, "PARTICIPANT_NOT_FOUND");

    const missing = await app.inject({
      method: "GET",
      url: `/v1/instances/${instanceId}/view`,
      headers: { cookie },
    });
    assert.equal(missing.statusCode, 400);
    assert.equal(missing.json().code, "PARTICIPANT_REQUIRED");
  });

  it("reports an unknown game version and an unknown instance", async () => {
    const { app, cookie, csrf } = await signedIn();

    const missingVersion = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-unknown" },
    });
    assert.equal(missingVersion.statusCode, 404);
    assert.equal(missingVersion.json().code, "GAME_VERSION_NOT_FOUND");

    const admin = await signedIn({ role: "admin" });
    const missingInstance = await admin.app.inject({
      method: "GET",
      url: "/v1/instances/instance-unknown",
      headers: { cookie: admin.cookie },
    });
    assert.equal(missingInstance.statusCode, 404);
    assert.equal(missingInstance.json().code, "INSTANCE_NOT_FOUND");
  });

  it("replays an idempotency key instead of advancing the instance twice", async () => {
    const { app, cookie, csrf } = await signedIn();
    const created = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-1" },
    });
    const { instanceId } = created.json() as { instanceId: string };
    const headers = { origin: ORIGIN, cookie, "x-csrf-token": csrf, "idempotency-key": "retry-1" };

    const first = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers,
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });
    const second = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers,
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });

    assert.equal(first.statusCode, 200);
    assert.equal(first.json().replayed, false);
    assert.equal(second.statusCode, 200);
    assert.equal(second.json().replayed, true);
    assert.equal(second.json().state.sequence, 2);
  });

  it("refuses client-supplied server-side event types", async () => {
    const { app, cookie, csrf } = await signedIn();
    const created = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-1" },
    });
    const { instanceId } = created.json() as { instanceId: string };

    const response = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { type: "aiFailed", payload: {} },
    });

    assert.equal(response.statusCode, 400);
    assert.equal(response.json().code, "INVALID_REQUEST");
  });

  it("refuses events on a finished instance and maps engine rejections to conflicts", async () => {
    const { app, cookie, csrf } = await signedIn();
    const created = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-1" },
    });
    const { instanceId } = created.json() as { instanceId: string };
    const headers = { origin: ORIGIN, cookie, "x-csrf-token": csrf, "idempotency-key": "first-input" };

    const finishing = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers,
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });
    assert.equal(finishing.statusCode, 200);

    // A retry of an accepted event replays even after the instance finished.
    const retry = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers,
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });
    assert.equal(retry.statusCode, 200);
    assert.equal(retry.json().replayed, true);

    const afterFinish = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers: { ...headers, "idempotency-key": "second-input" },
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });
    assert.equal(afterFinish.statusCode, 409);
    assert.equal(afterFinish.json().code, "UNEXPECTED_INPUT");

    const rejected = await signedIn({ appendError: new EngineError("SEQUENCE_MISMATCH", "stale sequence") });
    const stale = await rejected.app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie: rejected.cookie, "x-csrf-token": rejected.csrf },
      payload: { gameVersionId: "version-1" },
    });
    assert.equal(stale.statusCode, 409);
    assert.equal(stale.json().code, "SEQUENCE_MISMATCH");
  });
});

describe("admin instance controls", () => {
  async function twoAccounts() {
    const passwordHash = await hashPassword(PASSWORD);
    const state = createFakeStore({
      passwordHash,
      users: [
        makeUser({ passwordHash, username: "player-account" }),
        makeUser({ passwordHash, username: "admin-account", role: "admin" }),
      ],
    });
    const app = await createApp(state);
    const player = await login(app, "player-account");
    const admin = await login(app, "admin-account");
    return { app, state, player, admin };
  }

  async function createdInstance(app: Awaited<ReturnType<typeof createApp>>, cookie: string, csrf: string) {
    const created = await app.inject({
      method: "POST",
      url: "/v1/instances",
      headers: { origin: ORIGIN, cookie, "x-csrf-token": csrf },
      payload: { gameVersionId: "version-1" },
    });
    return (created.json() as { instanceId: string }).instanceId;
  }

  it("restricts lifecycle controls to administrators", async () => {
    const { app, player } = await twoAccounts();
    const instanceId = await createdInstance(app, player.cookie, player.body.csrfToken ?? "");

    const asPlayer = await app.inject({
      method: "POST",
      url: `/v1/admin/instances/${instanceId}/pause`,
      headers: { origin: ORIGIN, cookie: player.cookie, "x-csrf-token": player.body.csrfToken ?? "" },
    });
    assert.equal(asPlayer.statusCode, 403);
    assert.equal(asPlayer.json().code, "INSUFFICIENT_ROLE");
  });

  it("pauses an instance, refuses its events, then resumes it", async () => {
    const { app, state, admin } = await twoAccounts();
    const instanceId = await createdInstance(app, admin.cookie, admin.body.csrfToken ?? "");
    const adminHeaders = { origin: ORIGIN, cookie: admin.cookie, "x-csrf-token": admin.body.csrfToken ?? "" };

    const paused = await app.inject({
      method: "POST",
      url: `/v1/admin/instances/${instanceId}/pause`,
      headers: adminHeaders,
    });
    assert.equal(paused.statusCode, 200);
    assert.equal(paused.json().status, "paused");

    const blocked = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers: adminHeaders,
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });
    assert.equal(blocked.statusCode, 409);
    assert.equal(blocked.json().code, "INSTANCE_PAUSED");

    const resumed = await app.inject({
      method: "POST",
      url: `/v1/admin/instances/${instanceId}/resume`,
      headers: adminHeaders,
    });
    assert.equal(resumed.statusCode, 200);
    assert.equal(resumed.json().status, "resumed");

    const accepted = await app.inject({
      method: "POST",
      url: `/v1/instances/${instanceId}/events`,
      headers: adminHeaders,
      payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
    });
    assert.equal(accepted.statusCode, 200);

    assert.deepEqual(
      state.audits
        .map((entry) => entry.action)
        .filter((action) => action.startsWith("instance.")),
      ["instance.pause", "instance.resume"],
    );
  });

  it("cancels an instance and refuses later lifecycle changes", async () => {
    const { app, admin } = await twoAccounts();
    const instanceId = await createdInstance(app, admin.cookie, admin.body.csrfToken ?? "");
    const headers = { origin: ORIGIN, cookie: admin.cookie, "x-csrf-token": admin.body.csrfToken ?? "" };

    const cancelled = await app.inject({
      method: "POST",
      url: `/v1/admin/instances/${instanceId}/cancel`,
      headers,
    });
    assert.equal(cancelled.statusCode, 200);
    assert.equal(cancelled.json().status, "cancelled");

    const again = await app.inject({
      method: "POST",
      url: `/v1/admin/instances/${instanceId}/cancel`,
      headers,
    });
    assert.equal(again.statusCode, 409);
    assert.equal(again.json().code, "INSTANCE_NOT_CANCELLABLE");
  });

  it("force-times-out only timeoutable waits and returns a redacted status", async () => {
    const { app, state, admin } = await twoAccounts();
    const instanceId = await createdInstance(app, admin.cookie, admin.body.csrfToken ?? "");
    const headers = { origin: ORIGIN, cookie: admin.cookie, "x-csrf-token": admin.body.csrfToken ?? "" };

    // The fake instance waits on player input, which has no timeout semantics yet.
    const refused = await app.inject({
      method: "POST",
      url: `/v1/admin/instances/${instanceId}/timeout`,
      headers,
    });
    assert.equal(refused.statusCode, 409);
    assert.equal(refused.json().code, "NOT_TIMEOUTABLE");
    assert.equal(state.audits.some((entry) => entry.action === "instance.force_timeout"), false);

    const badRequest = await app.inject({
      method: "POST",
      url: "/v1/admin/instances/instance-unknown/pause",
      headers,
    });
    assert.equal(badRequest.statusCode, 409);
    assert.equal(badRequest.json().code, "INSTANCE_NOT_PAUSABLE");

    const status = await app.inject({
      method: "GET",
      url: `/v1/admin/instances/${instanceId}`,
      headers: { cookie: admin.cookie },
    });
    assert.equal(status.statusCode, 200);
    const body = status.json() as Record<string, unknown>;
    assert.equal(body.instanceId, instanceId);
    assert.equal(typeof body.currentSequence, "number");
    assert.deepEqual(body.counts, { events: 1, pendingCommands: 0, scheduledJobs: 0 });
    // Structure only: no variable values, no participant identities.
    assert.ok(Array.isArray(body.variableKeys));
    assert.ok(!JSON.stringify(body).includes("actorId"));

    const missing = await app.inject({
      method: "GET",
      url: "/v1/admin/instances/instance-unknown",
      headers: { cookie: admin.cookie },
    });
    assert.equal(missing.statusCode, 404);
  });
});
