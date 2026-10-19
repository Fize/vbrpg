import { z } from "zod";

const idSchema = z.string().min(1);
const jsonValueSchema: z.ZodType<unknown> = z.lazy(() =>
  z.union([
    z.string(),
    z.number().finite(),
    z.boolean(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(jsonValueSchema),
  ]),
);

/** The part of a seat's persona the reader may see. Gender is always there, MBTI never is. */
export const seatPersonaSchema = z.object({
  gender: z.string().min(1),
  mbti: z.string().min(1).optional(),
  profession: z.string().min(1).optional(),
  personality: z.string().min(1).optional(),
  style: z.string().min(1).optional(),
});

export const participantSchema = z.object({
  participantId: idSchema,
  /** The account behind a human seat. AI seats are unowned, so this is absent. */
  actorId: idSchema.optional(),
  roleId: idSchema.optional(),
  control: z.enum(["human", "ai"]),
  status: z.enum(["active", "eliminated", "disconnected", "finished"]),
});

export const waitingSchema = z.object({
  kind: z.enum(["playerInput", "collectInput", "timer"]),
  stepId: idSchema,
  participantIds: z.array(idSchema).default([]),
  /** Action names this step accepts. The game's catalogue defines what each one means. */
  actions: z.array(idSchema).default([]),
  deadlineMs: z.number().int().nonnegative().optional(),
});

export const gameStateSchema = z.object({
  instanceId: idSchema,
  gameVersionId: idSchema,
  engineVersion: z.string().min(1),
  sequence: z.number().int().nonnegative(),
  status: z.enum(["created", "running", "waiting", "paused", "completed", "cancelled"]),
  stepId: idSchema,
  variables: z.record(jsonValueSchema),
  participants: z.array(participantSchema),
  waiting: waitingSchema.nullable(),
  randomSeed: z.string().min(1),
});

const eventPayloadSchema = z.record(jsonValueSchema);

/**
 * Types the platform itself writes. A game may invent its own — the column has no check, because
 * the vocabulary belongs to the rules, not to the platform.
 */
export const platformEventTypes = {
  instanceCreated: "instanceCreated",
  playerInputReceived: "playerInputReceived",
  /** A seat said something in the room. Who said it comes from `participantId`. */
  seatMessage: "seatMessage",
  /** One model call, carrying usage. The seat's reasoning and reply live in `payload`. */
  aiCall: "aiCall",
  aiResultReceived: "aiResultReceived",
  aiFailed: "aiFailed",
  timerExpired: "timerExpired",
  randomResolved: "randomResolved",
  adminCommandApplied: "adminCommandApplied",
} as const;

const eventUsageSchema = z.object({
  providerId: idSchema,
  modelId: z.string().min(1),
  promptTokens: z.number().int().nonnegative(),
  completionTokens: z.number().int().nonnegative(),
  totalTokens: z.number().int().nonnegative(),
});

/**
 * One row of the match record. Rows are read as history, never replayed into state, so every field
 * a viewer might want — including a seat's own reasoning — is part of the row.
 */
export const gameEventSchema = z.object({
  eventId: idSchema,
  instanceId: idSchema,
  sequence: z.number().int().positive(),
  type: z.string().min(1),
  participantId: idSchema.nullable(),
  actorUserId: idSchema.nullable(),
  stepId: idSchema.nullable(),
  occurredAtMs: z.number().int().nonnegative(),
  idempotencyKey: z.string().min(1),
  payload: eventPayloadSchema,
  /** Set on model-call rows only, and always as a whole. */
  usage: eventUsageSchema.nullable(),
});

/** What an `aiCall` row carries: the reply, the provider's reasoning and the tool calls. */
export const aiCallPayloadSchema = z.object({
  content: z.string().nullish(),
  reasoning: z.string().nullish(),
  /** Provider-bound opaque field that must be replayed verbatim (e.g. a thinking signature). */
  reasoningSignature: z.string().nullish(),
  finishReason: z.string().nullish(),
  toolCalls: z
    .array(z.object({ id: z.string(), name: z.string(), arguments: z.string() }))
    .default([]),
});

export const seatRequestSchema = z
  .object({
    key: z.string().min(1).max(64),
    control: z.enum(["human", "ai"]),
    /** Human seat: the account to seat. Omitted means the caller takes the seat. */
    username: z.string().min(1).max(64).optional(),
    /** Usually dealt by the game in `initialState`, so it is only an invitation here. */
    roleId: z.string().min(1).max(64).optional(),
  })
  .strict();

export const createMatchRequestSchema = z
  .object({
    gameId: idSchema,
    seats: z.array(seatRequestSchema).min(1).max(24),
    randomSeed: z.string().min(1).max(128).optional(),
    variables: z.record(jsonValueSchema).optional(),
  })
  .strict();

export const submitEventRequestSchema = z
  .object({
    type: z.string().min(1).max(64),
    participantKey: z.string().min(1).max(64),
    payload: z.record(jsonValueSchema).default({}),
  })
  .strict();

export const playerViewSchema = z.object({
  instanceId: idSchema,
  gameVersionId: idSchema,
  sequence: z.number().int().nonnegative(),
  status: gameStateSchema.shape.status,
  publicState: z.record(jsonValueSchema),
  privateState: z.record(jsonValueSchema),
  availableActions: z.array(
    z.object({
      actionId: idSchema,
      input: z.record(jsonValueSchema),
    }),
  ),
});

/** One argument of an action. `seat` tells a UI to pick from this match's seats. */
export const actionArgSchema = z.object({
  description: z.string(),
  kind: z.enum(["seat"]).optional(),
});

/**
 * One creation parameter a game asks for. The game owns the meaning, the platform only renders a
 * field for it and hands the values back as `variables` — which is how a word list stays the
 * game's input instead of the platform's constant.
 */
export const setupFieldSchema = z.object({
  name: idSchema,
  label: z.string().min(1),
  description: z.string().min(1),
  /**
   * How the field is produced. `text` is typed by the creator; `category` is typed too, but it is
   * the prompt the platform's own model turns into a pair; `word` is one half of a pair the creator
   * types themselves (and then may only watch); a field with `from` is not asked for at all — the
   * platform fills it from the pair, so nobody at the table sees the words before they are dealt.
   */
  kind: z.enum(["text", "category", "word"]).optional(),
  /**
   * When the field is one half of a generated word pair, which half. The platform defines the pair
   * shape (`{civilian, undercover}`); the game says where each half goes in its own parameters.
   */
  from: z.enum(["pair.civilian", "pair.undercover"]).optional(),
});

/** The catalogue entry a seat needs to build a form: the action name is the event it produces. */
export const gameActionSchema = z.object({
  name: idSchema,
  /** What the table calls this action. The name is a machine word; this is the human one. */
  label: z.string().min(1),
  description: z.string(),
  args: z.record(actionArgSchema).optional(),
  audience: z.enum(["room", "seat"]).optional(),
});

export const matchSummarySchema = z.object({
  instanceId: idSchema,
  gameId: idSchema,
  gameVersion: z.string().min(1),
  status: gameStateSchema.shape.status,
  sequence: z.number().int().nonnegative(),
  stepId: idSchema,
  createdAt: z.string().min(1),
  /** Seats the caller holds here. Empty means it is watching, not playing. */
  mySeatKeys: z.array(z.string().min(1)),
});

export const matchSeatSchema = z.object({
  participantId: idSchema,
  key: z.string().min(1),
  control: z.enum(["human", "ai"]),
  status: participantSchema.shape.status,
  actorUserId: idSchema.nullable(),
  /** Platform flavour, dealt at creation: what this reader may see of the seat's persona. */
  persona: seatPersonaSchema.nullable(),
});

export const matchRecordRowSchema = z.object({
  eventId: idSchema,
  sequence: z.number().int().positive(),
  type: z.string().min(1),
  participantId: idSchema.nullable(),
  actorUserId: idSchema.nullable(),
  stepId: idSchema.nullable(),
  occurredAtMs: z.number().int().nonnegative(),
  idempotencyKey: z.string().min(1),
  payload: eventPayloadSchema,
  usage: eventUsageSchema.nullable(),
});

export const matchListSchema = z.object({ matches: z.array(matchSummarySchema) });

export const gameCatalogueEntrySchema = z.object({
  gameId: idSchema,
  title: z.string().min(1),
  version: z.string().min(1),
  engineVersion: z.string().min(1),
  /** Its step names, so a list can show what a match is waiting at without a second call. */
  steps: z.record(z.string().min(1)),
  /** What this game asks for at creation, in the game's own words. */
  setup: z.array(setupFieldSchema),
  /** The tables this game can be played at. A room's seat plan must stay inside this range. */
  seats: z.object({ min: z.number().int().positive(), max: z.number().int().positive() }),
});

/**
 * The game's own words, so the platform never invents a name and never shows a machine word to a
 * player. `steps` names the steps the game advances through, `words` names everything else the
 * game puts in state (variable names, roles, outcome labels). Anything absent stays as it is.
 */
export const gameVocabularySchema = z.object({
  title: z.string().min(1),
  steps: z.record(z.string().min(1)),
  words: z.record(z.string().min(1)),
});

export const gameCatalogueSchema = z.object({ games: z.array(gameCatalogueEntrySchema) });

/**
 * Everything a page needs for one match. Any signed-in account may read any match, so the projection
 * is what differs: a seat holder sees its own private state and actions, a watcher sees the same
 * public state and nothing else. The record is the same for both, because it is the match's history.
 */
export const matchDetailSchema = z.object({
  summary: matchSummarySchema,
  game: gameVocabularySchema,
  seats: z.array(matchSeatSchema),
  /** The point the match is waiting on. Public: it is who the table is waiting for, not a secret. */
  waiting: waitingSchema.nullable(),
  /** Always present: a seat holder's view, or a watcher's public-only view. */
  view: playerViewSchema,
  /** The game's rules in its own words, plus this seat's private state — what an AI seat is told. */
  briefing: z.string().nullable(),
  record: z.array(matchRecordRowSchema),
  actions: z.array(gameActionSchema),
});

/** Administrator lifecycle only: a match's rules never see these. */
export const updateMatchStatusRequestSchema = z
  .object({ status: z.enum(["running", "paused", "cancelled"]) })
  .strict();

/** Asking the platform's own model for a word pair: one category in, two words out. */
export const generateWordPairRequestSchema = z
  .object({ category: z.string().trim().min(1).max(40) })
  .strict();

export const wordPairSchema = z.object({
  civilian: z.string().min(1),
  undercover: z.string().min(1),
});

/** A seat in a room's plan. Humans take theirs, AI seats are placeholders until a match starts. */
export const roomSeatPlanEntrySchema = z
  .object({ key: z.string().min(1).max(64), control: z.enum(["human", "ai"]) })
  .strict();

export const createRoomRequestSchema = z
  .object({
    gameId: idSchema,
    seats: z.array(roomSeatPlanEntrySchema).min(1).max(24),
    /** Creation parameters the game asked for, e.g. the category its words come from. */
    variables: z.record(jsonValueSchema).optional(),
  })
  .strict();

export const updateRoomRequestSchema = z
  .object({
    seats: z.array(roomSeatPlanEntrySchema).min(1).max(24).optional(),
    variables: z.record(jsonValueSchema).optional(),
  })
  .strict()
  .refine((value) => value.seats !== undefined || value.variables !== undefined, {
    message: "At least one of seats or variables is required",
  });

export const roomReadyRequestSchema = z.object({ ready: z.boolean() }).strict();

/** The short name of a room: six characters people can say out loud and type in. */
export const roomCodeSchema = z.string().regex(/^[A-Z0-9]{6}$/);

export const joinRoomByCodeRequestSchema = z.object({ code: roomCodeSchema }).strict();

export const roomSeatSchema = z.object({
  key: z.string().min(1),
  seat: z.number().int().positive(),
  control: z.enum(["human", "ai"]),
  userId: idSchema.nullable(),
  username: z.string().min(1).nullable(),
  ready: z.boolean(),
  isMe: z.boolean(),
});

export const roomSummarySchema = z.object({
  roomId: idSchema,
  /** The room's short name, for saying out loud. The id stays the identifier. */
  code: roomCodeSchema,
  gameId: idSchema,
  gameTitle: z.string().min(1),
  gameVersion: z.string().min(1),
  status: z.enum(["open", "closed", "cancelled"]),
  /** True while the room's current match is still running: one match at a time, several over time. */
  playing: z.boolean(),
  currentInstanceId: idSchema.nullable(),
  ownerUserId: idSchema,
  isOwner: z.boolean(),
  mySeatKeys: z.array(z.string().min(1)),
  seats: z.number().int().positive(),
  humanSeats: z.number().int().nonnegative(),
  aiSeats: z.number().int().nonnegative(),
  takenSeats: z.number().int().nonnegative(),
  readySeats: z.number().int().nonnegative(),
  createdAt: z.string().min(1),
});

export const roomDetailSchema = roomSummarySchema.extend({
  seatPlan: z.array(roomSeatSchema),
  variables: z.record(jsonValueSchema),
});

export type GameEvent = z.infer<typeof gameEventSchema>;
export type GameState = z.infer<typeof gameStateSchema>;
export type Participant = z.infer<typeof participantSchema>;
export type SeatRequest = z.infer<typeof seatRequestSchema>;
export type AiCallPayload = z.infer<typeof aiCallPayloadSchema>;
export type CreateMatchRequest = z.infer<typeof createMatchRequestSchema>;
export type SubmitEventRequest = z.infer<typeof submitEventRequestSchema>;
export type PlayerView = z.infer<typeof playerViewSchema>;
export type ActionArg = z.infer<typeof actionArgSchema>;
export type SeatPersona = z.infer<typeof seatPersonaSchema>;
export type SetupField = z.infer<typeof setupFieldSchema>;
export type GenerateWordPairRequest = z.infer<typeof generateWordPairRequestSchema>;
export type WordPair = z.infer<typeof wordPairSchema>;
export type RoomSeatPlanEntry = z.infer<typeof roomSeatPlanEntrySchema>;
export type CreateRoomRequest = z.infer<typeof createRoomRequestSchema>;
export type UpdateRoomRequest = z.infer<typeof updateRoomRequestSchema>;
export type RoomSeat = z.infer<typeof roomSeatSchema>;
export type RoomSummary = z.infer<typeof roomSummarySchema>;
export type RoomDetail = z.infer<typeof roomDetailSchema>;
export type GameAction = z.infer<typeof gameActionSchema>;
export type GameVocabulary = z.infer<typeof gameVocabularySchema>;
export type GameCatalogueEntry = z.infer<typeof gameCatalogueEntrySchema>;
export type MatchSummary = z.infer<typeof matchSummarySchema>;
export type MatchSeat = z.infer<typeof matchSeatSchema>;
export type MatchRecordRow = z.infer<typeof matchRecordRowSchema>;
export type MatchDetail = z.infer<typeof matchDetailSchema>;
export type UpdateMatchStatusRequest = z.infer<typeof updateMatchStatusRequestSchema>;

export function parseGameEvent(input: unknown): GameEvent {
  return gameEventSchema.parse(input);
}

export function parseGameState(input: unknown): GameState {
  return gameStateSchema.parse(input);
}

export function parsePlayerView(input: unknown): PlayerView {
  return playerViewSchema.parse(input);
}

export function parseAiCallPayload(input: unknown): AiCallPayload {
  return aiCallPayloadSchema.parse(input);
}

export function parseCreateMatchRequest(input: unknown): CreateMatchRequest {
  return createMatchRequestSchema.parse(input);
}

export function parseSubmitEventRequest(input: unknown): SubmitEventRequest {
  return submitEventRequestSchema.parse(input);
}

export function parseUpdateMatchStatusRequest(input: unknown): UpdateMatchStatusRequest {
  return updateMatchStatusRequestSchema.parse(input);
}

export function parseGenerateWordPairRequest(input: unknown): GenerateWordPairRequest {
  return generateWordPairRequestSchema.parse(input);
}

export function parseCreateRoomRequest(input: unknown): CreateRoomRequest {
  return createRoomRequestSchema.parse(input);
}

export function parseUpdateRoomRequest(input: unknown): UpdateRoomRequest {
  return updateRoomRequestSchema.parse(input);
}

export function parseRoomReadyRequest(input: unknown): { ready: boolean } {
  return roomReadyRequestSchema.parse(input);
}

export function parseJoinRoomByCodeRequest(input: unknown): { code: string } {
  return joinRoomByCodeRequestSchema.parse(input);
}
