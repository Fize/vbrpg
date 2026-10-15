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

export const actorRefSchema = z.object({
  userId: idSchema,
  participantId: idSchema.optional(),
});

export const participantSchema = z.object({
  participantId: idSchema,
  actorId: idSchema,
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

export const gameEventSchema = z.object({
  eventId: idSchema,
  instanceId: idSchema,
  sequence: z.number().int().positive(),
  type: z.enum([
    "instanceCreated",
    "playerInputReceived",
    "timerExpired",
    "randomResolved",
    "aiResultReceived",
    "aiFailed",
    "adminCommandApplied",
  ]),
  actor: actorRefSchema.nullable(),
  occurredAtMs: z.number().int().nonnegative(),
  idempotencyKey: z.string().min(1),
  payload: eventPayloadSchema,
});

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

export type ActorRef = z.infer<typeof actorRefSchema>;
export type GameEvent = z.infer<typeof gameEventSchema>;
export type GameState = z.infer<typeof gameStateSchema>;
export type Participant = z.infer<typeof participantSchema>;
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
