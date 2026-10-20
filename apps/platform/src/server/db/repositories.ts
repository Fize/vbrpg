import { sql, type Insertable, type Kysely, type Selectable, type Transaction } from "kysely";
import type { GameState } from "../../shared/index.js";
import type {
  Database,
  GameEventsTable,
  GameInstancesTable,
  GameParticipantsTable,
  JsonObject,
} from "./types.js";

export type DbExecutor = Kysely<Database> | Transaction<Database>;

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

/** Newest first. Every match is public: the lobby is where people find one to watch or join. */
export async function listGameInstances(
  db: DbExecutor,
  input: { limit?: number } = {},
): Promise<Array<Selectable<GameInstancesTable>>> {
  return db
    .selectFrom("game_instances")
    .selectAll()
    .orderBy("created_at", "desc")
    .limit(input.limit ?? 50)
    .execute();
}

/** Which of these matches the account holds a seat in, and under which key. */
export async function listSeatsForUser(
  db: DbExecutor,
  input: { userId: string; instanceIds: readonly string[] },
): Promise<Array<{ instance_id: string; participant_key: string }>> {
  if (input.instanceIds.length === 0) return [];
  return db
    .selectFrom("game_participants")
    .select(["instance_id", "participant_key"])
    .where("actor_user_id", "=", input.userId)
    .where("instance_id", "in", [...input.instanceIds])
    .orderBy("seat", "asc")
    .execute();
}

