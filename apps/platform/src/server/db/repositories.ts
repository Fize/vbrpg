import { sql, type Kysely, type Selectable, type Transaction } from "kysely";
import type {
  Database,
  GameInstancesTable,
  JsonObject,
  PendingCommandsTable,
  ScheduledJobsTable,
} from "./types.js";

export interface LeaseOptions {
  workerId: string;
  limit?: number;
  leaseMs?: number;
  now?: Date;
}

export type DbExecutor = Kysely<Database> | Transaction<Database>;

function requirePositiveInteger(value: number | undefined, fallback: number): number {
  const resolved = value ?? fallback;
  if (!Number.isInteger(resolved) || resolved <= 0) {
    throw new Error("Lease limit and duration must be positive integers");
  }
  return resolved;
}

function leaseUntil(now: Date, leaseMs: number): Date {
  return new Date(now.getTime() + leaseMs);
}

/**
 * `available_at` and `run_at` default to the database clock, so claims must be compared against
 * the same clock. A worker host whose clock runs slightly behind Postgres would otherwise skip
 * every row it just queued and only pick it up on a later poll.
 */
const databaseNow = sql<Date>`now()`;

export async function getGameInstance(
  db: DbExecutor,
  instanceId: string,
): Promise<Selectable<GameInstancesTable> | undefined> {
  return db
    .selectFrom("game_instances")
    .selectAll()
    .where("id", "=", instanceId)
    .executeTakeFirst();
}

export async function createGameInstance(
  db: DbExecutor,
  input: {
    id: string;
    gameVersionId: string;
    status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled";
    currentSequence: number;
    stateJson: JsonObject;
  },
): Promise<void> {
  await db
    .insertInto("game_instances")
    .values({
      id: input.id,
      game_version_id: input.gameVersionId,
      status: input.status,
      current_sequence: input.currentSequence,
      state_json: input.stateJson,
    })
    .execute();
}

/** Platform-level lifecycle change: pause, resume, cancel. Never a game event. */
export async function setInstanceStatus(
  db: DbExecutor,
  instanceId: string,
  status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled",
): Promise<boolean> {
  const result = await db
    .updateTable("game_instances")
    .set({ status, updated_at: new Date() })
    .where("id", "=", instanceId)
    .executeTakeFirst();
  return Number(result.numUpdatedRows ?? 0) > 0;
}

export async function getLatestSnapshot(
  db: DbExecutor,
  instanceId: string,
): Promise<{ sequence: number; state_json: JsonObject } | undefined> {
  return db
    .selectFrom("game_snapshots")
    .select(["sequence", "state_json"])
    .where("instance_id", "=", instanceId)
    .orderBy("sequence", "desc")
    .limit(1)
    .executeTakeFirst();
}

export async function claimPendingCommands(
  db: DbExecutor,
  options: LeaseOptions,
): Promise<Array<Selectable<PendingCommandsTable>>> {
  const limit = requirePositiveInteger(options.limit, 50);
  const leaseMs = requirePositiveInteger(options.leaseMs, 30_000);
  const now = options.now ?? new Date();
  const until = leaseUntil(now, leaseMs);

  return db.transaction().execute(async (transaction) => {
    const rows = await transaction
      .selectFrom("pending_commands")
      .selectAll()
      .where((expression) =>
        expression.or([
          expression("status", "=", "pending"),
          expression.and([
            expression("status", "=", "leased"),
            expression("lease_until", "<", now),
          ]),
        ]),
      )
      // Paused, cancelled and finished instances keep their work queued instead of
      // consuming it: resuming simply makes the same rows claimable again.
      .where((expression) =>
        expression(
          "instance_id",
          "in",
          expression
            .selectFrom("game_instances")
            .select("id")
            .where("game_instances.status", "in", ["created", "running", "waiting"]),
        ),
      )
      .where("available_at", "<=", databaseNow)
      .orderBy("available_at", "asc")
      .limit(limit)
      .forUpdate()
      .skipLocked()
      .execute();
    if (rows.length === 0) {
      return [];
    }

    const ids = rows.map((row) => row.id);
    const claimed = await transaction
      .updateTable("pending_commands")
      .set({
        status: "leased",
        lease_until: until,
        leased_by: options.workerId,
        attempts: sql`attempts + 1`,
      })
      .where("id", "in", ids)
      .returningAll()
      .execute();
    return claimed;
  });
}

