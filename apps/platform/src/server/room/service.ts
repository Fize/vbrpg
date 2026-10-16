import { randomInt, randomUUID } from "node:crypto";
import type { Kysely } from "kysely";
import type {
  CreateRoomRequest,
  MatchSummary,
  RoomDetail,
  RoomSeat,
  RoomSeatPlanEntry,
  RoomSummary,
  UpdateRoomRequest,
} from "../../shared/index.js";
import {
  addRoomMember,
  findRoomByCode,
  clearRoomReadiness,
  createRoom,
  getPlatformUser,
  getRoom,
  listPlatformUsersByIds,
  listRoomMatches,
  listRoomMembers,
  listRooms,
  lockRoom,
  removeRoomMember,
  setRoomMemberReady,
  setRoomStatus,
  updateRoom,
  type Database,
} from "../db/index.js";
import type { GameModule, GameRegistry } from "../game/index.js";
import { AppError } from "../runtime/index.js";
import type { MatchService } from "../match/service.js";

const MAX_ROOMS_LISTED = 50;

/** No 0/O/1/I: a room code gets read out loud and typed by somebody else. */
const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

function generateRoomCode(): string {
  let code = "";
  for (let index = 0; index < 6; index += 1) {
    code += CODE_ALPHABET[randomInt(CODE_ALPHABET.length)];
  }
  return code;
}

function isUniqueViolation(error: unknown): boolean {
  return (
    typeof error === "object" && error !== null && (error as { code?: string }).code === "23505"
  );
}

export interface RoomActor {
  userId: string;
  isAdmin: boolean;
}

export interface RoomMatchRow {
  instanceId: string;
  status: string;
  sequence: number;
  createdAt: string;
}

/** A room row as the repositories return it, kept minimal so the service can be tested alone. */
interface RoomRow {
  id: string;
  game_id: string;
  game_version: string;
  owner_user_id: string;
  code: string;
  status: "open" | "closed" | "cancelled";
  seat_plan: RoomSeatPlanEntry[];
  persona_public: boolean;
  variables: Record<string, unknown>;
  current_instance_id: string | null;
  created_at: Date;
}

export interface RoomService {
  create(input: { actor: RoomActor; request: CreateRoomRequest }): Promise<RoomDetail>;
  list(input: { actor: RoomActor }): Promise<RoomSummary[]>;
  read(input: { actor: RoomActor; roomId: string }): Promise<RoomDetail>;
  update(input: {
    actor: RoomActor;
    roomId: string;
    patch: UpdateRoomRequest;
  }): Promise<RoomDetail>;
  join(input: { actor: RoomActor; roomId: string }): Promise<RoomDetail>;
  /** The same, for the six characters somebody read out loud. */
  joinByCode(input: { actor: RoomActor; code: string }): Promise<RoomDetail>;
  setReady(input: { actor: RoomActor; roomId: string; ready: boolean }): Promise<RoomDetail>;
  leave(input: { actor: RoomActor; roomId: string }): Promise<RoomDetail>;
  /** The owner's one act that can spend money: it deals a match, and may call the model for words. */
  start(input: { actor: RoomActor; roomId: string }): Promise<{ summary: MatchSummary }>;
  close(input: { actor: RoomActor; roomId: string }): Promise<RoomDetail>;
  matches(input: { actor: RoomActor; roomId: string }): Promise<RoomMatchRow[]>;
}

/**
 * Rooms are the table; matches are the rounds played at it. Nothing about a running match is stored
 * on the room — whether one is running is read from the current instance's status — so a room can
 * host one match after another without any state to reconcile.
 */
