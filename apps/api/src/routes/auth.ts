import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import type { ApiConfig } from "../config.js";
import { requireRole } from "../auth.js";

export async function registerAuthRoutes(
  app: FastifyInstance,
  _config: ApiConfig,
  authenticateRequest: preHandlerHookHandler,
): Promise<void> {
  app.get("/v1/tenant/me", { preHandler: authenticateRequest }, async (request) => ({
    userId: request.authPrincipal?.userId,
    tenantId: request.authPrincipal?.tenantId,
    roles: request.authPrincipal?.roles,
    sessionId: request.authPrincipal?.sessionId,
  }));

  app.get(
    "/v1/tenant/management-check",
    {
      preHandler: [
        authenticateRequest,
        async (request) => {
          requireRole(request.authPrincipal!, ["owner", "admin"]);
        },
      ],
    },
    async (request) => ({
      status: "authorized",
      tenantId: request.authPrincipal?.tenantId,
    }),
  );
}
