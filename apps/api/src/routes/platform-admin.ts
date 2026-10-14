import type { FastifyInstance } from "fastify";
import { randomUUID } from "node:crypto";
import { z } from "zod";
import {
  createProviderModelRequestSchema,
  createUserRequestSchema,
  normalizeUsername,
  providerInputSchema,
  updateProviderModelRequestSchema,
  updateProviderRequestSchema,
  updateUserRequestSchema,
  type ConnectionTestResult,
} from "@vbrpg/contracts";
import { AppError } from "@vbrpg/runtime";
import { hashPassword } from "../password.js";
import { openCredential, sealCredential, type CredentialKey } from "@vbrpg/runtime";
import { parseProviderEndpoint, testProviderConnection } from "../provider-endpoint.js";
import { createConcurrencyLimiter } from "../rate-limit.js";
import {
  authenticatePlatform,
  authenticatePlatformAdmin,
  authenticatePlatformAdminRead,
  requirePasswordChanged,
  type PlatformPrincipal,
  type PlatformRequestContext,
} from "../platform-auth.js";
import { toUserView } from "./platform-auth.js";

const providerIdParamSchema = z.object({ providerId: z.string().uuid() });
const modelIdParamSchema = z.object({ modelId: z.string().uuid() });
const userIdParamSchema = z.object({ userId: z.string().uuid() });

export async function registerPlatformAdminRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
): Promise<void> {
  const requireAdmin = authenticatePlatformAdmin(context);
  const requireAdminRead = authenticatePlatformAdminRead(context);
  const requireAuthenticated = authenticatePlatform(context);

  app.get("/v1/admin/users", { preHandler: requireAdminRead }, async () => ({
    users: (await context.store.listUsers()).map(toUserView),
  }));

  app.post("/v1/admin/users", { preHandler: requireAdmin }, async (request, reply) => {
    const principal = request.platformPrincipal!;
    const body = createUserRequestSchema.parse(request.body);
    try {
      const created = await context.store.createUser({
        username: normalizeUsername(body.username),
        passwordHash: await hashPassword(body.temporaryPassword),
        role: body.role,
        mustChangePassword: true,
      });
      await context.store.recordAudit({
        actorUserId: principal.userId,
        action: "admin.user.create",
        resourceType: "user",
        resourceId: created.id,
        metadata: { role: created.role },
        succeeded: true,
      });
      return reply.code(201).send(toUserView(created));
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new AppError(409, "USERNAME_TAKEN", "That username is already in use");
      }
      throw error;
    }
  });

  app.patch("/v1/admin/users/:userId", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { userId } = userIdParamSchema.parse(request.params);
    const body = updateUserRequestSchema.parse(request.body);
    const target = await context.store.getUser(userId);
    if (!target) throw new AppError(404, "USER_NOT_FOUND", "No such account");

    const remainsAdmin = (body.role ?? target.role) === "admin";
    const remainsActive = body.active ?? target.active;
    if (target.role === "admin" && target.active && (!remainsAdmin || !remainsActive)) {
      if ((await context.store.countActiveAdmins()) <= 1) {
        throw new AppError(409, "LAST_ADMIN", "The last active administrator cannot be demoted or disabled");
      }
    }

    const updated = await context.store.updateUser(userId, {
      ...(body.role === undefined ? {} : { role: body.role }),
      ...(body.active === undefined ? {} : { active: body.active }),
      ...(body.resetPassword === undefined
        ? {}
        : { passwordHash: await hashPassword(body.resetPassword), mustChangePassword: true }),
    });
    if (!updated) throw new AppError(404, "USER_NOT_FOUND", "No such account");

    // Role, status and password changes all invalidate existing sessions.
    await context.store.revokeUserSessions(userId);
    await context.store.recordAudit({
      actorUserId: principal.userId,
      action: "admin.user.update",
      resourceType: "user",
      resourceId: userId,
      metadata: {
        role: body.role,
        active: body.active,
        passwordReset: body.resetPassword !== undefined,
      },
      succeeded: true,
    });
    return toUserView(updated);
  });

  app.get("/v1/providers", { preHandler: requireAuthenticated }, async (request) => {
    requirePasswordChanged(request.platformPrincipal!);
    return { providers: await context.store.listProviders({ includeDisabled: false }) };
  });

  app.get("/v1/admin/providers", { preHandler: requireAdminRead }, async () => ({
    providers: await context.store.listProviders({ includeDisabled: true }),
  }));

  app.post("/v1/admin/providers", { preHandler: requireAdmin }, async (request, reply) => {
    const principal = request.platformPrincipal!;
    const body = providerInputSchema.parse(request.body);
    parseProviderEndpoint(body.baseUrl);
    try {
      const id = randomUUID();
      const created = await context.store.createProvider({
        id,
        name: body.name,
        baseUrl: body.baseUrl,
        enabled: true,
        // Associated data binds the ciphertext to this provider record.
        credential: sealCredential(body.apiKey, id, requireCredentialKey(context)),
      });
      await context.store.recordAudit({
        actorUserId: principal.userId,
        action: "admin.provider.create",
        resourceType: "provider",
        resourceId: created.id,
        succeeded: true,
      });
      return reply.code(201).send(created);
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new AppError(409, "PROVIDER_NAME_TAKEN", "That provider name is already in use");
      }
      throw error;
    }
  });

  app.patch("/v1/admin/providers/:providerId", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { providerId } = providerIdParamSchema.parse(request.params);
    const body = updateProviderRequestSchema.parse(request.body);
    if (body.baseUrl !== undefined) parseProviderEndpoint(body.baseUrl);

    try {
      const updated = await context.store.updateProvider(providerId, {
        ...(body.name === undefined ? {} : { name: body.name }),
        ...(body.baseUrl === undefined ? {} : { baseUrl: body.baseUrl }),
        ...(body.enabled === undefined ? {} : { enabled: body.enabled }),
        ...(body.apiKey === undefined
          ? {}
          : { credential: sealCredential(body.apiKey, providerId, requireCredentialKey(context)) }),
      });
      if (!updated) throw new AppError(404, "PROVIDER_NOT_FOUND", "No such provider");
      await context.store.recordAudit({
        actorUserId: principal.userId,
        action: "admin.provider.update",
        resourceType: "provider",
        resourceId: providerId,
        metadata: { secretReplaced: body.apiKey !== undefined, enabled: body.enabled },
        succeeded: true,
      });
      // Return the stored view so the response reflects persisted state.
      return (await context.store.getProviderView(providerId)) ?? updated;
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new AppError(409, "PROVIDER_NAME_TAKEN", "That provider name is already in use");
      }
      throw error;
    }
  });

  app.post("/v1/admin/providers/:providerId/test", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { providerId } = providerIdParamSchema.parse(request.params);
    return runConnectionTest(context, principal, providerId);
  });

  app.post("/v1/admin/providers/:providerId/models", { preHandler: requireAdmin }, async (request, reply) => {
    const principal = request.platformPrincipal!;
    const { providerId } = providerIdParamSchema.parse(request.params);
    const body = createProviderModelRequestSchema.parse(request.body);
    try {
      const model = await context.store.createProviderModel({
        providerId,
        modelId: body.modelId,
        displayName: body.displayName,
        enabled: body.enabled,
      });
      if (!model) throw new AppError(500, "MODEL_NOT_CREATED", "The model could not be created");
      await context.store.recordAudit({
        actorUserId: principal.userId,
        action: "admin.provider.model.create",
        resourceType: "provider_model",
        resourceId: model.id,
        metadata: { providerId },
        succeeded: true,
      });
      return reply.code(201).send(model);
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new AppError(409, "MODEL_TAKEN", "That model id already exists for this provider");
      }
      if (isForeignKeyViolation(error)) {
        throw new AppError(404, "PROVIDER_NOT_FOUND", "No such provider");
      }
      throw error;
    }
  });

  app.patch("/v1/admin/models/:modelId", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { modelId } = modelIdParamSchema.parse(request.params);
    const body = updateProviderModelRequestSchema.parse(request.body);
    try {
      const updated = await context.store.updateProviderModel(modelId, {
        ...(body.modelId === undefined ? {} : { modelId: body.modelId }),
        ...(body.displayName === undefined ? {} : { displayName: body.displayName }),
        ...(body.enabled === undefined ? {} : { enabled: body.enabled }),
      });
      if (!updated) throw new AppError(404, "MODEL_NOT_FOUND", "No such model");
      await context.store.recordAudit({
        actorUserId: principal.userId,
        action: "admin.provider.model.update",
        resourceType: "provider_model",
        resourceId: modelId,
        succeeded: true,
      });
      return updated;
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new AppError(409, "MODEL_TAKEN", "That model id already exists for this provider");
      }
      throw error;
    }
  });
}

