import type { Kysely } from "kysely";
import { sql } from "kysely";
import type { Database } from "./db/index.js";
import { findIdleInstanceIds } from "./db/index.js";

/**
 * Latency lives in fixed buckets rather than raw samples: percentiles only need a bucket, and a
 * process that keeps every duration would grow without a ceiling.
 */
const LATENCY_BUCKETS_MS = [5, 10, 25, 50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000];
const STUCK_LIMIT = 500;
const DEFAULT_WINDOW_MS = 24 * 60 * 60 * 1_000;

export interface AiHealth {
  calls: number;
  failures: number;
  failureRate: number;
  tokens: { prompt: number; completion: number; total: number };
}

export interface MetricsSnapshot {
  now: string;
  windowMs: number;
  /** Actions submitted to the write path, timed from request arrival to the reply. */
  actions: {
    count: number;
    latencyMs: { p50: number | null; p90: number | null; p99: number | null };
  };
  http: { responses: number; serverErrors: number; errorRate: number };
  /** Absent without a database, which is what the route tests run with. */
  matches: { stuck: number; idleTimeoutMs: number } | null;
  ai: AiHealth | null;
}

export interface Metrics {
  observeAction(durationMs: number): void;
  observeResponse(statusCode: number): void;
  snapshot(): Promise<MetricsSnapshot>;
}

/** Model health over a window, straight from the record: no counters to drift out of sync. */
export async function readAiHealth(db: Kysely<Database>, windowMs: number): Promise<AiHealth> {
  const result = await sql<{
    calls: string;
    failures: string;
    prompt_tokens: string;
    completion_tokens: string;
    total_tokens: string;
  }>`
    select
      count(*) filter (where type = 'aiCall') as calls,
      count(*) filter (where type = 'aiFailed') as failures,
      coalesce(sum(prompt_tokens), 0) as prompt_tokens,
      coalesce(sum(completion_tokens), 0) as completion_tokens,
      coalesce(sum(total_tokens), 0) as total_tokens
    from game_events
    where occurred_at > now() - make_interval(secs => ${windowMs / 1_000})
  `.execute(db);

  const row = result.rows[0];
  const calls = Number(row?.calls ?? 0);
  const failures = Number(row?.failures ?? 0);
  return {
    calls,
    failures,
    failureRate: calls === 0 ? 0 : failures / calls,
    tokens: {
      prompt: Number(row?.prompt_tokens ?? 0),
      completion: Number(row?.completion_tokens ?? 0),
      total: Number(row?.total_tokens ?? 0),
    },
  };
}

/**
 * A quantile is answered with the upper bound of the bucket that holds it. Anything past the last
 * bucket reports null instead of a made-up number.
 */
function quantile(
  counts: readonly number[],
  overflow: number,
  quantileValue: number,
): number | null {
  const total = counts.reduce((sum, count) => sum + count, 0) + overflow;
  if (total === 0) return null;
  const target = Math.ceil(total * quantileValue);
  let seen = 0;
  for (const [index, count] of counts.entries()) {
    seen += count;
    if (seen >= target) return LATENCY_BUCKETS_MS[index] ?? null;
  }
  return null;
}

export function createMetrics(deps: {
  db?: Kysely<Database>;
  /** A match with no advance for this long counts as stuck. */
  idleMs: number;
  windowMs?: number;
}): Metrics {
  const windowMs = deps.windowMs ?? DEFAULT_WINDOW_MS;
  const buckets: number[] = LATENCY_BUCKETS_MS.map(() => 0);
  let overflow = 0;
  let actions = 0;
  let responses = 0;
  let serverErrors = 0;

  return {
    observeAction(durationMs) {
      actions += 1;
      const index = LATENCY_BUCKETS_MS.findIndex((upper) => durationMs <= upper);
      if (index === -1) overflow += 1;
      else buckets[index] = (buckets[index] ?? 0) + 1;
    },

    observeResponse(statusCode) {
      responses += 1;
      if (statusCode >= 500) serverErrors += 1;
    },

    async snapshot() {
      const base = {
        now: new Date().toISOString(),
        windowMs,
        actions: {
          count: actions,
          latencyMs: {
            p50: quantile(buckets, overflow, 0.5),
            p90: quantile(buckets, overflow, 0.9),
            p99: quantile(buckets, overflow, 0.99),
          },
        },
        http: {
          responses,
          serverErrors,
          errorRate: responses === 0 ? 0 : serverErrors / responses,
        },
      };
      const db = deps.db;
      if (!db) return { ...base, matches: null, ai: null };
      const stuck = await findIdleInstanceIds(db, {
        cutoff: new Date(Date.now() - deps.idleMs),
        limit: STUCK_LIMIT,
      });
      return {
        ...base,
        matches: { stuck: stuck.length, idleTimeoutMs: deps.idleMs },
        ai: await readAiHealth(db, windowMs),
      };
    },
  };
}
