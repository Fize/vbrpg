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
  availableActions: z.array(z.object({
    actionId: idSchema,
    input: z.record(jsonValueSchema),
  })),
});

/** One argument of an action. `seat` tells a UI to pick from this match's seats. */
export const actionArgSchema = z.object({
  description: z.string(),
  kind: z.enum(["seat"]).optional(),
});

/** The catalogue entry a seat needs to build a form: the action name is the event it produces. */
export const gameActionSchema = z.object({
  name: idSchema,
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
});

export const matchSeatSchema = z.object({
  participantId: idSchema,
  key: z.string().min(1),
  control: z.enum(["human", "ai"]),
  status: participantSchema.shape.status,
  actorUserId: idSchema.nullable(),
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
  version: z.string().min(1),
  engineVersion: z.string().min(1),
});

export const gameCatalogueSchema = z.object({ games: z.array(gameCatalogueEntrySchema) });

/**
 * Everything a page needs for one match. `view` and `briefing` are absent for an administrator who
 * holds no seat; `actions` is the game's whole catalogue — the same vocabulary every seat sees.
 */
export const matchDetailSchema = z.object({
  summary: matchSummarySchema,
  seats: z.array(matchSeatSchema),
  /** The point the match is waiting on. Public: it is who the table is waiting for, not a secret. */
  waiting: waitingSchema.nullable(),
  view: playerViewSchema.nullable(),
  /** The game's rules in its own words, plus this seat's private state — what an AI seat is told. */
  briefing: z.string().nullable(),
  record: z.array(matchRecordRowSchema),
  actions: z.array(gameActionSchema),
});

/** Administrator lifecycle only: a match's rules never see these. */
export const updateMatchStatusRequestSchema = z
  .object({ status: z.enum(["running", "paused", "cancelled"]) })
  .strict();

export type GameEvent = z.infer<typeof gameEventSchema>;
export type GameState = z.infer<typeof gameStateSchema>;
export type Participant = z.infer<typeof participantSchema>;
export type SeatRequest = z.infer<typeof seatRequestSchema>;
export type AiCallPayload = z.infer<typeof aiCallPayloadSchema>;
export type CreateMatchRequest = z.infer<typeof createMatchRequestSchema>;
export type SubmitEventRequest = z.infer<typeof submitEventRequestSchema>;
export type PlayerView = z.infer<typeof playerViewSchema>;
export type ActionArg = z.infer<typeof actionArgSchema>;
export type GameAction = z.infer<typeof gameActionSchema>;
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
