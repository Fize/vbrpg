import type { Insertable, Selectable } from "kysely";
import type { RoomSeatPlanEntry } from "../../shared/index.js";
import type { Database, DbExecutor, RoomMembersTable, RoomsTable } from "./index.js";

/**
 * A room is the table: which game, which seats, who is sitting and who is ready. It outlives any
 * single match, so nothing about a running match is stored here — the current instance's status is
 * the only truth about that.
 */
export async function createRoom(
  db: DbExecutor,
  input: {
    id: string;
    gameId: string;
    gameVersion: string;
    ownerUserId: string;
    code: string;
    seatPlan: readonly RoomSeatPlanEntry[];
    personaPublic: boolean;
    variables: Record<string, unknown>;
  },
): Promise<void> {
  await db
    .insertInto("rooms")
    .values({
      id: input.id,
      game_id: input.gameId,
      game_version: input.gameVersion,
      owner_user_id: input.ownerUserId,
      code: input.code,
      status: "open",
      seat_plan: JSON.stringify(input.seatPlan),
      persona_public: input.personaPublic,
      variables: input.variables,
    })
    .execute();
}

export async function getRoom(
  db: DbExecutor,
  roomId: string,
): Promise<Selectable<RoomsTable> | undefined> {
  return db.selectFrom("rooms").selectAll().where("id", "=", roomId).executeTakeFirst();
}

export async function findRoomByCode(
  db: DbExecutor,
  code: string,
): Promise<Selectable<RoomsTable> | undefined> {
  return db.selectFrom("rooms").selectAll().where("code", "=", code).executeTakeFirst();
}

/** Locks a room for the rest of the transaction: one writer at a time, per room. */
export async function lockRoom(
  db: DbExecutor,
  roomId: string,
): Promise<Selectable<RoomsTable> | undefined> {
  return db.selectFrom("rooms").selectAll().where("id", "=", roomId).forUpdate().executeTakeFirst();
}

/** Open rooms are joinable by anyone; a closed one only shows up for the people already in it. */
export async function listRooms(
  db: DbExecutor,
  input: { userId: string; limit?: number },
): Promise<Array<Selectable<RoomsTable>>> {
  return (
    db
      .selectFrom("rooms")
      // Columns are named per table on purpose: a bare `selectAll()` across a join would let the
      // member row's `id` win over the room's, and every listed room would carry the wrong id.
      .selectAll("rooms")
      .leftJoin("room_members", "room_members.room_id", "rooms.id")
      .where((expression) =>
        expression.or([
          expression("rooms.status", "=", "open"),
          expression("room_members.user_id", "=", input.userId),
        ]),
      )
      .distinct()
      .orderBy("rooms.updated_at", "desc")
      .limit(input.limit ?? 50)
      .execute()
  );
}

export async function updateRoom(
  db: DbExecutor,
  roomId: string,
  patch: {
    seatPlan?: readonly RoomSeatPlanEntry[];
    personaPublic?: boolean;
    variables?: Record<string, unknown>;
    currentInstanceId?: string;
  },
): Promise<void> {
  await db
    .updateTable("rooms")
    .set({
      ...(patch.seatPlan === undefined ? {} : { seat_plan: JSON.stringify(patch.seatPlan) }),
      ...(patch.personaPublic === undefined ? {} : { persona_public: patch.personaPublic }),
      ...(patch.variables === undefined ? {} : { variables: patch.variables }),
      ...(patch.currentInstanceId === undefined
        ? {}
        : { current_instance_id: patch.currentInstanceId }),
      updated_at: new Date(),
    })
    .where("id", "=", roomId)
    .execute();
}

export async function setRoomStatus(
  db: DbExecutor,
  roomId: string,
  status: "open" | "closed" | "cancelled",
  ownerUserId?: string,
): Promise<void> {
  await db
    .updateTable("rooms")
    .set({
      status,
      ...(ownerUserId === undefined ? {} : { owner_user_id: ownerUserId }),
      ...(status === "open" ? {} : { closed_at: new Date() }),
      updated_at: new Date(),
    })
    .where("id", "=", roomId)
    .execute();
}

export async function listRoomMembers(
  db: DbExecutor,
  roomId: string,
): Promise<Array<Selectable<RoomMembersTable>>> {
  return db
    .selectFrom("room_members")
    .selectAll()
    .where("room_id", "=", roomId)
    .orderBy("seat", "asc")
    .execute();
}

export async function addRoomMember(
  db: DbExecutor,
  member: Insertable<RoomMembersTable>,
): Promise<void> {
  await db.insertInto("room_members").values(member).execute();
}

export async function removeRoomMember(
  db: DbExecutor,
  input: { roomId: string; userId?: string; seatKeys?: readonly string[] },
): Promise<void> {
  let query = db.deleteFrom("room_members").where("room_id", "=", input.roomId);
  if (input.userId !== undefined) query = query.where("user_id", "=", input.userId);
  if (input.seatKeys !== undefined) {
    if (input.seatKeys.length === 0) return;
    query = query.where("seat_key", "in", [...input.seatKeys]);
  }
  await query.execute();
}

export async function setRoomMemberReady(
  db: DbExecutor,
  input: { roomId: string; userId: string; ready: boolean },
): Promise<boolean> {
  const result = await db
    .updateTable("room_members")
    .set({ ready: input.ready })
    .where("room_id", "=", input.roomId)
    .where("user_id", "=", input.userId)
    .executeTakeFirst();
  return Number(result.numUpdatedRows ?? 0) > 0;
}

/** Ready is a statement about the next match, so starting one clears the table's answers. */
export async function clearRoomReadiness(db: DbExecutor, roomId: string): Promise<void> {
  await db
    .updateTable("room_members")
    .set({ ready: false })
    .where("room_id", "=", roomId)
    .execute();
}

/** Every match this table has played, newest first. */
export async function listRoomMatches(
  db: DbExecutor,
  roomId: string,
): Promise<Array<{ id: string; status: string; current_sequence: number; created_at: Date }>> {
  return db
    .selectFrom("game_instances")
    .select(["id", "status", "current_sequence", "created_at"])
    .where("room_id", "=", roomId)
    .orderBy("created_at", "desc")
    .execute() as Promise<
    Array<{ id: string; status: string; current_sequence: number; created_at: Date }>
  >;
}

export type { Database };
