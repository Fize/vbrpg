import type { FastifyInstance, FastifyReply } from "fastify";
import {
  parseChangePasswordRequest,
  parseLoginRequest,
  type LoginResult,
  type PlatformUser,
} from "../../shared/index.js";
import { AppError } from "../runtime/index.js";
import { hashPassword, verifyPassword } from "../password.js";
import { createCsrfToken, hashCsrfToken } from "../csrf.js";
import {
  SESSION_IDLE_MS,
  buildSessionCookie,
  clearSessionCookie,
  createSessionToken,
  hashToken,
  idleExpiry,
} from "../session.js";
import {
  absoluteExpiry,
  authenticatePlatform,
  authenticatePlatformWithCsrf,
  type PlatformRequestContext,
} from "../platform-auth.js";
import type { PlatformUserRecord } from "../db/index.js";
const GENERIC_LOGIN_FAILURE = new AppError(401, "INVALID_CREDENTIALS", "Invalid username or password");

export function toUserView(user: PlatformUserRecord): PlatformUser {
  return {
    id: user.id,
    username: user.username,
    role: user.role,
    active: user.active,
    mustChangePassword: user.mustChangePassword,
    createdAt: user.createdAt.toISOString(),
  };
}

export async function issueSession(
  context: PlatformRequestContext,
  reply: FastifyReply,
  userId: string,
  now = new Date(),
): Promise<{ csrfToken: string; expiresAt: Date }> {
  const token = createSessionToken();
  const csrfToken = createCsrfToken();
  const absoluteLifetime = absoluteExpiry(now);
  await context.store.createSession({
    userId,
    tokenHash: hashToken(token),
    csrfTokenHash: hashCsrfToken(csrfToken),
    idleExpiresAt: idleExpiry(now, absoluteLifetime),
    absoluteExpiresAt: absoluteLifetime,
  });
  reply.header(
    "set-cookie",
    buildSessionCookie(token, absoluteLifetime, context.config.sessionCookieSecure),
  );
  return { csrfToken, expiresAt: absoluteLifetime };
}

export async function registerPlatformAuthRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
): Promise<void> {
  const authenticate = authenticatePlatform(context);
  const authenticateWithCsrf = authenticatePlatformWithCsrf(context);

  app.post("/v1/auth/login", async (request, reply) => {
    const body = parseLoginRequest(request.body);
    const username = body.username.trim().toLowerCase();
    if (
      !context.limiters.loginByIp.allow(request.ip) ||
      !context.limiters.loginByAccount.allow(username)
    ) {
      await context.store.recordAudit({
        actorUserId: null,
        action: "auth.login",
        resourceType: "user",
        resourceId: null,
        metadata: { username },
        succeeded: false,
      });
      throw new AppError(429, "RATE_LIMITED", "Too many login attempts");
    }

    const user = await context.store.findUserByUsername(username);
    const passwordOk = await verifyPassword(body.password, user?.passwordHash ?? null);
    if (!user || !passwordOk || !user.active) {
      await context.store.recordAudit({
        actorUserId: user?.id ?? null,
        action: "auth.login",
        resourceType: "user",
        resourceId: user?.id ?? null,
        metadata: { username },
        succeeded: false,
      });
      throw GENERIC_LOGIN_FAILURE;
    }

    const session = await issueSession(context, reply, user.id);
    await context.store.recordAudit({
      actorUserId: user.id,
      action: "auth.login",
      resourceType: "user",
      resourceId: user.id,
      succeeded: true,
    });
    const result: LoginResult = {
      user: toUserView(user),
      csrfToken: session.csrfToken,
      expiresAt: session.expiresAt.toISOString(),
    };
    return reply.code(200).send(result);
  });

  app.post(
    "/v1/auth/logout",
    { preHandler: authenticateWithCsrf },
    async (request, reply) => {
      const principal = request.platformPrincipal!;
      await context.store.revokeSession(principal.sessionId);
      await context.store.recordAudit({
        actorUserId: principal.userId,
        action: "auth.logout",
        resourceType: "session",
        resourceId: principal.sessionId,
        succeeded: true,
      });
      reply.header("set-cookie", clearSessionCookie(context.config.sessionCookieSecure));
      return reply.code(204).send();
    },
  );

  app.get("/v1/auth/csrf", { preHandler: authenticate }, async (request) => {
    const principal = request.platformPrincipal!;
    const csrfToken = createCsrfToken();
    await context.store.rotateCsrfToken(principal.sessionId, hashCsrfToken(csrfToken));
    return { csrfToken };
  });

  app.get("/v1/me", { preHandler: authenticate }, async (request) => {
    const principal = request.platformPrincipal!;
    const user = await context.store.getUser(principal.userId);
    if (!user) throw new AppError(401, "SESSION_INVALID", "Authentication session is invalid or expired");
    return toUserView(user);
  });

  app.post(
    "/v1/auth/password",
    { preHandler: authenticateWithCsrf },
    async (request, reply) => {
      const principal = request.platformPrincipal!;
      const body = parseChangePasswordRequest(request.body);
      const user = await context.store.getUser(principal.userId);
      if (!user || !user.active) {
        throw new AppError(401, "SESSION_INVALID", "Authentication session is invalid or expired");
      }
      if (!(await verifyPassword(body.currentPassword, user.passwordHash))) {
        throw new AppError(403, "CURRENT_PASSWORD_INVALID", "The current password is incorrect");
      }
      if (body.currentPassword === body.newPassword) {
        throw new AppError(400, "PASSWORD_UNCHANGED", "The new password must differ from the current password");
      }

      await context.store.updateUser(user.id, {
        passwordHash: await hashPassword(body.newPassword),
        mustChangePassword: false,
      });
      // Every prior session is invalidated, then a fresh one is issued so the
      // caller keeps working with a rotated token and CSRF secret.
      await context.store.revokeUserSessions(user.id);
      const fresh = await context.store.getUser(user.id);
      if (!fresh) throw new AppError(500, "ACCOUNT_MISSING", "The account disappeared during the update");
      const session = await issueSession(context, reply, user.id);
      await context.store.recordAudit({
        actorUserId: user.id,
        action: "auth.password.change",
        resourceType: "user",
        resourceId: user.id,
        succeeded: true,
      });
      const result: LoginResult = {
        user: toUserView(fresh),
        csrfToken: session.csrfToken,
        expiresAt: session.expiresAt.toISOString(),
      };
      return reply.code(200).send(result);
    },
  );
}
