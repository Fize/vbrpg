import { sql, type Kysely, type Selectable, type Transaction } from "kysely";
import type {
  Database,
  AuthSessionsTable,
  GameInstancesTable,
  JsonObject,
  OutboxEventsTable,
  PendingCommandsTable,
  PlayerActionsTable,
  ScheduledJobsTable,
} from "./types.js";

export interface TenantContext {
  tenantId: string;
}

export interface LeaseOptions extends TenantContext {
  workerId: string;
  limit?: number;
  leaseMs?: number;
  now?: Date;
}

export type DbExecutor = Kysely<Database> | Transaction<Database>;

export async function withTenantContext<T>(
  db: Kysely<Database>,
  context: TenantContext,
  callback: (transaction: Transaction<Database>) => Promise<T>,
): Promise<T> {
  return db.transaction().execute(async (transaction) => {
    await sql`select set_config('app.tenant_id', ${context.tenantId}, true)`.execute(transaction);
    return callback(transaction);
  });
}

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

export async function getGameInstance(
  db: DbExecutor,
  context: TenantContext,
  instanceId: string,
): Promise<Selectable<GameInstancesTable> | undefined> {
  return db
    .selectFrom("game_instances")
    .selectAll()
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", instanceId)
    .executeTakeFirst();
}

export async function getLatestSnapshot(
  db: DbExecutor,
  context: TenantContext,
  instanceId: string,
): Promise<{ sequence: number; state_json: JsonObject } | undefined> {
  return db
    .selectFrom("game_snapshots")
    .select(["sequence", "state_json"])
    .where("tenant_id", "=", context.tenantId)
    .where("instance_id", "=", instanceId)
    .orderBy("sequence", "desc")
    .executeTakeFirst();
}

export async function getActiveAuthSession(
  db: DbExecutor,
  context: TenantContext,
  sessionId: string,
  now = new Date(),
): Promise<Selectable<AuthSessionsTable> | undefined> {
  return db
    .selectFrom("auth_sessions")
    .selectAll()
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", sessionId)
    .where("revoked_at", "is", null)
    .where("expires_at", ">", now)
    .executeTakeFirst();
}

export async function getTenantMembership(
  db: DbExecutor,
  context: TenantContext,
  userId: string,
): Promise<Selectable<Database["tenant_memberships"]> | undefined> {
  return db
    .selectFrom("tenant_memberships")
    .selectAll()
    .where("tenant_id", "=", context.tenantId)
    .where("user_id", "=", userId)
    .executeTakeFirst();
}

export async function listActiveTenantIds(db: DbExecutor): Promise<string[]> {
  const rows = await db
    .selectFrom("tenants")
    .select("id")
    .where("status", "=", "active")
    .orderBy("id", "asc")
    .execute();
  return rows.map((row) => row.id);
}

export async function recordPlayerAction(
  db: DbExecutor,
  context: TenantContext,
  action: Omit<PlayerActionsTable, "created_at" | "processed_at" | "result_json" | "error_code"> & {
    result_json?: JsonObject | null;
    error_code?: string | null;
  },
): Promise<Selectable<PlayerActionsTable>> {
  const row = await db
    .insertInto("player_actions")
    .values({
      ...action,
      tenant_id: context.tenantId,
      result_json: action.result_json ?? null,
      error_code: action.error_code ?? null,
      processed_at: null,
    })
    .onConflict((conflict) =>
      conflict.columns(["tenant_id", "instance_id", "idempotency_key"]).doNothing(),
    )
    .returningAll()
    .executeTakeFirst();

  if (row) {
    return row;
  }

  const existing = await db
    .selectFrom("player_actions")
    .selectAll()
    .where("tenant_id", "=", context.tenantId)
    .where("instance_id", "=", action.instance_id)
    .where("idempotency_key", "=", action.idempotency_key)
    .executeTakeFirst();
  if (!existing) {
    throw new Error("Player action insert did not return a row");
  }
  return existing;
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
      .where("tenant_id", "=", options.tenantId)
      .where((expression) =>
        expression.or([
          expression("status", "=", "pending"),
          expression.and([
            expression("status", "=", "leased"),
            expression("lease_until", "<", now),
          ]),
        ]),
      )
      .where("available_at", "<=", now)
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
      .where("tenant_id", "=", options.tenantId)
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
      .where("tenant_id", "=", options.tenantId)
      .where((expression) =>
        expression.or([
          expression("status", "=", "scheduled"),
          expression.and([
            expression("status", "=", "leased"),
            expression("lease_until", "<", now),
          ]),
        ]),
      )
      .where("run_at", "<=", now)
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
      .where("tenant_id", "=", options.tenantId)
      .where("id", "in", rows.map((row) => row.id))
      .returningAll()
      .execute();
  });
}

