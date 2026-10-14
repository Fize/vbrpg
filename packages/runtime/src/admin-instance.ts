import { parseGameEvent } from "@vbrpg/contracts";
import { setInstanceStatus } from "@vbrpg/db";
import type { Database, JsonObject, TenantContext } from "@vbrpg/db";
import type { Kysely } from "kysely";
import { dispatchGameEvent } from "./game-dispatch.js";
import { loadInstanceWithDefinition } from "./instance-loader.js";

const TERMINAL = new Set(["completed", "cancelled"]);

export type AdminInstanceAction = "paused" | "resumed" | "cancelled" | "rejected";

/** Lifecycle changes are platform state, not game events: they never enter the event log. */
export async function pauseInstance(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
): Promise<AdminInstanceAction> {
  const loaded = await loadInstanceWithDefinition(db, context, instanceId);
  if (!loaded) return "rejected";
  if (TERMINAL.has(loaded.state.status)) return "rejected";
  if (loaded.state.status === "paused") return "paused";
  await setInstanceStatus(db, context, instanceId, "paused");
  return "paused";
}

export async function resumeInstance(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
): Promise<AdminInstanceAction> {
  const loaded = await loadInstanceWithDefinition(db, context, instanceId);
  if (!loaded) return "rejected";
  if (loaded.state.status !== "paused") return "rejected";
  // Queued work was never consumed while paused, so the instance simply becomes claimable again.
  await setInstanceStatus(db, context, instanceId, loaded.state.waiting === null ? "running" : "waiting");
  return "resumed";
}

export async function cancelInstance(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
): Promise<AdminInstanceAction> {
  const loaded = await loadInstanceWithDefinition(db, context, instanceId);
  if (!loaded) return "rejected";
  if (TERMINAL.has(loaded.state.status)) return "rejected";
  await setInstanceStatus(db, context, instanceId, "cancelled");
  return "cancelled";
}

export interface ForceTimeoutResult {
  outcome: "completed" | "duplicate" | "skipped";
  reason?: string;
}

/**
 * Ends the current wait without waiting for its clock: timers fire immediately and AI
 * nodes take their declared fallback. Player input has no timeout semantics yet.
 */
export async function forceInstanceTimeout(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
): Promise<ForceTimeoutResult> {
  const loaded = await loadInstanceWithDefinition(db, context, instanceId);
  if (!loaded) return { outcome: "skipped", reason: "INSTANCE_NOT_FOUND" };
  const waiting = loaded.state.waiting;
  if (!waiting) return { outcome: "skipped", reason: "INSTANCE_NOT_WAITING" };
  if (waiting.kind !== "timer" && waiting.kind !== "ai") {
    return { outcome: "skipped", reason: `NOT_TIMEOUTABLE: ${waiting.kind}` };
  }

  const isTimer = waiting.kind === "timer";
  const event = parseGameEvent({
    eventId: `${instanceId}:${waiting.nodeId}:${loaded.currentSequence + 1}:admin-timeout`,
    instanceId,
    sequence: loaded.currentSequence + 1,
    type: isTimer ? "timerExpired" : "aiFailed",
    actor: null,
    occurredAtMs: Date.now(),
    idempotencyKey: `${instanceId}:${waiting.nodeId}:admin-timeout`,
    payload: isTimer ? { nodeId: waiting.nodeId } : { reason: "ADMIN_FORCE_TIMEOUT" },
  });

  const result = await dispatchGameEvent(db, context, loaded.compiled, event);
  return { outcome: result.replayed ? "duplicate" : "completed" };
}

async function countForInstance(
  db: Kysely<Database>,
  context: TenantContext,
  table: "game_events" | "pending_commands" | "scheduled_jobs",
  instanceId: string,
): Promise<number> {
  const row = await db
    .selectFrom(table)
    .select((expression) => expression.fn.countAll<number>().as("total"))
    .where("tenant_id", "=", context.tenantId)
    .where("instance_id", "=", instanceId)
    .executeTakeFirst();
  return Number(row?.total ?? 0);
}

export interface AdminInstanceView {
  instanceId: string;
  gameVersionId: string;
  engineVersion: string;
  status: string;
  currentSequence: number;
  currentNodeId: string;
  waiting: { kind: string; nodeId: string; participantIds: string[]; deadlineMs?: number } | null;
  participants: { total: number; byRole: Record<string, number>; byStatus: Record<string, number> };
  /** Variable names only: an operator gets structure, never hidden values. */
  variableKeys: string[];
  counts: { events: number; pendingCommands: number; scheduledJobs: number };
}

export async function describeInstance(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
): Promise<AdminInstanceView | undefined> {
  const loaded = await loadInstanceWithDefinition(db, context, instanceId);
  if (!loaded) return undefined;
  const { state } = loaded;

  const [events, pendingCommands, scheduledJobs] = await Promise.all([
    countForInstance(db, context, "game_events", instanceId),
    countForInstance(db, context, "pending_commands", instanceId),
    countForInstance(db, context, "scheduled_jobs", instanceId),
  ]);

  const byRole: Record<string, number> = {};
  const byStatus: Record<string, number> = {};
  for (const participant of state.participants) {
    const role = participant.roleId ?? "unassigned";
    byRole[role] = (byRole[role] ?? 0) + 1;
    byStatus[participant.status] = (byStatus[participant.status] ?? 0) + 1;
  }

  const waiting = state.waiting;
  return {
    instanceId: state.instanceId,
    gameVersionId: state.gameVersionId,
    engineVersion: state.engineVersion,
    status: state.status,
    currentSequence: loaded.currentSequence,
    currentNodeId: state.currentNodeId,
    waiting:
      waiting === null
        ? null
        : {
          kind: waiting.kind,
          nodeId: waiting.nodeId,
          participantIds: [...waiting.participantIds],
          ...(waiting.deadlineMs === undefined ? {} : { deadlineMs: waiting.deadlineMs }),
        },
    participants: { total: state.participants.length, byRole, byStatus },
    variableKeys: Object.keys(state.variables).sort(),
    counts: { events, pendingCommands, scheduledJobs },
  };
}
