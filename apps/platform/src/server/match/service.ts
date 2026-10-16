import { randomUUID } from "node:crypto";
import type { Kysely, Transaction } from "kysely";
import type {
  CreateMatchRequest,
  GameAction,
  GameCatalogueEntry,
  GameEvent,
  GameState,
  MatchRecordRow,
  MatchSeat,
  MatchSummary,
  PlayerView,
  SubmitEventRequest,
  UpdateMatchStatusRequest,
} from "../../shared/index.js";
import { platformEventTypes } from "../../shared/index.js";
import {
  EngineError,
  projectPlayerView,
  resolveVisibility,
  type GameModule,
  type GameRegistry,
} from "../game/index.js";
import { AppError } from "../runtime/index.js";
import {
  advanceGameInstance,
  createGameInstance,
  findEventByIdempotencyKey,
  findPlatformUserByUsername,
  getGameInstance,
  insertGameEvent,
  insertGameParticipants,
  listGameEvents,
  listGameInstances,
  listGameParticipants,
  listSeatsForUser,
  lockGameInstance,
  recordAuditLog,
  setInstanceStatus,
  updateGameParticipantStatus,
  type Database,
} from "../db/index.js";

/** A game never produces more than this many derived events out of one submission. */
const MAX_DERIVED_EVENTS = 32;

/** Statuses a match accepts input in. Anything else is a lifecycle an administrator chose. */
const ACTIVE_STATUSES: ReadonlyArray<GameState["status"]> = ["created", "running", "waiting"];

export interface MatchActor {
  userId: string;
  isAdmin: boolean;
}

/** One model turn as the executor sees it: the call that came back, and the action it asked for. */
export interface RecordTurnInput {
  instanceId: string;
  participantId: string;
  /** Deterministic per turn, so a retry or a racing worker replays instead of duplicating. */
  turnKey: string;
  callIndex: number;
  call: {
    payload: Record<string, unknown>;
    usage: {
      providerId: string;
      modelId: string;
      promptTokens: number;
      completionTokens: number;
      totalTokens: number;
    } | null;
  };
  action?: { type: string; payload: Record<string, unknown> };
}

/** A model turn that ended without an action; the row explains why, the game decides what follows. */
export interface RecordFailureInput {
  instanceId: string;
  participantId: string;
  turnKey: string;
  code: string;
  message: string;
}

export type RecordTurnResult =
  | { accepted: true; summary: MatchSummary }
  | { accepted: false; code: string; message: string; summary: MatchSummary };

export interface MatchService {
  create(input: { actor: MatchActor; request: CreateMatchRequest }): Promise<MatchSummary>;
  /** Every match, newest first, each tagged with the seats this actor holds in it. */
  list(input: { actor: MatchActor }): Promise<MatchSummary[]>;
  /** The games this deployment ships, so a client can offer them without hardcoding ids. */
  listGames(): GameCatalogueEntry[];
  /** Administrator lifecycle. Writes `status` and an audit row; the game never sees it. */
  setStatus(input: {
    actor: MatchActor;
    instanceId: string;
    status: UpdateMatchStatusRequest["status"];
  }): Promise<MatchSummary>;
  /**
   * Records one model turn atomically: the `aiCall` row always lands, and the action it requested
   * lands with it unless the rules refuse it. A refusal keeps the call and returns the reason, so
   * the executor can tell the model without losing the evidence.
   */
  recordTurn(input: RecordTurnInput): Promise<RecordTurnResult>;
  /** Records a turn that produced no action: one `aiFailed` row for the game to react to. */
  recordFailure(input: RecordFailureInput): Promise<MatchSummary>;
  submit(input: {
    actor: MatchActor;
    instanceId: string;
    idempotencyKey: string;
    request: SubmitEventRequest;
  }): Promise<{ replayed: boolean; summary: MatchSummary; view: PlayerView }>;
  read(input: { actor: MatchActor; instanceId: string }): Promise<{
    summary: MatchSummary;
    seats: MatchSeat[];
    waiting: GameState["waiting"];
    view: PlayerView;
    briefing: string | null;
    record: MatchRecordRow[];
    actions: GameAction[];
  }>;
}