function requireCredentialKey(context: PlatformRequestContext): CredentialKey {
  if (!context.config.credentialKey) {
    throw new AppError(
      503,
      "CREDENTIAL_KEY_NOT_CONFIGURED",
      "PLATFORM_CREDENTIAL_KEY must be configured before storing provider credentials",
    );
  }
  return context.config.credentialKey;
}

async function runConnectionTest(
  context: PlatformRequestContext,
  principal: PlatformPrincipal,
  providerId: string,
): Promise<ConnectionTestResult> {
  if (!context.limiters.connectionTestByAdmin.allow(`provider-test:${principal.userId}`)) {
    throw new AppError(429, "RATE_LIMITED", "Too many connection tests for this account");
  }
  const slots = context.limiters.connectionTestSlots;
  let limiter = slots.get(principal.userId);
  if (!limiter) {
    limiter = createConcurrencyLimiter(2);
    slots.set(principal.userId, limiter);
  }

  const record = await context.store.getProviderSecret(providerId);
  if (!record) throw new AppError(404, "PROVIDER_NOT_FOUND", "No such provider");
  if (!record.enabled) {
    throw new AppError(409, "PROVIDER_DISABLED", "A disabled provider cannot be tested");
  }

  const running = limiter.run(async () => {
    const endpoint = parseProviderEndpoint(record.baseUrl);
    const apiKey = openCredential(record.sealed, providerId, requireCredentialKey(context));
    const result = await testProviderConnection({ endpoint, apiKey });
    await context.store.recordAudit({
      actorUserId: principal.userId,
      action: "admin.provider.test",
      resourceType: "provider",
      resourceId: providerId,
      metadata: { ok: result.ok, errorCode: result.errorCode, latencyMs: result.latencyMs },
      succeeded: result.ok,
    });
    return result;
  });
  if (!running) {
    throw new AppError(429, "CONNECTION_TEST_SATURATED", "Two connection tests are already running");
  }
  return running;
}

function isUniqueViolation(error: unknown): boolean {
  return readPgCode(error) === "23505";
}

function isForeignKeyViolation(error: unknown): boolean {
  return readPgCode(error) === "23503";
}

function readPgCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) return undefined;
  const code = (error as { code?: unknown }).code;
  return typeof code === "string" ? code : undefined;
}
