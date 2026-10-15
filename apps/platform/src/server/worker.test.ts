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
    const worker = createWorker({ workerId: "test-worker", pollIntervalMs: 1000 }, logger);

    await expect(worker.runOnce()).resolves.toEqual({ processed: 0 });
    expect(logs).toEqual([{ workerId: "test-worker", processed: 0 }]);
  });

  it("reports what the injected tick did", async () => {
    const logs: Array<Record<string, unknown>> = [];
    const logger: WorkerLogger = { info(fields) { logs.push(fields); } };
    const worker = createWorker({ workerId: "test-worker", pollIntervalMs: 1000 }, logger, async () => ({
      turns: 2,
      failures: 1,
    }));

    await expect(worker.runOnce()).resolves.toEqual({ processed: 2 });
    expect(logs).toEqual([{ workerId: "test-worker", turns: 2, failures: 1 }]);
  });
});
