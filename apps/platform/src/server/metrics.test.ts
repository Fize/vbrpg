import { describe, expect, it } from "vitest";
import { createMetrics } from "./metrics.js";

describe("metrics", () => {
  it("answers percentiles from buckets and counts server errors", async () => {
    const metrics = createMetrics({ idleMs: 1_800_000 });
    // One sample per bucket: ≤5, ≤10, ≤25, ≤100, ≤1000.
    for (const ms of [3, 7, 20, 60, 900]) metrics.observeAction(ms);
    metrics.observeResponse(200);
    metrics.observeResponse(500);

    const snapshot = await metrics.snapshot();

    expect(snapshot.actions.count).toBe(5);
    expect(snapshot.actions.latencyMs).toEqual({ p50: 25, p90: 1_000, p99: 1_000 });
    expect(snapshot.http).toEqual({ responses: 2, serverErrors: 1, errorRate: 0.5 });
  });

  it("reports no latency at all when nothing has been timed", async () => {
    const snapshot = await createMetrics({ idleMs: 1_000 }).snapshot();

    expect(snapshot.actions).toEqual({ count: 0, latencyMs: { p50: null, p90: null, p99: null } });
    expect(snapshot.http.errorRate).toBe(0);
    // Without a database there is nothing to ask about matches or models.
    expect(snapshot.matches).toBeNull();
    expect(snapshot.ai).toBeNull();
  });

  it("keeps a slow tail out of the quantiles instead of guessing it", async () => {
    const metrics = createMetrics({ idleMs: 1_000 });
    metrics.observeAction(60_000);

    const snapshot = await metrics.snapshot();

    expect(snapshot.actions.count).toBe(1);
    expect(snapshot.actions.latencyMs.p50).toBeNull();
  });
});
