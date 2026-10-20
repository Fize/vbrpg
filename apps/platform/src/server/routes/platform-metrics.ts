import type { FastifyInstance } from "fastify";
import { authenticatePlatformAdminRead, type PlatformRequestContext } from "../platform-auth.js";
import type { Metrics } from "../metrics.js";

/** Operator read: how the platform is doing, in the same process that is serving it. */
export async function registerMetricsRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
  metrics: Metrics,
): Promise<void> {
  app.get("/v1/admin/metrics", { preHandler: authenticatePlatformAdminRead(context) }, async () =>
    metrics.snapshot(),
  );
}
