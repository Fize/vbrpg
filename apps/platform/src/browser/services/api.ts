const API_BASE = "/v1";

// Shared with the API, the worker and the database layer: the frontend must not carry a second
// copy of these shapes. Web-side aliases keep the call sites readable.
import type {
  ConnectionTestResult,
  CreateMatchRequest as CreateMatchInput,
  CreateProviderModelRequest as CreateProviderModelInput,
  CreateUserRequest as CreateUserInput,
  GameCatalogueEntry,
  LoginResult,
  MatchDetail,
  MatchSummary,
  PlatformUser as User,
  PlayerView,
  Provider,
  ProviderInput as CreateProviderInput,
  ProviderModel,
  SubmitEventRequest,
  UpdateMatchStatusRequest,
  UpdateProviderModelRequest as UpdateProviderModelInput,
  UpdateProviderRequest as UpdateProviderInput,
  UpdateUserRequest as UpdateUserInput,
} from "../../shared/index.js";

export type {
  ActionArg,
  ConnectionTestResult,
  CreateMatchRequest as CreateMatchInput,
  GameAction,
  GameCatalogueEntry,
  LoginResult,
  MatchDetail,
  MatchRecordRow,
  MatchSeat,
  MatchSummary,
  PlatformRole as Role,
  PlatformUser as User,
  PlayerView,
  Provider,
  ProviderErrorCode,
  ProviderModel,
  CreateProviderModelRequest as CreateProviderModelInput,
  CreateUserRequest as CreateUserInput,
  ProviderInput as CreateProviderInput,
  UpdateProviderModelRequest as UpdateProviderModelInput,
  UpdateProviderRequest as UpdateProviderInput,
  UpdateUserRequest as UpdateUserInput,
} from "../../shared/index.js";

/** The write path's answer: what the match looks like now, from this seat's point of view. */
export interface SubmitMatchResult {
  replayed: boolean;
  summary: MatchSummary;
  view: PlayerView;
}

/** Typed failure carrying the platform error envelope. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown>,
    requestId: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

let onUnauthorized: (() => void) | null = null;

/** Registered once by the router so an expired session anywhere returns to the login page. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

function handleUnauthorized(response: Response, config: RequestConfig): void {
  // A rejected login is not an expired session: the user is already on the login page.
  if (response.status !== 401 || config.skipAuthRedirect === true) return;
  setCsrfToken(null);
  onUnauthorized?.();
}

export function apiErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Unexpected error. Please try again.";
}

export function apiRequestId(error: unknown): string | null {
  return error instanceof ApiError && error.requestId.length > 0 ? error.requestId : null;
}

// The CSRF synchronizer token lives in memory only; it must never be persisted.
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

interface RequestConfig {
  method: HttpMethod;
  path: string;
  body?: unknown;
  csrf?: boolean;
  /** Sent as `Idempotency-Key`: a retried submission must not land twice. */
  idempotencyKey?: string;
  /** Set on the login call: its 401 means wrong credentials, not an expired session. */
  skipAuthRedirect?: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

function toApiError(status: number, body: unknown): ApiError {
  let code = "UNKNOWN_ERROR";
  let message = `Request failed with status ${status}`;
  let details: Record<string, unknown> = {};
  let requestId = "";
  if (isRecord(body)) {
    if (typeof body.code === "string") code = body.code;
    if (typeof body.error === "string") message = body.error;
    if (isRecord(body.details)) details = body.details;
    if (typeof body.requestId === "string") requestId = body.requestId;
  }
  return new ApiError(status, code, message, details, requestId);
}

async function send(config: RequestConfig): Promise<Response> {
  const headers: Record<string, string> = {};
  if (config.body !== undefined) headers["Content-Type"] = "application/json";
  if (config.csrf === true && csrfToken !== null) headers["X-CSRF-Token"] = csrfToken;
  if (config.idempotencyKey !== undefined) headers["Idempotency-Key"] = config.idempotencyKey;
  const init: RequestInit = {
    method: config.method,
    credentials: "include",
    headers,
  };
  if (config.body !== undefined) init.body = JSON.stringify(config.body);
  return fetch(`${API_BASE}${config.path}`, init);
}

async function unwrap<T>(response: Response, config: RequestConfig): Promise<T> {
  if (response.status === 204) return undefined as unknown as T;
  const body = await readJson(response);
  if (!response.ok) {
    handleUnauthorized(response, config);
    throw toApiError(response.status, body);
  }
  return body as T;
}

async function execute<T>(config: RequestConfig): Promise<T> {
  let response = await send(config);
  // A rotated session invalidates the token; refetch once and replay the request.
  if (config.csrf === true && response.status === 403) {
    const body = await readJson(response);
    if (isRecord(body) && body.code === "CSRF_TOKEN_INVALID") {
      await refreshCsrfToken();
      response = await send(config);
    } else {
      throw toApiError(response.status, body);
    }
  }
  return unwrap<T>(response, config);
}