export async function claimOutboxEvents(
  db: DbExecutor,
  options: LeaseOptions,
): Promise<Array<Selectable<OutboxEventsTable>>> {
  const limit = requirePositiveInteger(options.limit, 50);
  const leaseMs = requirePositiveInteger(options.leaseMs, 30_000);
  const now = options.now ?? new Date();
  const until = leaseUntil(now, leaseMs);

  return db.transaction().execute(async (transaction) => {
    const rows = await transaction
      .selectFrom("outbox_events")
      .selectAll()
      .where("tenant_id", "=", options.tenantId)
      .where("status", "in", ["pending", "failed"])
      .where((expression) =>
        expression.or([
          expression("lease_until", "is", null),
          expression("lease_until", "<", now),
        ]),
      )
      .where("available_at", "<=", now)
      .orderBy("available_at", "asc")
      .limit(limit)
      .forUpdate()
      .skipLocked()
      .execute();
    if (rows.length === 0) {
      return [];
    }

    return transaction
      .updateTable("outbox_events")
      .set({
        status: "leased",
        lease_until: until,
        leased_by: options.workerId,
        attempts: sql`attempts + 1`,
      })
      .where("tenant_id", "=", options.tenantId)
      .where("id", "in", rows.map((row) => row.id))
      .returningAll()
      .execute();
  });
}

export async function completeOutboxEvent(
  db: DbExecutor,
  context: TenantContext,
  eventId: string,
  workerId: string,
): Promise<void> {
  await db
    .updateTable("outbox_events")
    .set({ status: "published", published_at: new Date(), lease_until: null, leased_by: null })
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", eventId)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function releaseLease(
  db: DbExecutor,
  context: TenantContext,
  table: "pending_commands" | "scheduled_jobs" | "outbox_events",
  id: string,
  workerId: string,
  error?: string,
): Promise<void> {
  if (table === "outbox_events") {
    await db
      .updateTable("outbox_events")
      .set({ status: "pending", lease_until: null, leased_by: null, last_error: error ?? null })
      .where("tenant_id", "=", context.tenantId)
      .where("id", "=", id)
      .where("leased_by", "=", workerId)
      .execute();
    return;
  }

  await db
    .updateTable(table)
    .set({
      status: table === "pending_commands" ? "pending" : "scheduled",
      lease_until: null,
      leased_by: null,
      last_error: error ?? null,
    })
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", id)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function completePendingCommand(
  db: DbExecutor,
  context: TenantContext,
  commandId: string,
  workerId: string,
): Promise<void> {
  await db
    .updateTable("pending_commands")
    .set({ status: "completed", lease_until: null, leased_by: null, completed_at: new Date() })
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", commandId)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function completeScheduledJob(
  db: DbExecutor,
  context: TenantContext,
  jobId: string,
  workerId: string,
): Promise<void> {
  await db
    .updateTable("scheduled_jobs")
    .set({ status: "completed", lease_until: null, leased_by: null, completed_at: new Date() })
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", jobId)
    .where("leased_by", "=", workerId)
    .execute();
}

export async function failLeasedTask(
  db: DbExecutor,
  context: TenantContext,
  table: "pending_commands" | "scheduled_jobs" | "outbox_events",
  id: string,
  workerId: string,
  error: string,
  now = new Date(),
): Promise<void> {
  const row = await db
    .selectFrom(table)
    .select(["attempts", "max_attempts"])
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", id)
    .where("leased_by", "=", workerId)
    .executeTakeFirst();
  if (!row) return;
  const dead = row.attempts >= row.max_attempts;
  const retryAt = new Date(now.getTime() + Math.min(60_000, 2 ** Math.min(row.attempts, 10) * 1_000));
  if (table === "outbox_events") {
    await db
      .updateTable("outbox_events")
      .set({
        status: dead ? "dead" : "failed",
        available_at: retryAt,
        lease_until: null,
        leased_by: null,
        last_error: error,
      })
      .where("tenant_id", "=", context.tenantId)
      .where("id", "=", id)
      .where("leased_by", "=", workerId)
      .execute();
    return;
  }
  await db
    .updateTable(table)
    .set({
      status: dead ? "dead" : table === "pending_commands" ? "pending" : "scheduled",
      ...(table === "pending_commands" ? { available_at: retryAt } : { run_at: retryAt }),
      lease_until: null,
      leased_by: null,
      last_error: error,
    })
    .where("tenant_id", "=", context.tenantId)
    .where("id", "=", id)
    .where("leased_by", "=", workerId)
    .execute();
}
