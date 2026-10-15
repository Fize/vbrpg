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
  kind: z.enum(["playerInput", "collectInput", "timer", "ai"]),
  stepId: idSchema,
  participantIds: z.array(idSchema).default([]),
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

export type GameEvent = z.infer<typeof gameEventSchema>;
export type GameState = z.infer<typeof gameStateSchema>;
export type Participant = z.infer<typeof participantSchema>;
export type SeatRequest = z.infer<typeof seatRequestSchema>;
export type CreateMatchRequest = z.infer<typeof createMatchRequestSchema>;
export type SubmitEventRequest = z.infer<typeof submitEventRequestSchema>;
export type PlayerView = z.infer<typeof playerViewSchema>;

export function parseGameEvent(input: unknown): GameEvent {
  return gameEventSchema.parse(input);
}

export function parseGameState(input: unknown): GameState {
  return gameStateSchema.parse(input);
}

export function parsePlayerView(input: unknown): PlayerView {
  return playerViewSchema.parse(input);
}

export function parseCreateMatchRequest(input: unknown): CreateMatchRequest {
  return createMatchRequestSchema.parse(input);
}

export function parseSubmitEventRequest(input: unknown): SubmitEventRequest {
  return submitEventRequestSchema.parse(input);
}
