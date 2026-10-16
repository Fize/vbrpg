import type { FastifyInstance } from "fastify";
import { z } from "zod";
import {
  parseCreateMatchRequest,
  parseSubmitEventRequest,
  parseUpdateMatchStatusRequest,
} from "../../shared/index.js";
import {
  authenticatePlatform,
  authenticatePlatformWithCsrf,
  type PlatformRequestContext,
} from "../platform-auth.js";
import { AppError } from "../runtime/index.js";
import type { MatchActor, MatchService } from "../match/service.js";

const instanceParamSchema = z.object({ instanceId: z.string().uuid() });

export async function registerMatchRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
  matchService: MatchService,
): Promise<void> {
  const readOnly = authenticatePlatform(context);
  const write = authenticatePlatformWithCsrf(context);

  const actorOf = (request: { platformPrincipal?: { userId: string; role: string } }): MatchActor => ({
    userId: request.platformPrincipal!.userId,
    isAdmin: request.platformPrincipal!.role === "admin",
  });

  app.get("/v1/games", { preHandler: readOnly }, async () => ({
    games: matchService.listGames(),
  }));

  app.get("/v1/instances", { preHandler: readOnly }, async (request) => ({
    matches: await matchService.list({ actor: actorOf(request) }),
  }));

  app.post("/v1/instances", { preHandler: write }, async (request, reply) => {
    const body = parseCreateMatchRequest(request.body);
    const summary = await matchService.create({ actor: actorOf(request), request: body });
    return reply.code(201).send(summary);
  });

  app.post("/v1/instances/:instanceId/events", { preHandler: write }, async (request) => {
    const { instanceId } = instanceParamSchema.parse(request.params);
    const header = request.headers["idempotency-key"];
    const idempotencyKey = typeof header === "string" ? header.trim() : "";
    if (idempotencyKey.length === 0) {
      throw new AppError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required");
    }
    const body = parseSubmitEventRequest(request.body);
    return matchService.submit({ actor: actorOf(request), instanceId, idempotencyKey, request: body });
  });

  app.get("/v1/instances/:instanceId", { preHandler: readOnly }, async (request) => {
    const { instanceId } = instanceParamSchema.parse(request.params);
    return matchService.read({ actor: actorOf(request), instanceId });
  });

  // Administrator lifecycle: an audit row and a status change, never a game event.
  app.patch("/v1/instances/:instanceId/status", { preHandler: write }, async (request) => {
    const { instanceId } = instanceParamSchema.parse(request.params);
    const body = parseUpdateMatchStatusRequest(request.body);
    return matchService.setStatus({ actor: actorOf(request), instanceId, status: body.status });
  });
}
