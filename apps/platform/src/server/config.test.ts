import { describe, expect, it } from "vitest";
import { loadConfig } from "./config.js";

describe("api config", () => {
  it("reads the database url and derives development origins", () => {
    const config = loadConfig({
      NODE_ENV: "test",
      DATABASE_URL: "postgres://localhost:5432/vbrpg",
      AUTH_TOKEN_SECRET: "test-secret-that-is-long-enough",
    });

    expect(config.databaseUrl).toBe("postgres://localhost:5432/vbrpg");
    expect(config.trustedOrigins.length).toBeGreaterThan(0);
    expect(config.sessionCookieSecure).toBe(false);
  });

  it("requires the master key and https origins in production", () => {
    expect(() => loadConfig({ NODE_ENV: "production" })).toThrow(/PLATFORM_CREDENTIAL_KEY/);
    expect(() =>
      loadConfig({
        NODE_ENV: "production",
        PLATFORM_CREDENTIAL_KEY: "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
      }),
    ).toThrow(/TRUSTED_WEB_ORIGINS/);
  });
});
