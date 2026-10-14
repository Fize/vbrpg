import { createDb } from "@vbrpg/db";
import { createAiCommandHandler } from "@vbrpg/runtime";
import { createWorker } from "./worker.js";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} is required to run the worker`);
  }
  return value;
}

function optionalNumber(name: string): number | undefined {
  const value = process.env[name];
  if (value === undefined || value === "") return undefined;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive number`);
  }
  return parsed;
}

const maxTimeoutMs = optionalNumber("AI_TIMEOUT_MS");
const maxInputTokens = optionalNumber("AI_MAX_INPUT_TOKENS");
const contextWindowTokens = optionalNumber("AI_CONTEXT_WINDOW_TOKENS");

const db = createDb({ databaseUrl: requiredEnv("DATABASE_URL") });
const handleCommand = createAiCommandHandler(db, {
  credentialKeyEncoded: requiredEnv("PLATFORM_CREDENTIAL_KEY"),
  ...(maxTimeoutMs === undefined ? {} : { maxTimeoutMs }),
  ...(maxInputTokens === undefined ? {} : { maxInputTokens }),
  ...(contextWindowTokens === undefined ? {} : { contextWindowTokens }),
});

const worker = createWorker(
  {
    workerId: process.env.WORKER_ID ?? `worker-${process.pid}`,
    pollIntervalMs: Number(process.env.WORKER_POLL_INTERVAL_MS ?? 1_000),
    leaseMs: Number(process.env.WORKER_LEASE_MS ?? 30_000),
  },
  console,
  {
    db,
    handlers: {
      handleCommand: async (command) => {
        await handleCommand(command);
      },
    },
  },
);

let running = true;
process.on("SIGINT", () => {
  running = false;
});
process.on("SIGTERM", () => {
  running = false;
});

while (running) {
  try {
    await worker.runOnce();
  } catch (error) {
    console.error({ err: error }, "worker poll failed");
  }
  if (!running) break;
  await new Promise((resolve) => setTimeout(resolve, worker.config.pollIntervalMs));
}
