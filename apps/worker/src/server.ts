import { createWorker } from "./worker.js";

const worker = createWorker({
  workerId: process.env.WORKER_ID ?? `worker-${process.pid}`,
  pollIntervalMs: Number(process.env.WORKER_POLL_INTERVAL_MS ?? 1_000),
  leaseMs: Number(process.env.WORKER_LEASE_MS ?? 30_000),
});

const poll = async () => {
  await worker.runOnce();
};

await poll();
setInterval(poll, worker.config.pollIntervalMs);
