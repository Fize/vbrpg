import { describe, expect, it } from "vitest";
import {
  authenticate,
  authenticateWithSession,
  createAccessToken,
  requireRole,
  verifyAccessToken,
} from "./auth.js";

const secret = "test-secret-that-is-long-enough";
const principal = {
  userId: "user-1",
  tenantId: "tenant-a",
  roles: ["developer"] as const,
  sessionId: "session-1",
};

describe("access token boundary", () => {
  it("round-trips a signed tenant principal", () => {
    const token = createAccessToken(principal, secret, { now: 1_000, ttlSeconds: 60 });
    expect(verifyAccessToken(token, secret, 1_010)).toMatchObject({
      userId: "user-1",
      tenantId: "tenant-a",
      roles: ["developer"],
      sessionId: "session-1",
      issuedAt: 1_000,
      expiresAt: 1_060,
    });
  });

  it("rejects tampering and expiry", () => {
    const token = createAccessToken(principal, secret, { now: 1_000, ttlSeconds: 60 });
    expect(() => verifyAccessToken(`${token}x`, secret, 1_010)).toThrow();
    expect(() => verifyAccessToken(token, secret, 1_060)).toThrow();
  });

  it("requires the authenticated tenant header to match the token", () => {
    const now = Math.floor(Date.now() / 1000);
    const token = createAccessToken(principal, secret, { now, ttlSeconds: 60 });
    expect(() => authenticate(`Bearer ${token}`, "tenant-b", secret)).toThrowError(
      expect.objectContaining({ code: "TENANT_CONTEXT_MISMATCH", statusCode: 403 }),
    );
    expect(authenticate(`Bearer ${token}`, "tenant-a", secret).tenantId).toBe("tenant-a");
  });

  it("enforces tenant roles", () => {
    const now = Math.floor(Date.now() / 1000);
    const user = authenticate(
      `Bearer ${createAccessToken(principal, secret, { now, ttlSeconds: 60 })}`,
      "tenant-a",
      secret,
    );
    expect(() => requireRole(user, ["owner", "admin"])).toThrowError(
      expect.objectContaining({ code: "INSUFFICIENT_ROLE", statusCode: 403 }),
    );
    expect(requireRole(user, ["developer"])).toBe(user);
  });

  it("uses the database session role instead of trusting token roles", async () => {
    const now = Math.floor(Date.now() / 1000);
    const token = createAccessToken(
      { ...principal, roles: ["owner"] },
      secret,
      { now, ttlSeconds: 60 },
    );
    const resolved = await authenticateWithSession(
      `Bearer ${token}`,
      "tenant-a",
      secret,
      async (sessionId, tenantId) => ({
        userId: "user-1",
        tenantId,
        role: "player",
        expiresAt: new Date((now + 60) * 1000),
        revokedAt: null,
      }),
      new Date(now * 1000),
    );
    expect(resolved.roles).toEqual(["player"]);
  });
});
