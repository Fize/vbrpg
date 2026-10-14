import { parseGameEvent, type GameEvent } from "@vbrpg/contracts";
import type { Kysely } from "kysely";
import type { Database } from "@vbrpg/db";
import { dispatchGameEvent } from "./game-dispatch.js";
import { loadInstanceWithDefinition, RuntimeTaskError } from "./instance-loader.js";

export interface ClaimedScheduledJob {
  id: string;
  tenant_id: string;
  instance_id: string | null;
  job_key: string;
  job_type: string;
  payload: unknown;
  attempts: number;
  max_attempts: number;
}

export type ScheduledJobOutcome = "completed" | "duplicate" | "skipped";

export interface ScheduledJobResult {
  outcome: ScheduledJobOutcome;
  reason?: string;
}

/**
 * Fires an expired timer back into the instance. The waiting node comes from the
 * instance state, never from the job payload, so a stale job cannot advance a
 * workflow that has already moved on.
 */
export async function runScheduledJob(
  db: Kysely<Database>,
  context: { tenantId: string },
  job: ClaimedScheduledJob,
  now: () => Date = () => new Date(),
): Promise<ScheduledJobResult> {
  if (job.job_type !== "timerExpired") {
    return { outcome: "skipped", reason: `UNSUPPORTED_JOB: ${job.job_type}` };
  }
  if (job.instance_id === null) {
    return { outcome: "skipped", reason: "JOB_HAS_NO_INSTANCE" };
  }

  const loaded = await loadInstanceWithDefinition(db, context, job.instance_id);
  if (!loaded) {
    return { outcome: "skipped", reason: "INSTANCE_NOT_FOUND" };
  }
  if (loaded.state.waiting?.kind !== "timer") {
    return { outcome: "skipped", reason: "INSTANCE_NOT_WAITING_FOR_TIMER" };
  }

  const nodeId = loaded.state.waiting.nodeId;
  const event: GameEvent = parseGameEvent({
    eventId: `${loaded.state.instanceId}:${nodeId}:${loaded.currentSequence + 1}:timer`,
    instanceId: loaded.state.instanceId,
    sequence: loaded.currentSequence + 1,
    type: "timerExpired",
    actor: null,
    occurredAtMs: now().getTime(),
    idempotencyKey: `${loaded.state.instanceId}:${nodeId}:timer-expired`,
    payload: { nodeId },
  });

  const result = await dispatchGameEvent(db, context, loaded.compiled, event);
  return { outcome: result.replayed ? "duplicate" : "completed" };
}

export function createScheduledJobHandler(
  db: Kysely<Database>,
): (job: ClaimedScheduledJob) => Promise<ScheduledJobResult> {
  return async (job) => {
    if (typeof job.tenant_id !== "string" || job.tenant_id === "") {
      throw new RuntimeTaskError("TENANT_MISSING", "Claimed job carries no tenant id");
    }
    return runScheduledJob(db, { tenantId: job.tenant_id }, job);
  };
}
