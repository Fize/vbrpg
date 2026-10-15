import { createDb } from "@vbrpg/db";
import { createWorker } from "./worker.js";

const databaseUrl = process.env.DATABASE_URL;
if (databaseUrl === undefined || databaseUrl === "") {
  throw new Error("DATABASE_URL is required to run the worker");
}
const db = createDb({ databaseUrl });

// No game handlers yet: the poll loop, leases and outbox stay, the work itself arrives
// with the code-based game packaging.
const worker = createWorker(
  {
    workerId: process.env.WORKER_ID ?? `worker-${process.pid}`,
    pollIntervalMs: Number(process.env.WORKER_POLL_INTERVAL_MS ?? 1_000),
    leaseMs: Number(process.env.WORKER_LEASE_MS ?? 30_000),
  },
  console,
  { db, handlers: {} },
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
