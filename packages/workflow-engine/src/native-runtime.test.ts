import { describe, expect, it } from "vitest";
import type { GameDefinition, GameEvent, GameState } from "@vbrpg/contracts";
import { EngineError, transition } from "./native-runtime.js";

const definition: GameDefinition = {
  manifest: {
    gameId: "runtime-spike",
    slug: "runtime-spike",
    version: "1.0.0",
    dslVersion: "0.1",
    engineVersion: "native-0.1",
    authorId: "author-1",
    license: "MIT",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["assign"] },
      {
        id: "assign",
        type: "setVariable",
        config: { key: "rolesAssigned", value: true },
        next: ["wolf-action"],
      },
      {
        id: "wolf-action",
        type: "waitForPlayerInput",
        config: { participantId: "wolf", inputKey: "wolfTarget" },
        next: ["seer-action"],
      },
      {
        id: "seer-action",
        type: "waitForPlayerInput",
        config: { participantId: "seer", inputKey: "seerCheck" },
        next: ["vote"],
      },
      {
        id: "vote",
        type: "vote",
        config: { participantIds: ["wolf", "seer"], collectionKey: "votes" },
        next: ["end"],
      },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [],
  variables: {},
  visibility: {},
  presentation: {},
};

const initialState: GameState = {
  instanceId: "instance-1",
  gameVersionId: "version-1",
  engineVersion: "native-0.1",
  sequence: 0,
  status: "created",
  currentNodeId: "start",
  variables: {},
  participants: [
    { participantId: "wolf", actorId: "user-wolf", control: "human", status: "active" },
    { participantId: "seer", actorId: "user-seer", control: "human", status: "active" },
  ],
  waiting: null,
  randomSeed: "seed-1",
};

const timerDefinition: GameDefinition = {
  ...definition,
  manifest: { ...definition.manifest, gameId: "timer-spike", slug: "timer-spike" },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["timer"] },
      { id: "timer", type: "timer", config: { durationMs: 500 }, next: ["end"] },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
};

const aiDefinition: GameDefinition = {
  ...definition,
  manifest: { ...definition.manifest, gameId: "ai-spike", slug: "ai-spike" },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["ai"] },
      {
        id: "ai",
        type: "aiGenerate",
        config: {
          input: { promptKey: "runtime-spike" },
          timeoutMs: 5_000,
          maxAttempts: 2,
          fallbackNodeId: "end",
          resultKey: "aiResult",
        },
        next: ["end"],
      },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
};

function event(
  sequence: number,
  type: GameEvent["type"],
  payload: Record<string, unknown> = {},
): GameEvent {
  return {
    eventId: `event-${sequence}`,
    instanceId: "instance-1",
    sequence,
    type,
    actor: null,
    occurredAtMs: sequence * 1_000,
    idempotencyKey: `idempotency-${sequence}`,
    payload,
  };
}

function playToEnd(): GameState {
  let state = initialState;
  const events = [
    event(1, "instanceCreated"),
    event(2, "playerInputReceived", { participantId: "wolf", value: "seer" }),
    event(3, "playerInputReceived", { participantId: "seer", value: "wolf" }),
    event(4, "playerInputReceived", { participantId: "wolf", value: "seer" }),
    event(5, "playerInputReceived", { participantId: "seer", value: "wolf" }),
  ];

  for (const currentEvent of events) {
    state = transition(definition, state, currentEvent).state;
  }

  return state;
}

