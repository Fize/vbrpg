import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "./app.js";
import { createAccessToken } from "./auth.js";
import type { ApiConfig } from "./config.js";

const config: ApiConfig = {
  environment: "test",
  port: 3000,
  logLevel: "silent",
  authTokenSecret: "test-secret-that-is-long-enough",
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
});
