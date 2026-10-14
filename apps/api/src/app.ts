import Fastify, { type FastifyInstance } from "fastify";
import { ZodError } from "zod";
import { loadConfig, type ApiConfig } from "./config.js";
import { AppError, type ErrorResponse } from "./errors.js";
import { authenticate, authenticateWithSession, type AuthSessionLookup } from "./auth.js";
import { registerHealthRoutes } from "./routes/health.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { registerRuntimeRoutes } from "./routes/runtime.js";
import { registerPlatformAuthRoutes } from "./routes/platform-auth.js";
import { registerPlatformAdminRoutes } from "./routes/platform-admin.js";
import type { PlatformStore } from "./store.js";
import { createPlatformRequestContext } from "./platform-auth.js";
import { createOpenAiCompatibleClient } from "./ai.js";
import type { AiClient } from "./ai.js";

declare module "fastify" {
  interface FastifyRequest {
    authPrincipal?: import("./auth.js").AuthPrincipal;
  }
}

export interface BuildAppOptions {
  config?: ApiConfig;
  sessionLookup?: AuthSessionLookup;
  aiClient?: AiClient;
  platformStore?: PlatformStore;
}

export function buildApp(options: BuildAppOptions = {}): FastifyInstance {
  const config = options.config ?? loadConfig();
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
  void registerAuthRoutes(app, config, async (request) => {
    const tenantHeader = typeof request.headers["x-tenant-id"] === "string"
      ? request.headers["x-tenant-id"]
      : undefined;
    const principal = options.sessionLookup
      ? await authenticateWithSession(
        request.headers.authorization,
        tenantHeader,
        config.authTokenSecret,
        options.sessionLookup,
      )
      : authenticate(request.headers.authorization, tenantHeader, config.authTokenSecret);
    if (config.environment === "production" && !options.sessionLookup) {
      throw new AppError(503, "AUTH_SESSION_STORE_NOT_CONFIGURED", "Production authentication requires a session store");
    }
    request.authPrincipal = principal;
  });
  if (options.platformStore) {
    const platformContext = createPlatformRequestContext(options.platformStore, config);
    void registerPlatformAuthRoutes(app, platformContext);
    void registerPlatformAdminRoutes(app, platformContext);
  }
  void registerRuntimeRoutes(app, options.aiClient ?? createOpenAiCompatibleClient({
    ...(config.aiApiKey === undefined ? {} : { apiKey: config.aiApiKey }),
    baseUrl: config.aiApiBaseUrl,
    model: config.aiModel,
    timeoutMs: config.aiTimeoutMs,
    contextWindowTokens: config.aiContextWindowTokens,
    maxInputTokens: config.aiMaxInputTokens,
    reserveOutputTokens: config.aiReserveOutputTokens,
  }));
  return app;
}
