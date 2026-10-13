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
  tenantId: idSchema,
  participantId: idSchema.optional(),
});

export const nodeTypeSchema = z.enum([
  "start",
  "end",
  "setVariable",
  "branch",
  "waitForPlayerInput",
  "collectInput",
  "timer",
  "vote",
  "random",
  "aiGenerate",
  "emitEvent",
  "subflow",
  "parallel",
  "join",
]);

export const workflowNodeSchema = z.object({
  id: idSchema,
  type: nodeTypeSchema,
  config: z.record(jsonValueSchema).default({}),
  next: z.array(idSchema).default([]),
});

export const gameDefinitionSchema = z.object({
  manifest: z.object({
    gameId: idSchema,
    slug: z.string().regex(/^[a-z0-9][a-z0-9-]*$/),
    version: z.string().min(1),
    dslVersion: z.string().min(1),
    engineVersion: z.string().min(1),
    authorId: idSchema,
    license: z.string().min(1),
    attribution: z.string().optional(),
    contentHash: z.string().min(1).optional(),
  }),
  workflow: z.object({
    entryNodeId: idSchema,
    nodes: z.array(workflowNodeSchema).min(1),
  }),
  roles: z.array(z.object({ id: idSchema, name: z.string().min(1) })).default([]),
  variables: z.record(jsonValueSchema).default({}),
  visibility: z.record(jsonValueSchema).default({}),
  presentation: z.record(jsonValueSchema).default({}),
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
  nodeId: idSchema,
  participantIds: z.array(idSchema).default([]),
  deadlineMs: z.number().int().nonnegative().optional(),
});

export const gameStateSchema = z.object({
  instanceId: idSchema,
  gameVersionId: idSchema,
  engineVersion: z.string().min(1),
  sequence: z.number().int().nonnegative(),
  status: z.enum(["created", "running", "waiting", "paused", "completed", "cancelled"]),
  currentNodeId: idSchema,
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
    "adminCommandApplied",
  ]),
  actor: actorRefSchema.nullable(),
  occurredAtMs: z.number().int().nonnegative(),
  idempotencyKey: z.string().min(1),
  payload: eventPayloadSchema,
});

export const externalCommandSchema = z.discriminatedUnion("type", [
  z.object({
    commandId: idSchema,
    instanceId: idSchema,
    type: z.literal("aiGenerate"),
    input: eventPayloadSchema,
    timeoutMs: z.number().int().positive(),
    maxAttempts: z.number().int().positive(),
    fallbackNodeId: idSchema,
  }),
  z.object({
    commandId: idSchema,
    instanceId: idSchema,
    type: z.literal("schedule"),
    runAtMs: z.number().int().nonnegative(),
    job: z.enum(["timerExpired", "resumeWorkflow"]),
  }),
  z.object({
    commandId: idSchema,
    instanceId: idSchema,
    type: z.literal("emit"),
    eventName: idSchema,
    payload: eventPayloadSchema,
  }),
]);

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
export type GameDefinition = z.infer<typeof gameDefinitionSchema>;
export type GameEvent = z.infer<typeof gameEventSchema>;
export type GameState = z.infer<typeof gameStateSchema>;
export type Participant = z.infer<typeof participantSchema>;
export type ExternalCommand = z.infer<typeof externalCommandSchema>;
export type PlayerView = z.infer<typeof playerViewSchema>;

export function parseGameDefinition(input: unknown): GameDefinition {
  return gameDefinitionSchema.parse(input);
}

export function parseGameEvent(input: unknown): GameEvent {
  return gameEventSchema.parse(input);
}

export function parseGameState(input: unknown): GameState {
  return gameStateSchema.parse(input);
}

export function parseExternalCommand(input: unknown): ExternalCommand {
  return externalCommandSchema.parse(input);
}

export function parsePlayerView(input: unknown): PlayerView {
  return playerViewSchema.parse(input);
}
