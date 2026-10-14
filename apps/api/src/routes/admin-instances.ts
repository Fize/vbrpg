import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { AppError } from "@vbrpg/runtime";
import {
  authenticatePlatformAdmin,
  authenticatePlatformAdminRead,
  type PlatformPrincipal,
  type PlatformRequestContext,
} from "../platform-auth.js";

const instanceIdParamSchema = z.object({ instanceId: z.string().min(1) });

export async function registerAdminInstanceRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
): Promise<void> {
  const requireAdmin = authenticatePlatformAdmin(context);
  const requireAdminRead = authenticatePlatformAdminRead(context);

  async function audit(
    principal: PlatformPrincipal,
    action: string,
    instanceId: string,
    metadata: Record<string, unknown>,
  ): Promise<void> {
    await context.store.recordAudit({
      actorUserId: principal.userId,
      action,
      resourceType: "game_instance",
      resourceId: instanceId,
      metadata,
      succeeded: true,
    });
  }

  app.post("/v1/admin/instances/:instanceId/pause", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { instanceId } = instanceIdParamSchema.parse(request.params);
    const action = await context.store.pauseInstance(instanceId);
    if (action === "rejected") {
      throw new AppError(409, "INSTANCE_NOT_PAUSABLE", "The instance is finished or does not exist");
    }
    await audit(principal, "instance.pause", instanceId, {});
    return { status: action };
  });

  app.post("/v1/admin/instances/:instanceId/resume", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { instanceId } = instanceIdParamSchema.parse(request.params);
    const action = await context.store.resumeInstance(instanceId);
    if (action === "rejected") {
      throw new AppError(409, "INSTANCE_NOT_PAUSED", "Only a paused instance can be resumed");
    }
    await audit(principal, "instance.resume", instanceId, {});
    return { status: action };
  });

  app.post("/v1/admin/instances/:instanceId/cancel", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { instanceId } = instanceIdParamSchema.parse(request.params);
    const action = await context.store.cancelInstance(instanceId);
    if (action === "rejected") {
      throw new AppError(409, "INSTANCE_NOT_CANCELLABLE", "The instance is already finished or does not exist");
    }
    await audit(principal, "instance.cancel", instanceId, {});
    return { status: action };
  });

  app.post("/v1/admin/instances/:instanceId/timeout", { preHandler: requireAdmin }, async (request) => {
    const principal = request.platformPrincipal!;
    const { instanceId } = instanceIdParamSchema.parse(request.params);
    const result = await context.store.forceInstanceTimeout(instanceId);
    if (result.outcome === "skipped") {
      if (result.reason === "INSTANCE_NOT_FOUND") {
        throw new AppError(404, "INSTANCE_NOT_FOUND", "Unknown game instance");
      }
      throw new AppError(409, "NOT_TIMEOUTABLE", `The instance cannot be timed out: ${result.reason ?? "unknown"}`);
    }
    await audit(principal, "instance.force_timeout", instanceId, { outcome: result.outcome });
    return result;
  });

  // Redacted operational view: structure without any hidden value.
  app.get(
    "/v1/admin/instances/:instanceId",
    { preHandler: requireAdminRead },
    async (request) => {
      const { instanceId } = instanceIdParamSchema.parse(request.params);
      const view = await context.store.describeInstance(instanceId);
      if (!view) throw new AppError(404, "INSTANCE_NOT_FOUND", "Unknown game instance");
      return view;
    },
  );
}
