import { describe, expect, it } from "vitest";
import { createWorker, type WorkerLogger } from "./worker.js";

describe("worker foundation", () => {
  it("runs an empty poll without treating memory as authoritative state", async () => {
    const logs: Array<Record<string, unknown>> = [];
    const logger: WorkerLogger = {
      info(fields) {
        logs.push(fields);
      },
    };
    const worker = createWorker({ workerId: "test-worker", pollIntervalMs: 1000, leaseMs: 30_000 }, logger);

    await expect(worker.runOnce()).resolves.toEqual({ claimed: 0, processed: 0 });
    expect(logs).toEqual([{ workerId: "test-worker", claimed: 0, processed: 0 }]);
  });
});