export function createRoomService(options: {
  db: Kysely<Database>;
  registry: GameRegistry;
  matchService: MatchService;
}): RoomService {
  const { db, registry, matchService } = options;

  function requireGame(gameId: string): GameModule {
    const game = registry.get(gameId);
    if (!game) throw new AppError(404, "UNKNOWN_GAME", `No game is registered under ${gameId}`);
    return game;
  }

  /** A room may not hold a table the game cannot play. */
  function checkSeatPlan(game: GameModule, plan: readonly RoomSeatPlanEntry[]): void {
    if (plan.length < game.minSeats || plan.length > game.maxSeats) {
      throw new AppError(
        400,
        "SEATS_OUT_OF_RANGE",
        `${game.title} is played with ${game.minSeats}-${game.maxSeats} seats`,
      );
    }
    if (new Set(plan.map((seat) => seat.key)).size !== plan.length) {
      throw new AppError(400, "DUPLICATE_SEAT_KEY", "Seat keys must be unique");
    }
    if (!plan.some((seat) => seat.control === "human")) {
      throw new AppError(400, "NO_HUMAN_SEAT", "A room needs at least one human seat");
    }
  }

  async function isPlaying(room: RoomRow): Promise<boolean> {
    if (room.current_instance_id === null) return false;
    const row = await db
      .selectFrom("game_instances")
      .select(["status"])
      .where("id", "=", room.current_instance_id)
      .executeTakeFirst();
    return row !== undefined && row.status !== "completed" && row.status !== "cancelled";
  }

  /** The plan with whoever is sitting in it: the shape a room page renders. */
  async function seatsOf(input: { room: RoomRow; viewerId: string }): Promise<RoomSeat[]> {
    const members = await listRoomMembers(db, input.room.id);
    const usernames =
      members.length === 0
        ? new Map<string, string>()
        : new Map(
            (
              await listPlatformUsersByIds(
                db,
                members.map((member) => member.user_id),
              )
            ).map((user) => [user.id, user.username]),
          );
    const bySeat = new Map(members.map((member) => [member.seat_key, member]));

    return input.room.seat_plan.map((seat, index) => {
      const member = bySeat.get(seat.key);
      return {
        key: seat.key,
        seat: index + 1,
        control: seat.control,
        userId: member?.user_id ?? null,
        username: member === undefined ? null : (usernames.get(member.user_id) ?? null),
        ready: member?.ready ?? false,
        isMe: member?.user_id === input.viewerId,
      };
    });
  }

  function summaryOf(input: {
    room: RoomRow;
    game: GameModule;
    seats: readonly RoomSeat[];
    viewer: RoomActor;
    playing: boolean;
  }): RoomSummary {
    const { room, seats } = input;
    return {
      roomId: room.id,
      code: room.code,
      gameId: room.game_id,
      gameTitle: input.game.title,
      gameVersion: room.game_version,
      status: room.status,
      playing: input.playing,
      currentInstanceId: room.current_instance_id,
      ownerUserId: room.owner_user_id,
      isOwner: room.owner_user_id === input.viewer.userId,
      mySeatKeys: seats.filter((seat) => seat.isMe).map((seat) => seat.key),
      seats: seats.length,
      humanSeats: seats.filter((seat) => seat.control === "human").length,
      aiSeats: seats.filter((seat) => seat.control === "ai").length,
      takenSeats: seats.filter((seat) => seat.userId !== null).length,
      readySeats: seats.filter((seat) => seat.userId !== null && seat.ready).length,
      personaPublic: room.persona_public,
      createdAt: room.created_at.toISOString(),
    };
  }

  async function requireRoom(roomId: string): Promise<RoomRow> {
    const room = await getRoom(db, roomId);
    if (!room) throw new AppError(404, "ROOM_NOT_FOUND", "No such room");
    return room as unknown as RoomRow;
  }

  async function detailOf(input: { actor: RoomActor; roomId: string }): Promise<RoomDetail> {
    const room = await requireRoom(input.roomId);
    const game = requireGame(room.game_id);
    const seats = await seatsOf({ room, viewerId: input.actor.userId });
    return {
      ...summaryOf({ room, game, seats, viewer: input.actor, playing: await isPlaying(room) }),
      seatPlan: seats,
      variables: room.variables,
    };
  }

  /** Seating a member is one operation, whether the caller found the room by id or by its code. */
  async function joinRoom(actor: RoomActor, roomId: string): Promise<RoomDetail> {
    await db.transaction().execute(async (transaction) => {
      const locked = await lockRoom(transaction, roomId);
      if (!locked) throw new AppError(404, "ROOM_NOT_FOUND", "No such room");
      const room = locked as unknown as RoomRow;
      if (room.status !== "open") throw new AppError(409, "ROOM_CLOSED", "This room is closed");
      if (await isPlaying(room)) {
        throw new AppError(409, "ROOM_BUSY", "A match of this room is still running");
      }

      const members = await listRoomMembers(transaction, roomId);
      if (members.some((member) => member.user_id === actor.userId)) {
        throw new AppError(409, "ALREADY_SEATED", "You are already sitting in this room");
      }
      const taken = new Set(members.map((member) => member.seat_key));
      const index = room.seat_plan.findIndex(
        (seat) => seat.control === "human" && !taken.has(seat.key),
      );
      if (index < 0) throw new AppError(409, "ROOM_FULL", "Every human seat is taken");
      const seat = room.seat_plan[index] as RoomSeatPlanEntry;

      await addRoomMember(transaction, {
        id: randomUUID(),
        room_id: roomId,
        user_id: actor.userId,
        seat_key: seat.key,
        seat: index + 1,
        ready: false,
      });
    });
    return detailOf({ actor, roomId });
  }

  return {
    async create({ actor, request }) {
      const game = requireGame(request.gameId);
      checkSeatPlan(game, request.seats);
      const owner = await getPlatformUser(db, actor.userId);
      if (!owner) throw new AppError(401, "ACCOUNT_MISSING", "The account no longer exists");

      const roomId = randomUUID();
      const ownerSeatIndex = request.seats.findIndex((seat) => seat.control === "human");
      const ownerSeat = request.seats[ownerSeatIndex] as RoomSeatPlanEntry;

      // A code collision is a retry, not an error: the space is large and the constraint is the truth.
      for (let attempt = 0; attempt < 5; attempt += 1) {
        try {
          await db.transaction().execute(async (transaction) => {
            await createRoom(transaction, {
              id: roomId,
              gameId: game.id,
              gameVersion: game.version,
              ownerUserId: actor.userId,
              code: generateRoomCode(),
              seatPlan: request.seats,
              personaPublic: request.personaPublic ?? false,
              variables: request.variables ?? {},
            });
            // The owner sits down first: a table with nobody in it is a table nobody can start.
            await addRoomMember(transaction, {
              id: randomUUID(),
              room_id: roomId,
              user_id: actor.userId,
              seat_key: ownerSeat.key,
              seat: ownerSeatIndex + 1,
              ready: false,
            });
          });
          return detailOf({ actor, roomId });
        } catch (error) {
          if (!isUniqueViolation(error)) throw error;
        }
      }
      throw new AppError(500, "ROOM_CODE_UNAVAILABLE", "Could not find a free room code");
    },

    async list({ actor }) {
      const rooms = (await listRooms(db, {
        userId: actor.userId,
        limit: MAX_ROOMS_LISTED,
      })) as unknown as RoomRow[];
      const summaries: RoomSummary[] = [];
      for (const room of rooms) {
        const seats = await seatsOf({ room, viewerId: actor.userId });
        summaries.push(
          summaryOf({
            room,
            game: requireGame(room.game_id),
            seats,
            viewer: actor,
            playing: await isPlaying(room),
          }),
        );
      }
      return summaries;
    },

    read: detailOf,

    async update({ actor, roomId, patch }) {
      await db.transaction().execute(async (transaction) => {
        const locked = await lockRoom(transaction, roomId);
        if (!locked) throw new AppError(404, "ROOM_NOT_FOUND", "No such room");
        const room = locked as unknown as RoomRow;
        if (room.owner_user_id !== actor.userId) {
          throw new AppError(403, "NOT_ROOM_OWNER", "Only the room's owner may change it");
        }
        if (room.status !== "open") throw new AppError(409, "ROOM_CLOSED", "This room is closed");
        if (await isPlaying(room)) {
          throw new AppError(409, "ROOM_BUSY", "A match of this room is still running");
        }

        const plan = patch.seats ?? room.seat_plan;
        if (patch.seats !== undefined) checkSeatPlan(requireGame(room.game_id), patch.seats);

        const members = await listRoomMembers(transaction, roomId);
        const kept = new Set(plan.map((seat) => seat.key));
        const dropped = members
          .filter((member) => !kept.has(member.seat_key))
          .map((member) => member.seat_key);
        if (dropped.length > 0) {
          // A seat that disappears takes its member with it; they may take another free seat.
          await removeRoomMember(transaction, { roomId, seatKeys: dropped });
        }

        await updateRoom(transaction, roomId, {
          ...(patch.seats === undefined ? {} : { seatPlan: patch.seats }),
          ...(patch.personaPublic === undefined ? {} : { personaPublic: patch.personaPublic }),
          ...(patch.variables === undefined ? {} : { variables: patch.variables }),
        });

        // The owner always holds a seat: if theirs is gone, they take the first free human one.
        const remaining = await listRoomMembers(transaction, roomId);
        const ownerSeated = remaining.some((member) => member.user_id === room.owner_user_id);
        if (!ownerSeated) {
          const taken = new Set(remaining.map((member) => member.seat_key));
          const freeIndex = plan.findIndex(
            (seat) => seat.control === "human" && !taken.has(seat.key),
          );
          if (freeIndex >= 0) {
            const seat = plan[freeIndex] as RoomSeatPlanEntry;
            await addRoomMember(transaction, {
              id: randomUUID(),
              room_id: roomId,
              user_id: room.owner_user_id,
              seat_key: seat.key,
              seat: freeIndex + 1,
              ready: false,
            });
          }
        }
      });
      return detailOf({ actor, roomId });
    },

    join: async ({ actor, roomId }) => joinRoom(actor, roomId),

    async joinByCode({ actor, code }) {
      const found = await findRoomByCode(db, code.trim().toUpperCase());
      if (!found) throw new AppError(404, "ROOM_NOT_FOUND", "No room has that code");
      return joinRoom(actor, found.id);
    },

    async close({ actor, roomId }) {
      const room = await requireRoom(roomId);
      if (room.owner_user_id !== actor.userId && !actor.isAdmin) {
        throw new AppError(403, "NOT_ROOM_OWNER", "Only the room's owner may close it");
      }
      await setRoomStatus(db, roomId, "cancelled");
      return detailOf({ actor, roomId });
    },

    async setReady({ actor, roomId, ready }) {
      await requireRoom(roomId);
      const updated = await setRoomMemberReady(db, { roomId, userId: actor.userId, ready });
      if (!updated) throw new AppError(403, "NOT_SEATED", "Only a seated player can be ready");
      return detailOf({ actor, roomId });
    },

    async leave({ actor, roomId }) {
      const room = await requireRoom(roomId);
      await removeRoomMember(db, { roomId, userId: actor.userId });
      if (room.owner_user_id !== actor.userId) return detailOf({ actor, roomId });

      const members = await listRoomMembers(db, roomId);
      if (members.length === 0) {
        await setRoomStatus(db, roomId, "closed");
      } else {
        // The owner hands the table over rather than leaving it unstartable.
        const heir = members[0] as { user_id: string };
        await setRoomStatus(db, roomId, room.status, heir.user_id);
      }
      return detailOf({ actor, roomId });
    },

    async start({ actor, roomId }) {
      const room = await requireRoom(roomId);
      if (room.owner_user_id !== actor.userId) {
        throw new AppError(403, "NOT_ROOM_OWNER", "Only the room's owner may start a match");
      }
      if (room.status !== "open") throw new AppError(409, "ROOM_CLOSED", "This room is closed");
      if (await isPlaying(room)) {
        throw new AppError(409, "ROOM_BUSY", "A match of this room is still running");
      }

      const members = await listRoomMembers(db, roomId);
      const usernames = new Map(
        (
          await listPlatformUsersByIds(
            db,
            members.map((member) => member.user_id),
          )
        ).map((user) => [user.id, user.username]),
      );
      const bySeat = new Map(members.map((member) => [member.seat_key, member]));
      // Occupancy first, readiness second: "someone is missing" is the more useful complaint when
      // both are true, and it keeps the reason the same whatever order the seats are in.
      const empty = room.seat_plan.find(
        (seat) => seat.control === "human" && !bySeat.has(seat.key),
      );
      if (empty) throw new AppError(409, "SEAT_EMPTY", `Seat ${empty.key} has nobody in it`);
      const unready = room.seat_plan.find(
        (seat) => seat.control === "human" && bySeat.get(seat.key)?.ready !== true,
      );
      if (unready) throw new AppError(409, "NOT_READY", `Seat ${unready.key} is not ready`);

      const seats = room.seat_plan.map((seat) => {
        if (seat.control === "ai") return { key: seat.key, control: "ai" as const };
        const member = bySeat.get(seat.key) as { user_id: string };
        const username = usernames.get(member.user_id);
        if (username === undefined) {
          throw new AppError(409, "ACCOUNT_MISSING", "A seated account no longer exists");
        }
        return { key: seat.key, control: "human" as const, username };
      });

      // A match is created exactly the way any other match is; the room only remembers which one.
      const summary = await matchService.create({
        actor: { userId: actor.userId, isAdmin: actor.isAdmin },
        roomId,
        request: {
          gameId: room.game_id,
          seats,
          ...(room.persona_public ? { personaPublic: true } : {}),
          ...(Object.keys(room.variables).length === 0 ? {} : { variables: room.variables }),
        },
      });
      await updateRoom(db, roomId, { currentInstanceId: summary.instanceId });
      // Ready is a statement about the next match, so starting one clears the table's answers.
      await clearRoomReadiness(db, roomId);
      return { summary };
    },

    // The history is a list of the room's matches, and every match is readable by any signed-in
    // account anyway, so it needs no rule of its own beyond being signed in.
    async matches({ roomId }) {
      await requireRoom(roomId);
      const rows = await listRoomMatches(db, roomId);
      return rows.map((row) => ({
        instanceId: row.id,
        status: row.status,
        sequence: row.current_sequence,
        createdAt: row.created_at.toISOString(),
      }));
    },
  };
}
