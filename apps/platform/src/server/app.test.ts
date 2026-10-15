import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "./app.js";
import type { ApiConfig } from "./config.js";

const config: ApiConfig = {
  environment: "test",
  port: 3000,
  logLevel: "silent",
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

  it("does not serve the retired tenant routes", async () => {
    const app = buildApp({ config });
    apps.push(app);
    const response = await app.inject({ method: "GET", url: "/v1/tenant/me" });

    expect(response.statusCode).toBe(404);
    expect(response.json()).toMatchObject({ code: "ROUTE_NOT_FOUND" });
  });

  it("refuses to serve production traffic without a database-backed store", () => {
    expect(() => buildApp({ config: { ...config, environment: "production" } })).toThrow(
      /platform store/,
    );
  });
});