describe("native workflow runtime spike", () => {
  it("executes role assignment, two private actions, and collected votes", () => {
    let result = transition(definition, initialState, event(1, "instanceCreated"));

    expect(result.state.variables).toEqual({ rolesAssigned: true });
    expect(result.state.waiting).toEqual({
      kind: "playerInput",
      nodeId: "wolf-action",
      participantIds: ["wolf"],
    });

    result = transition(
      definition,
      result.state,
      event(2, "playerInputReceived", { participantId: "wolf", value: "seer" }),
    );
    expect(result.state.waiting?.nodeId).toBe("seer-action");

    result = transition(
      definition,
      result.state,
      event(3, "playerInputReceived", { participantId: "seer", value: "wolf" }),
    );
    expect(result.state.waiting?.kind).toBe("collectInput");

    result = transition(
      definition,
      result.state,
      event(4, "playerInputReceived", { participantId: "wolf", value: "seer" }),
    );
    expect(result.state.status).toBe("waiting");
    expect(result.state.variables.votes).toEqual({ wolf: "seer" });

    result = transition(
      definition,
      result.state,
      event(5, "playerInputReceived", { participantId: "seer", value: "wolf" }),
    );
    expect(result.state.status).toBe("completed");
    expect(result.state.variables.votes).toEqual({ wolf: "seer", seer: "wolf" });
  });

  it("produces the same final state when replaying the same event trace", () => {
    const first = playToEnd();
    const second = playToEnd();

    expect(JSON.stringify(first)).toBe(JSON.stringify(second));
  });

  it("rejects an input from a participant who is not waiting", () => {
    const created = transition(definition, initialState, event(1, "instanceCreated"));

    expect(() => transition(
      definition,
      created.state,
      event(2, "playerInputReceived", { participantId: "seer", value: "wolf" }),
    )).toThrowError(new EngineError("NOT_ALLOWED", "Participant is not allowed to respond: seer"));
  });

  it("rejects repeated votes instead of applying them twice", () => {
    let result = transition(definition, initialState, event(1, "instanceCreated"));
    result = transition(
      definition,
      result.state,
      event(2, "playerInputReceived", { participantId: "wolf", value: "seer" }),
    );
    result = transition(
      definition,
      result.state,
      event(3, "playerInputReceived", { participantId: "seer", value: "wolf" }),
    );
    result = transition(
      definition,
      result.state,
      event(4, "playerInputReceived", { participantId: "wolf", value: "seer" }),
    );

    expect(() => transition(
      definition,
      result.state,
      event(5, "playerInputReceived", { participantId: "wolf", value: "wolf" }),
    )).toThrowError(new EngineError("DUPLICATE_INPUT", "Participant already responded: wolf"));
  });

  it("does not accept gaps in the event sequence", () => {
    expect(() => transition(definition, initialState, event(2, "instanceCreated"))).toThrowError(
      new EngineError("SEQUENCE_MISMATCH", "Event sequence must advance exactly once"),
    );
  });

  it("turns a timer node into a deterministic scheduled command", () => {
    const result = transition(timerDefinition, initialState, event(1, "instanceCreated"));

    expect(result.state.waiting).toEqual({
      kind: "timer",
      nodeId: "timer",
      participantIds: [],
      deadlineMs: 1_500,
    });
    expect(result.commands).toEqual([{
      commandId: "instance-1:schedule:1:timer",
      instanceId: "instance-1",
      type: "schedule",
      runAtMs: 1_500,
      job: "timerExpired",
    }]);

    const completed = transition(
      timerDefinition,
      result.state,
      event(2, "timerExpired", { nodeId: "timer" }),
    );
    expect(completed.state.status).toBe("completed");
  });

  it("turns an AI node into a bounded command and resumes from its result", () => {
    const result = transition(aiDefinition, initialState, event(1, "instanceCreated"));

    expect(result.commands).toEqual([{
      commandId: "instance-1:ai:1:ai",
      instanceId: "instance-1",
      type: "aiGenerate",
      input: { promptKey: "runtime-spike" },
      timeoutMs: 5_000,
      maxAttempts: 2,
      fallbackNodeId: "end",
    }]);

    const completed = transition(
      aiDefinition,
      result.state,
      event(2, "aiResultReceived", { result: { choice: "seer" } }),
    );
    expect(completed.state.status).toBe("completed");
    expect(completed.state.variables.aiResult).toEqual({ choice: "seer" });
  });
});