export async function claimScheduledJobs(
  db: DbExecutor,
  options: LeaseOptions,
): Promise<Array<Selectable<ScheduledJobsTable>>> {
  const limit = requirePositiveInteger(options.limit, 50);
  const leaseMs = requirePositiveInteger(options.leaseMs, 30_000);
  const now = options.now ?? new Date();
  const until = leaseUntil(now, leaseMs);

  return db.transaction().execute(async (transaction) => {
    const rows = await transaction
      .selectFrom("scheduled_jobs")
      .selectAll()
      .where((expression) =>
        expression.or([
          expression("status", "=", "scheduled"),
          expression.and([
            expression("status", "=", "leased"),
            expression("lease_until", "<", now),
          ]),
        ]),
      )
      // Same rule as commands: work for a paused or finished match stays queued. A job with no
      // instance belongs to no match and is always claimable.
      .where((expression) =>
        expression.or([
          expression("instance_id", "is", null),
          expression(
            "instance_id",
            "in",
            expression
              .selectFrom("game_instances")
              .select("id")
              .where("game_instances.status", "in", ["created", "running", "waiting"]),
          ),
        ]),
      )
      .where("run_at", "<=", databaseNow)
      .orderBy("run_at", "asc")
      .limit(limit)
      .forUpdate()
      .skipLocked()
      .execute();
    if (rows.length === 0) {
      return [];
    }

    return transaction
      .updateTable("scheduled_jobs")
      .set({
        status: "leased",
        lease_until: until,
        leased_by: options.workerId,
        attempts: sql`attempts + 1`,
      })
      .where("id", "in", rows.map((row) => row.id))
      .returningAll()
      .execute();
  });
}

export async function releaseLease(
  db: DbExecutor,
  table: "pending_commands" | "scheduled_jobs",
  id: string,
  workerId: string,
  error?: string,
): Promise<void> {
  await db
    .updateTable(table)
    .set({
      status: table === "pending_commands" ? "pending" : "scheduled",
      lease_until: null,
      leased_by: null,
      last_error: error ?? null,
    })
    .where("id", "=", id)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function completePendingCommand(
  db: DbExecutor,
  commandId: string,
  workerId: string,
): Promise<void> {
  await db
    .updateTable("pending_commands")
    .set({ status: "completed", lease_until: null, leased_by: null, completed_at: new Date() })
    .where("id", "=", commandId)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function completeScheduledJob(
  db: DbExecutor,
  jobId: string,
  workerId: string,
): Promise<void> {
  await db
    .updateTable("scheduled_jobs")
    .set({ status: "completed", lease_until: null, leased_by: null, completed_at: new Date() })
    .where("id", "=", jobId)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function failLeasedTask(
  db: DbExecutor,
  table: "pending_commands" | "scheduled_jobs",
  id: string,
  workerId: string,
  error: string,
  now = new Date(),
): Promise<void> {
  const row = await db
    .selectFrom(table)
    .select(["attempts", "max_attempts"])
    .where("id", "=", id)
    .where("leased_by", "=", workerId)
    .executeTakeFirst();
  if (!row) return;
  const dead = row.attempts >= row.max_attempts;
  const retryAt = new Date(now.getTime() + Math.min(60_000, 2 ** Math.min(row.attempts, 10) * 1_000));
  await db
    .updateTable(table)
    .set({
      status: dead ? "dead" : table === "pending_commands" ? "pending" : "scheduled",
      ...(table === "pending_commands" ? { available_at: retryAt } : { run_at: retryAt }),
      lease_until: null,
      leased_by: null,
      last_error: error,
    })
    .where("id", "=", id)
    .where("leased_by", "=", workerId)
    .execute();
}