export async function createGameInstance(
  db: DbExecutor,
  input: {
    id: string;
    gameId: string;
    gameVersion: string;
    status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled";
    currentSequence: number;
    stateJson: JsonObject;
    /** The room this match is played at, when there is one. */
    roomId?: string;
  },
): Promise<void> {
  await db
    .insertInto("game_instances")
    .values({
      id: input.id,
      game_id: input.gameId,
      game_version: input.gameVersion,
      status: input.status,
      current_sequence: input.currentSequence,
      state_json: input.stateJson,
      ...(input.roomId === undefined ? {} : { room_id: input.roomId }),
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

/** Locks the match for the rest of the transaction: one writer at a time, per instance. */
export async function lockGameInstance(
  db: DbExecutor,
  instanceId: string,
): Promise<Selectable<GameInstancesTable> | undefined> {
  return db
    .selectFrom("game_instances")
    .selectAll()
    .where("id", "=", instanceId)
    .forUpdate()
    .executeTakeFirst();
}

/** Optimistic guard on top of the row lock: zero rows updated means somebody advanced first. */
export async function advanceGameInstance(
  db: DbExecutor,
  input: {
    instanceId: string;
    expectedSequence: number;
    state: GameState;
  },
): Promise<boolean> {
  const result = await db
    .updateTable("game_instances")
    .set({
      state_json: input.state as unknown as JsonObject,
      current_sequence: input.state.sequence,
      status: input.state.status,
      updated_at: new Date(),
      ...(input.state.status === "completed" ? { completed_at: new Date() } : {}),
    })
    .where("id", "=", input.instanceId)
    .where("current_sequence", "=", input.expectedSequence)
    .executeTakeFirst();
  return Number(result.numUpdatedRows ?? 0) > 0;
}

export async function insertGameParticipants(
  db: DbExecutor,
  rows: ReadonlyArray<Insertable<GameParticipantsTable>>,
): Promise<void> {
  if (rows.length === 0) return;
  await db
    .insertInto("game_participants")
    .values([...rows])
    .execute();
}

export async function listGameParticipants(
  db: DbExecutor,
  instanceId: string,
): Promise<Array<Selectable<GameParticipantsTable>>> {
  return db
    .selectFrom("game_participants")
    .selectAll()
    .where("instance_id", "=", instanceId)
    .orderBy("seat", "asc")
    .execute();
}

/** Seat status is denormalized from the state for queries and the pre-write check, so it follows it. */
export async function updateGameParticipantStatus(
  db: DbExecutor,
  instanceId: string,
  participantId: string,
  status: GameParticipantsTable["status"],
): Promise<void> {
  await db
    .updateTable("game_participants")
    .set({ status })
    .where("instance_id", "=", instanceId)
    .where("id", "=", participantId)
    .execute();
}

export async function insertGameEvent(
  db: DbExecutor,
  row: Insertable<GameEventsTable>,
): Promise<void> {
  await db.insertInto("game_events").values(row).execute();
}

export async function findEventByIdempotencyKey(
  db: DbExecutor,
  instanceId: string,
  idempotencyKey: string,
): Promise<Selectable<GameEventsTable> | undefined> {
  return db
    .selectFrom("game_events")
    .selectAll()
    .where("instance_id", "=", instanceId)
    .where("idempotency_key", "=", idempotencyKey)
    .executeTakeFirst();
}

/** The whole record, in order. No viewer filtering: whoever may read a match reads all of it. */
export async function listGameEvents(
  db: DbExecutor,
  instanceId: string,
): Promise<Array<Selectable<GameEventsTable>>> {
  return db
    .selectFrom("game_events")
    .selectAll()
    .where("instance_id", "=", instanceId)
    .orderBy("sequence", "asc")
    .execute();
}

/**
 * Takes the match's current AI turn for one worker. A lease that has not expired belongs to another
 * worker, and the caller must leave the turn alone — that is the whole point of the claim.
 */
export async function claimAiTurn(
  db: DbExecutor,
  input: { instanceId: string; workerId: string; leaseMs: number },
): Promise<boolean> {
  const now = new Date();
  const result = await db
    .updateTable("game_instances")
    .set({
      ai_claim_until: new Date(now.getTime() + input.leaseMs),
      ai_claim_worker: input.workerId,
    })
    .where("id", "=", input.instanceId)
    .where("status", "in", ["running", "waiting"])
    .where(({ eb, or }) => or([eb("ai_claim_until", "is", null), eb("ai_claim_until", "<", now)]))
    .executeTakeFirst();
  return Number(result.numUpdatedRows ?? 0) > 0;
}

/** Hands the turn back. Only the worker that claimed it may release it. */
export async function releaseAiTurn(
  db: DbExecutor,
  input: { instanceId: string; workerId: string },
): Promise<void> {
  await db
    .updateTable("game_instances")
    .set({ ai_claim_until: null, ai_claim_worker: null })
    .where("id", "=", input.instanceId)
    .where("ai_claim_worker", "=", input.workerId)
    .execute();
}

/**
 * Matches that have not moved for a while. `updated_at` is bumped on every advance, so an old
 * stamp on an active match means nobody — human or worker — has pushed it forward.
 */
export async function findIdleInstanceIds(
  db: DbExecutor,
  input: { cutoff: Date; limit: number },
): Promise<string[]> {
  const rows = await db
    .selectFrom("game_instances")
    .select("id")
    .where("status", "in", ["running", "waiting"])
    .where("updated_at", "<", input.cutoff)
    .orderBy("updated_at", "asc")
    .limit(input.limit)
    .execute();
  return rows.map((row) => row.id);
}

/**
 * Matches where a waiting point still expects an AI seat. The pending list lives in the state, so
 * the filter is a jsonb containment check rather than a scan followed by a filter in JavaScript.
 */
export async function findReadyAiSeats(
  db: DbExecutor,
  limit: number,
): Promise<Array<{ instanceId: string; participantId: string }>> {
  const result = await sql<{ instance_id: string; participant_id: string }>`
    select i.id as instance_id, p.id as participant_id
    from game_instances i
    join game_participants p
      on p.instance_id = i.id and p.control = 'ai' and p.status = 'active'
    where i.status in ('running', 'waiting')
      and i.state_json -> 'waiting' -> 'participantIds' ? p.id
    order by i.updated_at asc, p.seat asc
    limit ${limit}
  `.execute(db);
  return result.rows.map((row) => ({
    instanceId: row.instance_id,
    participantId: row.participant_id,
  }));
}