export function createMatchService(options: {
  db: Kysely<Database>;
  registry: GameRegistry;
}): MatchService {
  const { db, registry } = options;

  function requireGame(gameId: string): GameModule {
    const game = registry.get(gameId);
    if (!game) throw new AppError(404, "UNKNOWN_GAME", `No game is registered under ${gameId}`);
    return game;
  }

  function summarize(
    row: {
      id: string;
      game_id: string;
      game_version: string;
      status: GameState["status"];
      current_sequence: number;
      state_json: unknown;
      created_at: Date;
    },
    mySeats: ReadonlyArray<{ participant_key: string }> = [],
  ): MatchSummary {
    const state = row.state_json as GameState;
    return {
      instanceId: row.id,
      gameId: row.game_id,
      gameVersion: row.game_version,
      status: row.status,
      sequence: row.current_sequence,
      stepId: state.stepId,
      createdAt: row.created_at.toISOString(),
      mySeatKeys: mySeats.map((seat) => seat.participant_key),
    };
  }

  function viewFor(game: GameModule, state: GameState, participantId: string): PlayerView {
    return projectPlayerView(resolveVisibility(game.visibility, state), state, {
      kind: "participant",
      participantId,
    });
  }

  /** What a watcher sees: the same public state, no private state, no actions. */
  function spectatorViewFor(game: GameModule, state: GameState): PlayerView {
    return projectPlayerView(resolveVisibility(game.visibility, state), state, {
      kind: "spectator",
    });
  }

  /** A rule that refuses is a client error carrying the game's own code; anything else is a bug. */
  function settle<T>(run: () => T): T {
    try {
      return run();
    } catch (error) {
      if (error instanceof EngineError) {
        throw new AppError(409, error.code, error.message);
      }
      throw error;
    }
  }

  function runTransition(game: GameModule, state: GameState, event: GameEvent) {
    return settle(() => game.transition(state, event));
  }

  /**
   * The one write path: run the rule for this event, append the row, then advance the instance.
   * `sequence` belongs to the platform, everything else to the game. Runs in the caller's
   * transaction, so the row and the state can never disagree.
   */
  async function applyEvent(
    transaction: Transaction<Database>,
    input: { game: GameModule; instanceId: string; state: GameState; event: GameEvent },
  ): Promise<{ state: GameState; lastSequence: number }> {
    let state = input.state;
    let lastSequence = input.state.sequence;
    let derived = 0;
    const queue: Array<{ event: GameEvent; key: string }> = [
      { event: input.event, key: input.event.idempotencyKey },
    ];

    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) break;
      lastSequence += 1;
      const row: GameEvent = { ...item.event, sequence: lastSequence, idempotencyKey: item.key };
      const result = runTransition(input.game, state, row);
      await insertGameEvent(transaction, {
        id: row.eventId,
        instance_id: input.instanceId,
        sequence: row.sequence,
        type: row.type,
        participant_id: row.participantId,
        actor_user_id: row.actorUserId,
        step_id: row.stepId,
        idempotency_key: row.idempotencyKey,
        payload: row.payload,
        provider_id: row.usage?.providerId ?? null,
        model_id: row.usage?.modelId ?? null,
        prompt_tokens: row.usage?.promptTokens ?? null,
        completion_tokens: row.usage?.completionTokens ?? null,
        total_tokens: row.usage?.totalTokens ?? null,
      });
      state = { ...result.state, sequence: lastSequence };

      for (const extra of result.events) {
        derived += 1;
        if (derived > MAX_DERIVED_EVENTS) {
          throw new AppError(500, "TOO_MANY_DERIVED_EVENTS", "The game produced too many events");
        }
        // Derived events are a consequence of the submitted one, so their keys inherit it.
        queue.push({ event: extra, key: `${input.event.idempotencyKey}:${derived}` });
      }
    }

    // Seats carry a denormalized status for queries and for the pre-write check; keep it honest.
    for (const seat of state.participants) {
      const before = input.state.participants.find(
        (candidate) => candidate.participantId === seat.participantId,
      );
      if (before !== undefined && before.status !== seat.status) {
        await updateGameParticipantStatus(
          transaction,
          input.instanceId,
          seat.participantId,
          seat.status,
        );
      }
    }

    const advanced = await advanceGameInstance(transaction, {
      instanceId: input.instanceId,
      expectedSequence: input.state.sequence,
      state,
    });
    if (!advanced) {
      throw new AppError(409, "SEQUENCE_CONFLICT", "Another write advanced this match first");
    }
    return { state, lastSequence };
  }

  return {
    async create({ actor, request }) {
      const game = requireGame(request.gameId);
      const instanceId = randomUUID();
      const randomSeed = request.randomSeed ?? randomUUID();

      return db.transaction().execute(async (transaction) => {
        const planned = await Promise.all(
          request.seats.map(async (seat, index) => {
            let actorUserId: string | null = null;
            if (seat.control === "human") {
              // No seat name means the caller takes it; otherwise the account must exist.
              actorUserId = actor.userId;
              if (seat.username !== undefined) {
                const account = await findPlatformUserByUsername(
                  transaction,
                  seat.username.trim().toLowerCase(),
                );
                if (!account || !account.active) {
                  throw new AppError(
                    404,
                    "ACCOUNT_NOT_FOUND",
                    `No active account named ${seat.username}`,
                  );
                }
                actorUserId = account.id;
              }
            }
            return { ...seat, id: randomUUID(), actorUserId, seat: index + 1 };
          }),
        );

        const state = settle(() =>
          game.initialState({
            instanceId,
            gameVersionId: `${game.id}@${game.version}`,
            engineVersion: game.engineVersion,
            randomSeed,
            participants: planned.map((seat) => ({
              participantId: seat.id,
              ...(seat.actorUserId === null ? {} : { actorId: seat.actorUserId }),
              ...(seat.roleId === undefined ? {} : { roleId: seat.roleId }),
              control: seat.control,
              status: "active" as const,
            })),
            ...(request.variables === undefined ? {} : { variables: request.variables }),
          }),
        );

        await createGameInstance(transaction, {
          id: instanceId,
          gameId: game.id,
          gameVersion: game.version,
          status: state.status,
          currentSequence: 0,
          stateJson: state as unknown as Record<string, unknown>,
        });

        await insertGameParticipants(
          transaction,
          planned.map((seat) => {
            const dealt = state.participants.find(
              (candidate) => candidate.participantId === seat.id,
            );
            return {
              id: seat.id,
              instance_id: instanceId,
              actor_user_id: seat.actorUserId,
              participant_key: seat.key,
              role_id: dealt?.roleId ?? null,
              control: seat.control,
              status: dealt?.status ?? "active",
              seat: seat.seat,
              created_at: new Date(),
            };
          }),
        );

        // Creation is a write like any other: the game sees `instanceCreated` and moves to its
        // first waiting point, so the instance never stays in `created` while seats wait.
        await applyEvent(transaction, {
          game,
          instanceId,
          state: { ...state, sequence: 0 },
          event: {
            eventId: randomUUID(),
            instanceId,
            sequence: 1,
            type: platformEventTypes.instanceCreated,
            participantId: null,
            actorUserId: null,
            stepId: "start",
            occurredAtMs: Date.now(),
            idempotencyKey: `${instanceId}:created`,
            payload: {},
            usage: null,
          },
        });

        const stored = await getGameInstance(transaction, instanceId);
        if (!stored)
          throw new AppError(500, "INSTANCE_MISSING", "The match vanished during creation");
        return summarize(stored);
      });
    },

    async list({ actor }) {
      const rows = await listGameInstances(db, { limit: 50 });
      const seats = await listSeatsForUser(db, {
        userId: actor.userId,
        instanceIds: rows.map((row) => row.id),
      });
      const byInstance = new Map<string, Array<{ participant_key: string }>>();
      for (const seat of seats) {
        const list = byInstance.get(seat.instance_id) ?? [];
        list.push({ participant_key: seat.participant_key });
        byInstance.set(seat.instance_id, list);
      }
      return rows.map((row) => summarize(row, byInstance.get(row.id) ?? []));
    },

    listGames() {
      return registry.list().map((game) => ({
        gameId: game.id,
        title: game.title,
        version: game.version,
        engineVersion: game.engineVersion,
        steps: { ...(game.steps ?? {}) },
      }));
    },

    /**
     * The platform suspends a match without touching its state: the row lock is what serializes
     * this against a submission, and `state_json` keeps the status the game itself last chose, so
     * a resume hands the match back exactly as it was.
     */
    async setStatus({ actor, instanceId, status }) {
      if (!actor.isAdmin) {
        throw new AppError(
          403,
          "ADMIN_REQUIRED",
          "Only administrators may change a match lifecycle",
        );
      }
      return db.transaction().execute(async (transaction) => {
        const instance = await lockGameInstance(transaction, instanceId);
        if (!instance) throw new AppError(404, "MATCH_NOT_FOUND", "No such match");
        const isActive = ACTIVE_STATUSES.includes(instance.status);
        if (status === "running") {
          if (instance.status !== "paused") {
            throw new AppError(409, "MATCH_NOT_PAUSED", "Only a paused match can be resumed");
          }
        } else if (!isActive && instance.status !== "paused") {
          throw new AppError(
            409,
            "MATCH_ENDED",
            `A match in status ${instance.status} cannot change`,
          );
        } else if (instance.status === status) {
          throw new AppError(409, "MATCH_STATUS_UNCHANGED", `This match is already ${status}`);
        }

        // Resuming hands the match back the status the game itself last chose.
        const previous = stateOf(instance).status;
        const resuming = instance.status === "paused" && status === "running";
        const next = resuming && ACTIVE_STATUSES.includes(previous) ? previous : status;
        await setInstanceStatus(transaction, instanceId, next);
        await recordAuditLog(transaction, {
          id: randomUUID(),
          actorUserId: actor.userId,
          action: `match.${next}`,
          resourceType: "game_instance",
          resourceId: instanceId,
          metadata: { from: instance.status, to: next },
          succeeded: true,
        });
        return summarize({ ...instance, status: next });
      });
    },

    async recordTurn(input) {
      return db.transaction().execute(async (transaction) => {
        const instance = await lockGameInstance(transaction, input.instanceId);
        if (!instance) throw new AppError(404, "MATCH_NOT_FOUND", "No such match");
        const game = requireGame(instance.game_id);
        const seats = await listGameParticipants(transaction, input.instanceId);
        const seat = seats.find((candidate) => candidate.id === input.participantId);
        if (!seat) throw new AppError(404, "SEAT_NOT_FOUND", "That seat is not in this match");

        let state = stateOf(instance);
        const callKey = `${input.turnKey}:call:${input.callIndex}`;
        const already = await findEventByIdempotencyKey(transaction, input.instanceId, callKey);
        if (!already) {
          const callRow: GameEvent = {
            eventId: randomUUID(),
            instanceId: input.instanceId,
            sequence: instance.current_sequence + 1,
            type: platformEventTypes.aiCall,
            participantId: seat.id,
            actorUserId: null,
            stepId: state.stepId,
            occurredAtMs: Date.now(),
            idempotencyKey: callKey,
            payload: input.call.payload,
            usage: input.call.usage,
          };
          const applied = await applyEvent(transaction, {
            game,
            instanceId: input.instanceId,
            state: { ...state, sequence: instance.current_sequence },
            event: callRow,
          });
          state = applied.state;
        }

        const action = input.action;
        if (action === undefined) {
          const stored = await getGameInstance(transaction, input.instanceId);
          if (!stored)
            throw new AppError(500, "INSTANCE_MISSING", "The match vanished during the write");
          return { accepted: true, summary: summarize(stored) };
        }

        const actionKey = `${input.turnKey}:act:${input.callIndex}`;
        const replayed = await findEventByIdempotencyKey(transaction, input.instanceId, actionKey);
        if (replayed) {
          const stored = await getGameInstance(transaction, input.instanceId);
          if (!stored)
            throw new AppError(500, "INSTANCE_MISSING", "The match vanished during the write");
          return { accepted: true, summary: summarize(stored) };
        }

        const current = stateOf(instance);
        try {
          const applied = await applyEvent(transaction, {
            game,
            instanceId: input.instanceId,
            state: { ...current, sequence: state.sequence },
            event: {
              eventId: randomUUID(),
              instanceId: input.instanceId,
              sequence: state.sequence + 1,
              type: action.type,
              participantId: seat.id,
              actorUserId: null,
              stepId: state.stepId,
              occurredAtMs: Date.now(),
              idempotencyKey: actionKey,
              payload: action.payload,
              usage: null,
            },
          });
          return {
            accepted: true,
            summary: {
              ...summarize(instance),
              status: applied.state.status,
              sequence: applied.lastSequence,
              stepId: applied.state.stepId,
            },
          };
        } catch (error) {
          // The rule refused the action: the call stays in the log and the reason goes back.
          if (error instanceof AppError) {
            return {
              accepted: false,
              code: error.code,
              message: error.message,
              summary: { ...summarize(instance), sequence: state.sequence },
            };
          }
          throw error;
        }
      });
    },

    async recordFailure(input) {
      return db.transaction().execute(async (transaction) => {
        const instance = await lockGameInstance(transaction, input.instanceId);
        if (!instance) throw new AppError(404, "MATCH_NOT_FOUND", "No such match");
        const game = requireGame(instance.game_id);
        const key = `${input.turnKey}:failed`;
        const already = await findEventByIdempotencyKey(transaction, input.instanceId, key);
        if (already) return summarize(instance);

        // The game may react (skip the seat, replace it, end the match); the platform does not.
        const applied = await applyEvent(transaction, {
          game,
          instanceId: input.instanceId,
          state: { ...stateOf(instance), sequence: instance.current_sequence },
          event: {
            eventId: randomUUID(),
            instanceId: input.instanceId,
            sequence: instance.current_sequence + 1,
            type: platformEventTypes.aiFailed,
            participantId: input.participantId,
            actorUserId: null,
            stepId: stateOf(instance).stepId,
            occurredAtMs: Date.now(),
            idempotencyKey: key,
            payload: { code: input.code, message: input.message },
            usage: null,
          },
        });
        return {
          ...summarize(instance),
          status: applied.state.status,
          sequence: applied.lastSequence,
        };
      });
    },

    async submit({ actor, instanceId, idempotencyKey, request }) {
      if (idempotencyKey.trim().length === 0) {
        throw new AppError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key must not be empty");
      }

      return db.transaction().execute(async (transaction) => {
        const instance = await lockGameInstance(transaction, instanceId);
        if (!instance) throw new AppError(404, "MATCH_NOT_FOUND", "No such match");
        const game = requireGame(instance.game_id);
        const seats = await listGameParticipants(transaction, instanceId);
        const seat = seats.find(
          (candidate) => candidate.participant_key === request.participantKey,
        );
        if (!seat)
          throw new AppError(404, "SEAT_NOT_FOUND", `No seat named ${request.participantKey}`);
        if (seat.actor_user_id !== actor.userId) {
          throw new AppError(403, "NOT_YOUR_SEAT", "That seat belongs to another account");
        }
        if (seat.status !== "active") {
          throw new AppError(409, "SEAT_INACTIVE", "That seat is no longer active");
        }

        const current = stateOf(instance);
        // A repeated key returns the state as it is now, not as it was: the caller asked again.
        const replay = await findEventByIdempotencyKey(transaction, instanceId, idempotencyKey);
        if (replay) {
          return {
            replayed: true,
            summary: summarize(instance),
            view: viewFor(game, current, seat.id),
          };
        }

        if (!["created", "running", "waiting"].includes(instance.status)) {
          throw new AppError(
            409,
            "MATCH_NOT_RUNNING",
            `A match in status ${instance.status} takes no input`,
          );
        }

        const applied = await applyEvent(transaction, {
          game,
          instanceId,
          state: { ...current, sequence: instance.current_sequence },
          event: {
            eventId: randomUUID(),
            instanceId,
            sequence: instance.current_sequence + 1,
            type: request.type,
            participantId: seat.id,
            actorUserId: actor.userId,
            stepId: current.stepId,
            occurredAtMs: Date.now(),
            idempotencyKey,
            payload: request.payload,
            usage: null,
          },
        });

        return {
          replayed: false,
          summary: {
            ...summarize(instance),
            status: applied.state.status,
            sequence: applied.lastSequence,
            stepId: applied.state.stepId,
          },
          view: viewFor(game, applied.state, seat.id),
        };
      });
    },

    async read({ actor, instanceId }) {
      const instance = await getGameInstance(db, instanceId);
      if (!instance) throw new AppError(404, "MATCH_NOT_FOUND", "No such match");
      const game = requireGame(instance.game_id);
      const seats = await listGameParticipants(db, instanceId);
      // Any signed-in account may watch any match; holding a seat is what changes the view.
      const mine = seats.find((seat) => seat.actor_user_id === actor.userId);

      const rows = await listGameEvents(db, instanceId);
      const state = stateOf(instance);
      return {
        summary: summarize(
          instance,
          seats.filter((seat) => seat.actor_user_id === actor.userId),
        ),
        game: {
          title: game.title,
          steps: { ...(game.steps ?? {}) },
          words: { ...(game.words ?? {}) },
        },
        seats: seats.map((seat) => ({
          participantId: seat.id,
          key: seat.participant_key,
          control: seat.control,
          status: seat.status,
          actorUserId: seat.actor_user_id,
        })),
        view: mine ? viewFor(game, state, mine.id) : spectatorViewFor(game, state),
        waiting: state.waiting,
        // The same words an AI seat is given: a human seat deserves the rules it is playing by.
        briefing: mine ? (game.briefing?.(state, mine.id) ?? null) : null,
        record: rows.map(toRecordRow),
        actions: (game.actions ?? []).map((action) => ({
          name: action.name,
          label: action.label,
          description: action.description,
          ...(action.args ? { args: { ...action.args } } : {}),
          ...(action.audience ? { audience: action.audience } : {}),
        })),
      };
    },
  };
}

function stateOf(row: { state_json: unknown }): GameState {
  return row.state_json as GameState;
}

function toRecordRow(row: {
  id: string;
  sequence: number;
  type: string;
  participant_id: string | null;
  actor_user_id: string | null;
  step_id: string | null;
  occurred_at: Date;
  idempotency_key: string;
  payload: Record<string, unknown>;
  provider_id: string | null;
  model_id: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}): MatchRecordRow {
  return {
    eventId: row.id,
    sequence: row.sequence,
    type: row.type,
    participantId: row.participant_id,
    actorUserId: row.actor_user_id,
    stepId: row.step_id,
    occurredAtMs: row.occurred_at.getTime(),
    idempotencyKey: row.idempotency_key,
    payload: row.payload,
    usage:
      row.provider_id === null || row.model_id === null
        ? null
        : {
            providerId: row.provider_id,
            modelId: row.model_id,
            promptTokens: row.prompt_tokens ?? 0,
            completionTokens: row.completion_tokens ?? 0,
            totalTokens: row.total_tokens ?? 0,
          },
  };
}
