import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, setCsrfToken, type User } from "./api";

const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();
vi.stubGlobal("fetch", fetchMock);

const user: User = {
  id: "11111111-1111-1111-1111-111111111111",
  username: "alice",
  role: "user",
  active: true,
  mustChangePassword: false,
  createdAt: "2026-01-01T00:00:00.000Z",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function callAt(index: number): [RequestInfo | URL, RequestInit | undefined] {
  const call = fetchMock.mock.calls[index];
  if (!call) throw new Error(`Expected a fetch call at index ${index}`);
  return [call[0], call[1]];
}

function headerOf(init: RequestInit | undefined, name: string): string | undefined {
  const headers = init?.headers;
  if (!headers || headers instanceof Headers || Array.isArray(headers)) return undefined;
  return headers[name];
}

beforeEach(() => {
  fetchMock.mockReset();
  setCsrfToken(null);
});

describe("api client", () => {
  it("sends session credentials with every request", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, user));

    await api.loadCurrentUser();

    const [url, init] = callAt(0);
    expect(url).toBe("/v1/me");
    expect(init?.credentials).toBe("include");
  });

  it("maps the platform error envelope to a typed ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, {
        error: "Invalid username or password",
        code: "INVALID_CREDENTIALS",
        details: {},
        requestId: "req-401",
      }),
    );

    let caught: unknown;
    try {
      await api.login("bob", "wrong-password");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    if (!(caught instanceof ApiError)) throw new Error("Expected an ApiError");
    expect(caught.status).toBe(401);
    expect(caught.code).toBe("INVALID_CREDENTIALS");
    expect(caught.requestId).toBe("req-401");
    expect(caught.message).toBe("Invalid username or password");
  });

  it("attaches the CSRF token to writes but not to reads", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, { user, csrfToken: "login-token", expiresAt: "2026-01-01T12:00:00.000Z" }),
    );

    await api.login("alice", "supersecretpassword");

    fetchMock.mockResolvedValueOnce(jsonResponse(200, { users: [user] }));
    await api.listUsers();

    // Browsers omit Origin on same-origin GET, so reads must stay CSRF-free.
    const [, readInit] = callAt(1);
    expect(headerOf(readInit, "X-CSRF-Token")).toBeUndefined();

    fetchMock.mockResolvedValueOnce(jsonResponse(201, user));
    await api.createUser({ username: "bob", temporaryPassword: "temporary-pw-1", role: "user" });

    const [, writeInit] = callAt(2);
    expect(headerOf(writeInit, "X-CSRF-Token")).toBe("login-token");
  });

  it("refetches the CSRF token once and retries the rejected request", async () => {
    setCsrfToken("stale-token");
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse(403, {
          error: "The CSRF token is missing or invalid",
          code: "CSRF_TOKEN_INVALID",
          details: {},
          requestId: "req-csrf",
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { csrfToken: "fresh-token" }))
      .mockResolvedValueOnce(jsonResponse(201, user));

    const created = await api.createUser({
      username: "alice",
      temporaryPassword: "twelvechars1",
      role: "user",
    });

    expect(created).toEqual(user);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(callAt(1)[0]).toBe("/v1/auth/csrf");
    expect(headerOf(callAt(0)[1], "X-CSRF-Token")).toBe("stale-token");
    expect(headerOf(callAt(2)[1], "X-CSRF-Token")).toBe("fresh-token");
  });

  it("does not retry a 403 that is not a CSRF rotation", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(403, {
        error: "The authenticated account lacks the required role",
        code: "INSUFFICIENT_ROLE",
        details: {},
        requestId: "req-role",
      }),
    );

    await expect(api.listUsers()).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
