import { describe, expect, it } from "vitest";
import type { GameDefinition, GameEvent, GameState } from "@vbrpg/contracts";
import { EngineError, deterministicRandom, transition } from "./native-runtime.js";

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
  agents: [],
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
          agentId: "seer",
          participantId: "seer",
          input: { promptKey: "runtime-spike" },
          fallbackNodeId: "end",
          resultKey: "aiResult",
        },
        next: ["end"],
      },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [{ id: "seer", name: "Seer" }],
  agents: [
    {
      id: "seer",
      roleId: "seer",
      systemPrompt: "You are the seer.",
      limits: { timeoutMs: 5_000, maxAttempts: 2, tokenBudget: 4_096 },
    },
  ],
};

const loopDefinition: GameDefinition = {
  ...definition,
  manifest: { ...definition.manifest, gameId: "loop-spike", slug: "loop-spike" },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["loop"] },
      {
        id: "loop",
        type: "loop",
        config: {
          bodyNodeId: "tally",
          counterKey: "round",
          maxIterations: 3,
          while: { op: "lt", args: [{ op: "var", name: "round" }, { op: "lit", value: 3 }] },
        },
        next: ["end"],
      },
      {
        id: "tally",
        type: "setVariable",
        config: {
          key: "total",
          valueExpr: { op: "add", args: [{ op: "var", name: "total" }, { op: "lit", value: 1 }] },
        },
        next: ["loop"],
      },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  variables: { round: 0, total: 0 },
};

const loopState: GameState = { ...initialState, variables: { round: 0, total: 0 } };

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

    expect(result.state.waiting).toEqual({
      kind: "ai",
      nodeId: "ai",
      participantIds: ["seer"],
    });
    expect(result.commands).toEqual([{
      commandId: "instance-1:ai:1:ai",
      instanceId: "instance-1",
      type: "aiGenerate",
      agentId: "seer",
      input: { promptKey: "runtime-spike" },
      // The limits come from the agent the version declares, not from the node.
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

  it("refuses an AI node whose agent the version does not declare", () => {
    const unknownAgent: GameDefinition = {
      ...aiDefinition,
      agents: [],
    };

    expect(() => transition(unknownAgent, initialState, event(1, "instanceCreated"))).toThrowError(
      new EngineError("UNKNOWN_AGENT", "Node ai references an undeclared agent: seer"),
    );
  });

  it("routes an exhausted AI command to its declared fallback node", () => {
    const waiting = transition(aiDefinition, initialState, event(1, "instanceCreated"));

    const failed = transition(aiDefinition, waiting.state, event(2, "aiFailed", { reason: "TIMEOUT" }));

    expect(failed.state.status).toBe("completed");
    expect(failed.state.waiting).toBeNull();
    expect(failed.state.variables.aiResult).toBeUndefined();
  });
});

const randomDefinition: GameDefinition = {
  ...definition,
  manifest: { ...definition.manifest, gameId: "random-spike", slug: "random-spike" },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["roll"] },
      {
        id: "roll",
        type: "random",
        config: { key: "roll", min: 1, max: 6 },
        next: ["end"],
      },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
};

describe("deterministic randomness", () => {
  it("derives the same value for the same instance, node and sequence", () => {
    const value = deterministicRandom("seed-1", "roll", 1, 1, 6);

    expect(value).toBe(deterministicRandom("seed-1", "roll", 1, 1, 6));

    // A 6-value range collides by chance, so compare whole sequences instead.
    const draw = (seed: string) =>
      Array.from({ length: 20 }, (_, index) => deterministicRandom(seed, "roll", index + 1, 1, 1_000_000));
    expect(draw("seed-2")).not.toEqual(draw("seed-1"));
  });

  it("stays inside the configured range", () => {
    const values = new Set<number>();
    for (let sequence = 1; sequence <= 200; sequence += 1) {
      const value = deterministicRandom("seed-range", "roll", sequence, 3, 7);
      expect(value).toBeGreaterThanOrEqual(3);
      expect(value).toBeLessThanOrEqual(7);
      values.add(value);
    }
    expect(values.size).toBe(5);
  });

  it("writes the derived value and replays identically", () => {
    const first = transition(randomDefinition, initialState, {
      eventId: "event-1",
      instanceId: "instance-1",
      sequence: 1,
      type: "instanceCreated",
      actor: null,
      occurredAtMs: 0,
      idempotencyKey: "create",
      payload: {},
    });

    const replay = transition(randomDefinition, initialState, {
      eventId: "event-1",
      instanceId: "instance-1",
      sequence: 1,
      type: "instanceCreated",
      actor: null,
      occurredAtMs: 0,
      idempotencyKey: "create",
      payload: {},
    });

    expect(first.state.variables.roll).toBeGreaterThanOrEqual(1);
    expect(first.state.variables.roll).toBeLessThanOrEqual(6);
    expect(replay.state).toEqual(first.state);

    const reseeded = transition(
      { ...randomDefinition, variables: {} },
      { ...initialState, randomSeed: "another-seed" },
      {
        eventId: "event-1",
        instanceId: "instance-1",
        sequence: 1,
        type: "instanceCreated",
        actor: null,
        occurredAtMs: 0,
        idempotencyKey: "create",
        payload: {},
      },
    );
    expect(transition(randomDefinition, initialState, {
      eventId: "event-1",
      instanceId: "instance-1",
      sequence: 1,
      type: "instanceCreated",
      actor: null,
      occurredAtMs: 0,
      idempotencyKey: "create",
      payload: {},
    }).state.variables.roll).not.toBe(reseeded.state.variables.roll);
  });

  it("repeats the loop body while the condition holds and exits on it", () => {
    const result = transition(loopDefinition, loopState, event(1, "instanceCreated"));

    expect(result.state.variables).toEqual({ round: 3, total: 3 });
    expect(result.state.status).toBe("completed");
    expect(result.commands).toEqual([]);
  });

  it("stops at maxIterations when the loop declares no condition", () => {
    const bounded: GameDefinition = {
      ...loopDefinition,
      workflow: {
        ...loopDefinition.workflow,
        nodes: loopDefinition.workflow.nodes.map((node) =>
          node.id === "loop"
            ? { ...node, config: { bodyNodeId: "tally", counterKey: "round", maxIterations: 2 } }
            : node,
        ),
      },
    };

    const result = transition(bounded, loopState, event(1, "instanceCreated"));

    expect(result.state.variables).toEqual({ round: 2, total: 2 });
    expect(result.state.status).toBe("completed");
  });

  it("replays a loop to an identical state", () => {
    expect(transition(loopDefinition, loopState, event(1, "instanceCreated")).state).toEqual(
      transition(loopDefinition, loopState, event(1, "instanceCreated")).state,
    );
  });
});
