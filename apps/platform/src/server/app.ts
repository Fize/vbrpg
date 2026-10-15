import Fastify, { type FastifyInstance } from "fastify";
import { ZodError } from "zod";
import { loadConfig, type ApiConfig } from "./config.js";
import { AppError, type ErrorResponse } from "./runtime/index.js";
import { registerHealthRoutes } from "./routes/health.js";
import { registerPlatformAuthRoutes } from "./routes/platform-auth.js";
import { registerPlatformAdminRoutes } from "./routes/platform-admin.js";
import { registerMatchRoutes } from "./routes/matches.js";
import type { MatchService } from "./match/service.js";
import type { PlatformStore } from "./store.js";
import { createPlatformRequestContext } from "./platform-auth.js";

export interface BuildAppOptions {
  config?: ApiConfig;
  platformStore?: PlatformStore;
  matchService?: MatchService;
}

export function buildApp(options: BuildAppOptions = {}): FastifyInstance {
  const config = options.config ?? loadConfig();
  if (config.environment === "production" && !options.platformStore) {
    throw new Error("Production requires a database-backed platform store");
  }
  const app = Fastify({
    logger: { level: config.logLevel },
    requestIdHeader: "x-request-id",
  });

  app.addHook("onSend", async (request, reply) => {
    reply.header("x-request-id", request.id);
  });

  app.setNotFoundHandler((request, reply) => {
    const response: ErrorResponse = {
      error: "Route not found",
      code: "ROUTE_NOT_FOUND",
      details: { method: request.method, url: request.url },
      requestId: request.id,
    };
    return reply.code(404).send(response);
  });

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof AppError) {
      return reply.code(error.statusCode).send({
        error: error.message,
        code: error.code,
        details: error.details,
        requestId: request.id,
      } satisfies ErrorResponse);
    }

    if (error instanceof ZodError) {
      return reply.code(400).send({
        error: "Invalid request",
        code: "INVALID_REQUEST",
        details: { issues: error.issues },
        requestId: request.id,
      } satisfies ErrorResponse);
    }

    request.log.error({ err: error }, "Unhandled request error");
    return reply.code(500).send({
      error: "Internal server error",
      code: "INTERNAL_ERROR",
      details: {},
      requestId: request.id,
    } satisfies ErrorResponse);
  });

  void registerHealthRoutes(app, config);
  if (options.platformStore) {
    const platformContext = createPlatformRequestContext(options.platformStore, config);
    void registerPlatformAuthRoutes(app, platformContext);
    void registerPlatformAdminRoutes(app, platformContext);
    if (options.matchService) {
      void registerMatchRoutes(app, platformContext, options.matchService);
    }
  }
  return app;
}