export async function refreshCsrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/csrf`, {
    method: "GET",
    credentials: "include",
  });
  const body = await readJson(response);
  if (!response.ok) throw toApiError(response.status, body);
  const token = isRecord(body) && typeof body.csrfToken === "string" ? body.csrfToken : "";
  if (token.length === 0) {
    throw new ApiError(response.status, "CSRF_TOKEN_MISSING", "No CSRF token was returned", {}, "");
  }
  csrfToken = token;
  return token;
}

export const api = {
  async login(username: string, password: string): Promise<LoginResult> {
    const result = await execute<LoginResult>({
      method: "POST",
      path: "/auth/login",
      body: { username, password },
      skipAuthRedirect: true,
    });
    csrfToken = result.csrfToken;
    return result;
  },

  async logout(): Promise<void> {
    await execute<void>({ method: "POST", path: "/auth/logout", csrf: true });
    csrfToken = null;
  },

  loadCurrentUser(): Promise<User> {
    return execute<User>({ method: "GET", path: "/me" });
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<LoginResult> {
    const result = await execute<LoginResult>({
      method: "POST",
      path: "/auth/password",
      body: { currentPassword, newPassword },
      csrf: true,
    });
    csrfToken = result.csrfToken;
    return result;
  },

  async listGames(): Promise<GameCatalogueEntry[]> {
    const result = await execute<{ games: GameCatalogueEntry[] }>({ method: "GET", path: "/games" });
    return result.games;
  },

  async listMatches(): Promise<MatchSummary[]> {
    const result = await execute<{ matches: MatchSummary[] }>({
      method: "GET",
      path: "/instances",
    });
    return result.matches;
  },

  createMatch(input: CreateMatchInput): Promise<MatchSummary> {
    return execute<MatchSummary>({ method: "POST", path: "/instances", body: input, csrf: true });
  },

  readMatch(instanceId: string): Promise<MatchDetail> {
    return execute<MatchDetail>({
      method: "GET",
      path: `/instances/${encodeURIComponent(instanceId)}`,
    });
  },

  submitMatchEvent(
    instanceId: string,
    input: SubmitEventRequest,
    idempotencyKey: string,
  ): Promise<SubmitMatchResult> {
    return execute<SubmitMatchResult>({
      method: "POST",
      path: `/instances/${encodeURIComponent(instanceId)}/events`,
      body: input,
      csrf: true,
      idempotencyKey,
    });
  },

  setMatchStatus(
    instanceId: string,
    status: UpdateMatchStatusRequest["status"],
  ): Promise<MatchSummary> {
    return execute<MatchSummary>({
      method: "PATCH",
      path: `/instances/${encodeURIComponent(instanceId)}/status`,
      body: { status },
      csrf: true,
    });
  },

  async listUsers(): Promise<User[]> {
    const result = await execute<{ users: User[] }>({
      method: "GET",
      path: "/admin/users",
    });
    return result.users;
  },

  createUser(input: CreateUserInput): Promise<User> {
    return execute<User>({ method: "POST", path: "/admin/users", body: input, csrf: true });
  },

  updateUser(userId: string, patch: UpdateUserInput): Promise<User> {
    return execute<User>({
      method: "PATCH",
      path: `/admin/users/${encodeURIComponent(userId)}`,
      body: patch,
      csrf: true,
    });
  },

  async deleteUser(userId: string): Promise<void> {
    await execute<void>({
      method: "DELETE",
      path: `/admin/users/${encodeURIComponent(userId)}`,
      csrf: true,
    });
  },

  async deleteProvider(providerId: string): Promise<void> {
    await execute<void>({
      method: "DELETE",
      path: `/admin/providers/${encodeURIComponent(providerId)}`,
      csrf: true,
    });
  },

  async deleteProviderModel(modelRecordId: string): Promise<void> {
    await execute<void>({
      method: "DELETE",
      path: `/admin/models/${encodeURIComponent(modelRecordId)}`,
      csrf: true,
    });
  },

  async listEnabledProviders(): Promise<Provider[]> {
    const result = await execute<{ providers: Provider[] }>({ method: "GET", path: "/providers" });
    return result.providers;
  },

  async listProviders(): Promise<Provider[]> {
    const result = await execute<{ providers: Provider[] }>({
      method: "GET",
      path: "/admin/providers",
    });
    return result.providers;
  },

  createProvider(input: CreateProviderInput): Promise<Provider> {
    return execute<Provider>({ method: "POST", path: "/admin/providers", body: input, csrf: true });
  },

  updateProvider(providerId: string, patch: UpdateProviderInput): Promise<Provider> {
    return execute<Provider>({
      method: "PATCH",
      path: `/admin/providers/${encodeURIComponent(providerId)}`,
      body: patch,
      csrf: true,
    });
  },

  testProvider(providerId: string): Promise<ConnectionTestResult> {
    return execute<ConnectionTestResult>({
      method: "POST",
      path: `/admin/providers/${encodeURIComponent(providerId)}/test`,
      csrf: true,
    });
  },

  createProviderModel(providerId: string, input: CreateProviderModelInput): Promise<ProviderModel> {
    return execute<ProviderModel>({
      method: "POST",
      path: `/admin/providers/${encodeURIComponent(providerId)}/models`,
      body: input,
      csrf: true,
    });
  },

  updateProviderModel(modelId: string, patch: UpdateProviderModelInput): Promise<ProviderModel> {
    return execute<ProviderModel>({
      method: "PATCH",
      path: `/admin/models/${encodeURIComponent(modelId)}`,
      body: patch,
      csrf: true,
    });
  },
};
