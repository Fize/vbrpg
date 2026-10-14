import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "./app.js";
import { createAccessToken } from "./auth.js";
import type { ApiConfig } from "./config.js";

const config: ApiConfig = {
  environment: "test",
  port: 3000,
  logLevel: "silent",
  authTokenSecret: "test-secret-that-is-long-enough",
  aiApiBaseUrl: "https://api.example.test/v1",
  aiModel: "test-model",
  aiTimeoutMs: 1000,
  aiContextWindowTokens: 1000,
  aiMaxInputTokens: 768,
  aiReserveOutputTokens: 128,
};

const mvpDefinition = {
  manifest: {
    gameId: "mvp-game",
    slug: "mvp-game",
    version: "1.0.0",
    dslVersion: "v1",
    engineVersion: "native-test",
    authorId: "user-1",
    license: "MIT",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["end"] },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [],
  variables: {},
  visibility: {},
  presentation: {},
};

describe("API foundation", () => {
  const apps: Array<Awaited<ReturnType<typeof buildApp>>> = [];

  afterEach(async () => {
    await Promise.all(apps.splice(0).map((app) => app.close()));
  });

  it("exposes health with a request id", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const response = await app.inject({ method: "GET", url: "/health" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({ status: "ok", service: "api" });
    expect(response.headers["x-request-id"]).toBeTruthy();
  });

  it("does not claim readiness without database configuration", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const response = await app.inject({ method: "GET", url: "/ready" });

    expect(response.statusCode).toBe(503);
    expect(response.json()).toMatchObject({
      status: "not_ready",
      checks: { database: "not_configured" },
    });
  });

  it("uses the shared error shape for unknown routes", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const response = await app.inject({ method: "GET", url: "/missing" });

    expect(response.statusCode).toBe(404);
    expect(response.json()).toMatchObject({
      code: "ROUTE_NOT_FOUND",
      details: { method: "GET", url: "/missing" },
    });
  });

  it("rejects unauthenticated requests to protected routes", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const response = await app.inject({ method: "GET", url: "/v1/tenant/me" });

    expect(response.statusCode).toBe(401);
    expect(response.json()).toMatchObject({ code: "AUTH_REQUIRED" });
  });

  it("rejects a cross-tenant header even with a valid token", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const token = createAccessToken(
      { userId: "user-1", tenantId: "tenant-a", roles: ["admin"], sessionId: "session-1" },
      config.authTokenSecret!,
      { now: Math.floor(Date.now() / 1000) },
    );
    const response = await app.inject({
      method: "GET",
      url: "/v1/tenant/me",
      headers: { authorization: `Bearer ${token}`, "x-tenant-id": "tenant-b" },
    });

    expect(response.statusCode).toBe(403);
    expect(response.json()).toMatchObject({ code: "TENANT_CONTEXT_MISMATCH" });
  });

  it("enforces owner/admin access on management routes", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const playerToken = createAccessToken(
      { userId: "user-1", tenantId: "tenant-a", roles: ["player"], sessionId: "session-1" },
      config.authTokenSecret!,
    );
    const denied = await app.inject({
      method: "GET",
      url: "/v1/tenant/management-check",
      headers: { authorization: `Bearer ${playerToken}`, "x-tenant-id": "tenant-a" },
    });
    expect(denied.statusCode).toBe(403);

    const adminToken = createAccessToken(
      { userId: "user-2", tenantId: "tenant-a", roles: ["admin"], sessionId: "session-2" },
      config.authTokenSecret!,
    );
    const allowed = await app.inject({
      method: "GET",
      url: "/v1/tenant/management-check",
      headers: { authorization: `Bearer ${adminToken}`, "x-tenant-id": "tenant-a" },
    });
    expect(allowed.statusCode).toBe(200);
    expect(allowed.json()).toEqual({ status: "authorized", tenantId: "tenant-a" });
  });

  it("does not allow production token-only authentication", async () => {
    const app = buildApp({
      config: { ...config, environment: "production" },
    });
    apps.push(app);
    const token = createAccessToken(
      { userId: "user-1", tenantId: "tenant-a", roles: ["admin"], sessionId: "session-1" },
      config.authTokenSecret!,
    );
    const response = await app.inject({
      method: "GET",
      url: "/v1/tenant/me",
      headers: { authorization: `Bearer ${token}`, "x-tenant-id": "tenant-a" },
    });

    expect(response.statusCode).toBe(503);
    expect(response.json()).toMatchObject({ code: "AUTH_SESSION_STORE_NOT_CONFIGURED" });
  });

  it("exposes the minimal compile and dispatch loop", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const compileResponse = await app.inject({
      method: "POST",
      url: "/v1/mvp/runtime/compile",
      payload: { definition: mvpDefinition },
    });
    expect(compileResponse.statusCode).toBe(200);
    expect(compileResponse.json()).toMatchObject({ entryNodeId: "start", nodeCount: 2 });

    const instanceResponse = await app.inject({
      method: "POST",
      url: "/v1/mvp/runtime/instances",
      payload: {
        definition: mvpDefinition,
        instanceId: "mvp-instance",
        gameVersionId: "mvp-version",
        randomSeed: "seed",
        participants: [],
      },
    });
    expect(instanceResponse.statusCode).toBe(200);
    expect(instanceResponse.json()).toMatchObject({ state: { status: "created", sequence: 0, currentNodeId: "start" } });

    const dispatchResponse = await app.inject({
      method: "POST",
      url: "/v1/mvp/runtime/dispatch",
      payload: {
        definition: mvpDefinition,
        state: {
          instanceId: "mvp-instance",
          gameVersionId: "mvp-version",
          engineVersion: "native-test",
          sequence: 0,
          status: "created",
          currentNodeId: "start",
          variables: {},
          participants: [],
          waiting: null,
          randomSeed: "seed",
        },
        event: {
          eventId: "mvp-event",
          instanceId: "mvp-instance",
          sequence: 1,
          type: "instanceCreated",
          actor: null,
          occurredAtMs: 0,
          idempotencyKey: "mvp-create",
          payload: {},
        },
      },
    });
    expect(dispatchResponse.statusCode).toBe(200);
    expect(dispatchResponse.json()).toMatchObject({ state: { status: "completed", sequence: 1 }, commands: [] });
  });

  it("rejects an invalid MVP definition", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const response = await app.inject({
      method: "POST",
      url: "/v1/mvp/runtime/compile",
      payload: { definition: { ...mvpDefinition, manifest: { ...mvpDefinition.manifest, dslVersion: "v0" } } },
    });
    expect(response.statusCode).toBe(400);
    expect(response.json()).toMatchObject({ code: "INVALID_GAME_DEFINITION" });
  });

  it("runs one AI step with only the current game context", async () => {
    const aiDefinition = {
      ...mvpDefinition,
      workflow: {
        entryNodeId: "start",
        nodes: [
          { id: "start", type: "start", config: {}, next: ["ai"] },
          {
            id: "ai",
            type: "aiGenerate",
            config: {
              input: { action: "choose" },
              timeoutMs: 1000,
              maxAttempts: 1,
              fallbackNodeId: "end",
              resultKey: "choice",
            },
            next: ["end"],
          },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      },
    };
    const app = buildApp({
      config,
      aiClient: {
        async generate(request) {
          expect(request.state.currentNodeId).toBe("ai");
          expect(request.recentEvents).toHaveLength(1);
          return { choice: "A" };
        },
      },
    });
    apps.push(app);
    const response = await app.inject({
      method: "POST",
      url: "/v1/mvp/runtime/ai-dispatch",
      payload: {
        definition: aiDefinition,
        state: {
          instanceId: "ai-instance",
          gameVersionId: "ai-version",
          engineVersion: "native-test",
          sequence: 0,
          status: "created",
          currentNodeId: "start",
          variables: {},
          participants: [],
          waiting: null,
          randomSeed: "seed",
        },
        event: {
          eventId: "ai-event",
          instanceId: "ai-instance",
          sequence: 1,
          type: "instanceCreated",
          actor: null,
          occurredAtMs: 0,
          idempotencyKey: "ai-create",
          payload: {},
        },
        recentEvents: [{
          eventId: "ai-event",
          instanceId: "ai-instance",
          sequence: 1,
          type: "instanceCreated",
          actor: null,
          occurredAtMs: 0,
          idempotencyKey: "ai-create",
          payload: {},
        }, {
          eventId: "other-game-event",
          instanceId: "other-game",
          sequence: 1,
          type: "instanceCreated",
          actor: null,
          occurredAtMs: 0,
          idempotencyKey: "other-game-create",
          payload: {},
        }],
      },
    });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({ aiResult: { choice: "A" }, state: { status: "completed", sequence: 2 } });
  });
});
