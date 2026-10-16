import type { FastifyRequest, preHandlerHookHandler } from "fastify";
import type { PlatformRole } from "../shared/index.js";
import type { ApiConfig } from "./config.js";
import { AppError } from "./runtime/index.js";
import { assertTrustedOrigin, csrfTokenMatches } from "./csrf.js";
import { createRateLimiter, type ConcurrencyLimiter, type RateLimiter } from "./rate-limit.js";
import {
  LAST_SEEN_THROTTLE_MS,
  SESSION_ABSOLUTE_MS,
  SESSION_IDLE_MS,
  hashToken,
  idleExpiry,
  readSessionCookie,
  sessionInvalid,
} from "./session.js";
import type { PlatformStore } from "./store.js";

export interface PlatformPrincipal {
  userId: string;
  username: string;
  role: PlatformRole;
  sessionId: string;
  csrfTokenHash: Buffer | null;
  expiresAt: Date;
}

declare module "fastify" {
  interface FastifyRequest {
    platformPrincipal?: PlatformPrincipal;
  }
}

export interface PlatformRequestContext {
  store: PlatformStore;
  config: ApiConfig;
  limiters: PlatformLimiters;
}

export interface PlatformLimiters {
  loginByIp: RateLimiter;
  loginByAccount: RateLimiter;
  connectionTestByAdmin: RateLimiter;
  connectionTestSlots: Map<string, ConcurrencyLimiter>;
  /** Each word pair is a paid model call, so it is capped per account. */
  wordPairByUser: RateLimiter;
}

/** Limiters are per-app-instance state, created once alongside the store. */
export function createPlatformRequestContext(
  store: PlatformStore,
  config: ApiConfig,
): PlatformRequestContext {
  return {
    store,
    config,
    limiters: {
      loginByIp: createRateLimiter({ limit: 10, windowMs: 60_000 }),
      loginByAccount: createRateLimiter({ limit: 5, windowMs: 60_000 }),
      connectionTestByAdmin: createRateLimiter({ limit: 5, windowMs: 60_000 }),
      connectionTestSlots: new Map(),
      // Each word pair is a paid model call, so the cap is per account, not per match.
      wordPairByUser: createRateLimiter({ limit: 10, windowMs: 60_000 }),
    },
  };
}

export async function resolvePrincipal(
  request: FastifyRequest,
  context: PlatformRequestContext,
): Promise<PlatformPrincipal> {
  const token = readSessionCookie(request.headers.cookie);
  if (!token) throw sessionInvalid();

  const session = await context.store.findSessionByTokenHash(hashToken(token));
  if (!session) throw sessionInvalid();

  const user = await context.store.getUser(session.userId);
  if (!user || !user.active) throw sessionInvalid();

  const now = new Date();
  // Refresh lazily: a write on every request would make reads expensive.
  if (session.idleExpiresAt.getTime() - now.getTime() < SESSION_IDLE_MS - LAST_SEEN_THROTTLE_MS) {
    await context.store.touchSession(session.id, idleExpiry(now, session.absoluteExpiresAt));
  }

  return {
    userId: user.id,
    username: user.username,
    role: user.role,
    sessionId: session.id,
    csrfTokenHash: session.csrfTokenHash,
    expiresAt: session.absoluteExpiresAt,
  };
}

/** Every protected route re-checks the DB role; a client claim is never trusted. */
export function requirePlatformRole(
  principal: PlatformPrincipal,
  allowed: readonly PlatformRole[],
): void {
  if (!allowed.includes(principal.role)) {
    throw new AppError(
      403,
      "INSUFFICIENT_ROLE",
      "The authenticated account lacks the required role",
    );
  }
}

export function authenticatePlatform(context: PlatformRequestContext): preHandlerHookHandler {
  return async (request) => {
    request.platformPrincipal = await resolvePrincipal(request, context);
  };
}

export function authenticatePlatformWithCsrf(
  context: PlatformRequestContext,
): preHandlerHookHandler {
  return async (request) => {
    const principal = await resolvePrincipal(request, context);
    assertCsrf(request, principal, context.config);
    request.platformPrincipal = principal;
  };
}

export function authenticatePlatformAdmin(context: PlatformRequestContext): preHandlerHookHandler {
  return async (request) => {
    const principal = await resolvePrincipal(request, context);
    requirePlatformRole(principal, ["admin"]);
    assertCsrf(request, principal, context.config);
    request.platformPrincipal = principal;
  };
}

/**
 * Read-only admin access. Browsers omit `Origin` on same-origin GET requests, so
 * reads must not require the CSRF/Origin check that guards state changes.
 */
export function authenticatePlatformAdminRead(
  context: PlatformRequestContext,
): preHandlerHookHandler {
  return async (request) => {
    const principal = await resolvePrincipal(request, context);
    requirePlatformRole(principal, ["admin"]);
    request.platformPrincipal = principal;
  };
}

/**
 * Origin is checked against the configured allowlist and the CSRF token against
 * the hash stored on the session; both are required for cookie-authenticated writes.
 */
export function assertCsrf(
  request: FastifyRequest,
  principal: PlatformPrincipal,
  config: ApiConfig,
): void {
  assertTrustedOrigin(
    typeof request.headers.origin === "string" ? request.headers.origin : undefined,
    config.trustedOrigins,
  );
  const header = request.headers["x-csrf-token"];
  const token = typeof header === "string" ? header : undefined;
  if (!token || !csrfTokenMatches(token, principal.csrfTokenHash)) {
    throw new AppError(403, "CSRF_TOKEN_INVALID", "The CSRF token is missing or invalid");
  }
}

export function absoluteExpiry(now = new Date()): Date {
  return new Date(now.getTime() + SESSION_ABSOLUTE_MS);
}
