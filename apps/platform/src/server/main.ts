import { existsSync } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { FastifyInstance } from "fastify";
import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";
import { closeDb, createDb } from "./db/index.js";
import { createPlatformStore } from "./store.js";
import { createBuiltInRegistry } from "./games/index.js";
import { createMatchService } from "./match/service.js";
import { createAiSeatRunner } from "./match/ai-seat.js";
import { createWorker } from "./worker.js";

type Role = "api" | "worker" | "both";

/** One package, one image, two roles: `--role=api|worker|both`, default api. */
function parseRole(argv: readonly string[]): Role {
  const flag = argv.find((argument) => argument.startsWith("--role="));
  const value = flag?.slice("--role=".length) ?? "api";
  if (value !== "api" && value !== "worker" && value !== "both") {
    throw new Error(`Unknown role: ${value}`);
  }
  return value;
}

const CONTENT_TYPES: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

/** The browser bundle ships inside the same image, so the console is served same-origin. */
function registerStaticFiles(app: FastifyInstance, webRoot: string): void {
  app.get<{ Params: { "*": string } }>("/*", async (request, reply) => {
    const requested = decodeURIComponent(request.params["*"] ?? "");
    // API paths never fall back to the SPA entry point; they answer with the platform error shape.
    if (requested.startsWith("v1/")) {
      return reply.callNotFound();
    }

    const candidate = resolve(join(webRoot, normalize(requested)));
    if (!candidate.startsWith(webRoot)) {
      return reply.callNotFound();
    }

    try {
      const info = await stat(candidate);
      if (info.isFile()) {
        const type = CONTENT_TYPES[extname(candidate)] ?? "application/octet-stream";
        return reply.type(type).header("cache-control", "no-cache").send(await readFile(candidate));
      }
    } catch {
      // Not a file: fall through to the SPA entry point.
    }

    return reply
      .type(CONTENT_TYPES[".html"] ?? "text/html")
      .send(await readFile(join(webRoot, "index.html")));
  });
}

async function startHttp(databaseUrl: string | undefined): Promise<void> {
  const config = loadConfig();
  const db = databaseUrl === undefined ? undefined : createDb({ databaseUrl });
  const app = buildApp({
    config,
    ...(db
      ? {
        platformStore: createPlatformStore(db),
        matchService: createMatchService({ db, registry: createBuiltInRegistry() }),
      }
      : {}),
  });

  const webRoot = fileURLToPath(new URL("../browser", import.meta.url));
  if (existsSync(webRoot)) {
    registerStaticFiles(app, webRoot);
  }

  if (db) {
    app.addHook("onClose", async () => closeDb(db));
  }

  await app.listen({ host: "0.0.0.0", port: config.port });
}

async function startWorker(databaseUrl: string | undefined): Promise<void> {
  if (databaseUrl === undefined) {
    throw new Error("DATABASE_URL is required for the worker role");
  }
  const db = createDb({ databaseUrl });
  const config = loadConfig();
  const registry = createBuiltInRegistry();
  const credentialKey = config.credentialKey;
  if (!credentialKey) {
    throw new Error("PLATFORM_CREDENTIAL_KEY is required to run AI seats");
  }
  const runner = createAiSeatRunner({
    db,
    registry,
    service: createMatchService({ db, registry }),
    credentialKey,
  });
  const worker = createWorker(
    {
      workerId: process.env.WORKER_ID ?? `worker-${process.pid}`,
      pollIntervalMs: Number(process.env.WORKER_POLL_INTERVAL_MS ?? 1_000),
    },
    console,
    () => runner.runOnce(),
  );

  let running = true;
  const stop = (): void => {
    running = false;
  };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);

  while (running) {
    try {
      await worker.runOnce();
    } catch (error) {
      console.error({ err: error }, "worker poll failed");
    }
    if (!running) break;
    await new Promise((done) => setTimeout(done, worker.config.pollIntervalMs));
  }
  await closeDb(db);
}

const role = parseRole(process.argv.slice(2));
const databaseUrl = process.env.DATABASE_URL;

try {
  if (role === "api" || role === "both") {
    await startHttp(databaseUrl);
  }
  if (role === "worker" || role === "both") {
    await startWorker(databaseUrl);
  }
} catch (error) {
  console.error({ err: error }, "platform failed to start");
  process.exitCode = 1;
}
