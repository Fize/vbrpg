import type { FastifyInstance } from "fastify";
import type { ApiConfig } from "../config.js";

export async function registerHealthRoutes(
  app: FastifyInstance,
  _config: ApiConfig,
): Promise<void> {
  app.get("/health", async (request) => ({
    status: "ok",
    service: "api",
    requestId: request.id,
  }));
}
