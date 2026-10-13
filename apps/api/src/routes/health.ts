import type { FastifyInstance } from "fastify";
import type { ApiConfig } from "../config.js";

export async function registerHealthRoutes(
  app: FastifyInstance,
  config: ApiConfig,
): Promise<void> {
  app.get("/health", async (request) => ({
    status: "ok",
    service: "api",
    requestId: request.id,
  }));

  app.get("/ready", async (request, reply) => {
    const database = config.databaseUrl === undefined ? "not_configured" : "configured";
    if (database === "not_configured") {
      return reply.code(503).send({
        status: "not_ready",
        checks: { database },
        requestId: request.id,
      });
    }

    return {
      status: "ready",
      checks: { database },
      requestId: request.id,
    };
  });
}
