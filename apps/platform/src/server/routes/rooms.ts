import type { FastifyInstance } from "fastify";
import { z } from "zod";
import {
  parseCreateRoomRequest,
  parseJoinRoomByCodeRequest,
  parseRoomReadyRequest,
  parseUpdateRoomRequest,
} from "../../shared/index.js";
import {
  authenticatePlatform,
  authenticatePlatformWithCsrf,
  type PlatformRequestContext,
} from "../platform-auth.js";
import { AppError } from "../runtime/index.js";
import type { RoomActor, RoomService } from "../room/service.js";

const roomParamSchema = z.object({ roomId: z.string().uuid() });

export async function registerRoomRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
  rooms: RoomService,
): Promise<void> {
  const readOnly = authenticatePlatform(context);
  const write = authenticatePlatformWithCsrf(context);
  const actorOf = (request: {
    platformPrincipal?: { userId: string; role: string };
  }): RoomActor => ({
    userId: request.platformPrincipal!.userId,
    isAdmin: request.platformPrincipal!.role === "admin",
  });

  app.post("/v1/rooms", { preHandler: write }, async (request, reply) => {
    const body = parseCreateRoomRequest(request.body);
    const detail = await rooms.create({ actor: actorOf(request), request: body });
    return reply.code(201).send(detail);
  });

  app.get("/v1/rooms", { preHandler: readOnly }, async (request) => ({
    rooms: await rooms.list({ actor: actorOf(request) }),
  }));

  // Reading the code out loud is how people get into a room they were told about.
  app.post("/v1/rooms/join", { preHandler: write }, async (request) => {
    const body = parseJoinRoomByCodeRequest(request.body);
    return rooms.joinByCode({ actor: actorOf(request), code: body.code });
  });

  app.get("/v1/rooms/:roomId", { preHandler: readOnly }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    return rooms.read({ actor: actorOf(request), roomId });
  });

  app.get("/v1/rooms/:roomId/matches", { preHandler: readOnly }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    return { matches: await rooms.matches({ actor: actorOf(request), roomId }) };
  });

  app.patch("/v1/rooms/:roomId", { preHandler: write }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    const patch = parseUpdateRoomRequest(request.body);
    return rooms.update({ actor: actorOf(request), roomId, patch });
  });

  app.post("/v1/rooms/:roomId/join", { preHandler: write }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    return rooms.join({ actor: actorOf(request), roomId });
  });

  app.post("/v1/rooms/:roomId/ready", { preHandler: write }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    const body = parseRoomReadyRequest(request.body);
    return rooms.setReady({ actor: actorOf(request), roomId, ready: body.ready });
  });

  app.post("/v1/rooms/:roomId/leave", { preHandler: write }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    return rooms.leave({ actor: actorOf(request), roomId });
  });

  // Starting a match is the one room action that can spend money (the model's word pair).
  app.post("/v1/rooms/:roomId/start", { preHandler: write }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    const actor = actorOf(request);
    if (!context.limiters.matchStartByUser.allow(actor.userId)) {
      throw new AppError(429, "RATE_LIMITED", "Too many matches started");
    }
    return rooms.start({ actor, roomId });
  });

  app.post("/v1/rooms/:roomId/close", { preHandler: write }, async (request) => {
    const { roomId } = roomParamSchema.parse(request.params);
    return rooms.close({ actor: actorOf(request), roomId });
  });
}
