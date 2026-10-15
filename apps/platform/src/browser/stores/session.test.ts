import { beforeEach, describe, expect, it, vi } from "vitest";
import { login, loadCurrentUser, sessionState } from "./session";
import type { User } from "../services/api";

const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();
vi.stubGlobal("fetch", fetchMock);

const user: User = {
  id: "22222222-2222-2222-2222-222222222222",
  username: "root",
  role: "admin",
  active: true,
  createdAt: "2026-01-01T00:00:00.000Z",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  sessionState.user = null;
  sessionState.loading = false;
  sessionState.initialized = false;
});

describe("session store", () => {
  it("login stores the returned user", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, { user, csrfToken: "csrf-token", expiresAt: "2026-01-01T12:00:00.000Z" }),
    );

    const result = await login("root", "supersecretpassword");

    expect(result).toEqual(user);
    expect(sessionState.user).toEqual(user);
    expect(sessionState.initialized).toBe(true);
  });

  it("a 401 from loadCurrentUser clears the session", async () => {
    sessionState.user = user;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, {
        error: "Authentication session is invalid or expired",
        code: "SESSION_INVALID",
        details: {},
        requestId: "req-session",
      }),
    );

    const result = await loadCurrentUser();

    expect(result).toBeNull();
    expect(sessionState.user).toBeNull();
  });
});
