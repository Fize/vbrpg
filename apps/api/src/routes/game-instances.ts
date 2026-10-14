import { randomUUID } from "node:crypto";
import type { FastifyInstance } from "fastify";
import { PLATFORM_TENANT_ID } from "@vbrpg/db";
import {
  parseCreateInstanceRequest,
  parseSubmitEventRequest,
  type GameEvent,
} from "@vbrpg/contracts";
import { AppError } from "@vbrpg/runtime";
import { EngineError } from "@vbrpg/workflow-engine";
import {
  authenticatePlatform,
  authenticatePlatformWithCsrf,
  requirePasswordChanged,
  type PlatformRequestContext,
} from "../platform-auth.js";
import { createRateLimiter } from "../rate-limit.js";

function readIdempotencyKey(header: string | string[] | undefined): string | undefined {
  const value = Array.isArray(header) ? header[0] : header;
  return value === undefined || value === "" ? undefined : value;
}

/** Engine rejections are caller-visible conflicts, not server faults. */
function toConflict(error: unknown): AppError {
  if (error instanceof EngineError) {
    return new AppError(409, error.code, error.message);
  }
  return new AppError(409, "INSTANCE_CONFLICT", error instanceof Error ? error.message : "Event rejected");
}

export async function registerGameInstanceRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
): Promise<void> {
  const createLimiter = createRateLimiter({ limit: 30, windowMs: 60_000 });

  app.post("/v1/instances", { preHandler: [authenticatePlatformWithCsrf(context)] }, async (request, reply) => {
    const principal = request.platformPrincipal;
    if (!principal) throw new AppError(401, "SESSION_INVALID", "Authentication is required");
    requirePasswordChanged(principal);
    if (!createLimiter.allow(principal.userId)) {
      throw new AppError(429, "RATE_LIMITED", "Too many instances created recently");
    }

    const body = parseCreateInstanceRequest(request.body);
    const instanceId = randomUUID();
    const state = await context.store.createInstance({
      instanceId,
      gameVersionId: body.gameVersionId,
      randomSeed: body.randomSeed ?? randomUUID(),
      participants: body.participants,
      ...(body.variables === undefined ? {} : { variables: body.variables }),
    });
    if (!state) {
      throw new AppError(404, "GAME_VERSION_NOT_FOUND", "No workflow definition exists for that game version");
    }

    const createdEvent: GameEvent = {
      eventId: randomUUID(),
      instanceId,
      sequence: 1,
      type: "instanceCreated",
      actor: { userId: principal.userId, tenantId: PLATFORM_TENANT_ID },
      occurredAtMs: Date.now(),
      idempotencyKey: `${instanceId}:created`,
      payload: {},
    };
    let created;
    try {
      created = await context.store.appendEvent(instanceId, createdEvent);
    } catch (error) {
      throw toConflict(error);
    }
    reply.code(201);
    return {
      instanceId,
      state: created?.state ?? state,
      commands: created?.commands ?? [],
    };
  });

  app.get(
    "/v1/instances/:instanceId",
    { preHandler: [authenticatePlatform(context)] },
    async (request) => {
      const principal = request.platformPrincipal;
      if (!principal) throw new AppError(401, "SESSION_INVALID", "Authentication is required");
      requirePasswordChanged(principal);
      const { instanceId } = request.params as { instanceId: string };
      const view = await context.store.getInstanceState(instanceId);
      if (!view) throw new AppError(404, "INSTANCE_NOT_FOUND", "Unknown game instance");
      return view;
    },
  );

  app.post(
    "/v1/instances/:instanceId/events",
    { preHandler: [authenticatePlatformWithCsrf(context)] },
    async (request) => {
      const principal = request.platformPrincipal;
      if (!principal) throw new AppError(401, "SESSION_INVALID", "Authentication is required");
      requirePasswordChanged(principal);

      const { instanceId } = request.params as { instanceId: string };
      const body = parseSubmitEventRequest(request.body);
      const view = await context.store.getInstanceState(instanceId);
      if (!view) throw new AppError(404, "INSTANCE_NOT_FOUND", "Unknown game instance");

      // Sequence and event id are server-derived; the client only chooses the idempotency token.
      const token = readIdempotencyKey(request.headers["idempotency-key"]) ?? randomUUID();
      const event: GameEvent = {
        eventId: randomUUID(),
        instanceId,
        sequence: view.currentSequence + 1,
        type: body.type,
        actor: { userId: principal.userId, tenantId: PLATFORM_TENANT_ID },
        occurredAtMs: Date.now(),
        idempotencyKey: `${instanceId}:${token}`,
        payload: body.payload,
      };

      try {
        const result = await context.store.appendEvent(instanceId, event);
        if (!result) throw new AppError(404, "INSTANCE_NOT_FOUND", "Unknown game instance");
        return { state: result.state, commands: result.commands, replayed: result.replayed };
      } catch (error) {
        if (error instanceof AppError) throw error;
        throw toConflict(error);
      }
    },
  );
}
