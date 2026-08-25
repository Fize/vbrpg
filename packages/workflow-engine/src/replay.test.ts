import { describe, expect, it } from "vitest";
import type { GameDefinition, GameEvent, GameState } from "@vbrpg/contracts";
import { replayEvents } from "./replay.js";

const definition: GameDefinition = {
  manifest: {
    gameId: "game-replay",
    slug: "replay-test",
    version: "1.0.0",
    dslVersion: "v1",
    engineVersion: "native-test",
    authorId: "user-1",
    license: "MIT",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["input"] },
      { id: "input", type: "waitForPlayerInput", config: { inputKey: "answer", participantId: "p1" }, next: ["end"] },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [],
  variables: {},
  visibility: {},
  presentation: {},
};

const initialState: GameState = {
  instanceId: "instance-replay",
  gameVersionId: "version-replay",
  engineVersion: "native-test",
  sequence: 0,
  status: "created",
  currentNodeId: "start",
  variables: {},
  participants: [{ participantId: "p1", actorId: "user-1", control: "human", status: "active" }],
  waiting: null,
  randomSeed: "seed",
};

const events: GameEvent[] = [
  {
    eventId: "event-1",
    instanceId: "instance-replay",
    sequence: 1,
    type: "instanceCreated",
    actor: null,
    occurredAtMs: 1,
    idempotencyKey: "create",
    payload: {},
  },
  {
    eventId: "event-2",
    instanceId: "instance-replay",
    sequence: 2,
    type: "playerInputReceived",
    actor: { userId: "user-1", tenantId: "tenant-1", participantId: "p1" },
    occurredAtMs: 2,
    idempotencyKey: "answer",
    payload: { participantId: "p1", value: "yes" },
  },
];

describe("event replay", () => {
  it("replays the same event sequence deterministically", () => {
    const first = replayEvents(definition, initialState, events);
    const second = replayEvents(definition, initialState, events);
    expect(first).toEqual(second);
    expect(first.state.status).toBe("completed");
    expect(first.state.variables).toEqual({ answer: "yes" });
  });
});
