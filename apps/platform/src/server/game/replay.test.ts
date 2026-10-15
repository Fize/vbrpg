import { describe, expect, it } from "vitest";
import type { GameEvent, GameState } from "../../shared/index.js";
import { replayEvents, type TransitionFn } from "./replay.js";

/** A tiny game: one input event writes a variable and finishes. */
const transition: TransitionFn = (state, event) => {
  if (event.type === "instanceCreated") {
    return {
      state: { ...state, sequence: event.sequence, status: "waiting", waiting: {
        kind: "playerInput", stepId: "input", participantIds: ["p1"],
      } },
      events: [event],
      commands: [],
    };
  }
  const value = (event.payload as { value?: unknown }).value;
  return {
    state: { ...state, sequence: event.sequence, status: "completed", waiting: null,
      variables: { ...state.variables, answer: value } },
    events: [event],
    commands: [],
  };
};

const initialState: GameState = {
  instanceId: "instance-replay",
  gameVersionId: "version-replay",
  engineVersion: "native-test",
  sequence: 0,
  status: "created",
  stepId: "start",
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
    actor: { userId: "user-1", participantId: "p1" },
    occurredAtMs: 2,
    idempotencyKey: "answer",
    payload: { participantId: "p1", value: "yes" },
  },
];

describe("event replay", () => {
  it("replays the same event sequence deterministically", () => {
    const first = replayEvents(transition, initialState, events);
    const second = replayEvents(transition, initialState, events);
    expect(first).toEqual(second);
    expect(first.state.status).toBe("completed");
    expect(first.state.variables).toEqual({ answer: "yes" });
  });
});
