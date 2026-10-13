import { describe, expect, it } from "vitest";
import { compileGameDefinition } from "./compiler.js";
import { createInitialState, dispatchEvent } from "./runtime.js";

const compiled = compileGameDefinition({
  manifest: {
    gameId: "runtime-game",
    slug: "runtime-test",
    version: "1.0.0",
    dslVersion: "v1",
    engineVersion: "native-test",
    authorId: "user-1",
    license: "MIT",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["end"] },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [],
  variables: { round: 1 },
  visibility: {},
  presentation: {},
});

describe("compiled runtime entry points", () => {
  it("creates a deterministic initial state from a compiled definition", () => {
    const state = createInitialState(compiled, {
      instanceId: "instance-1",
      gameVersionId: "version-1",
      randomSeed: "seed-1",
      participants: [],
    });
    expect(state).toMatchObject({
      status: "created",
      currentNodeId: "start",
      variables: { round: 1 },
      sequence: 0,
    });
  });

  it("dispatches through the compiled definition", () => {
    const state = createInitialState(compiled, {
      instanceId: "instance-1",
      gameVersionId: "version-1",
      randomSeed: "seed-1",
      participants: [],
    });
    const result = dispatchEvent(compiled, state, {
      eventId: "event-1",
      instanceId: "instance-1",
      sequence: 1,
      type: "instanceCreated",
      actor: null,
      occurredAtMs: 0,
      idempotencyKey: "create",
      payload: {},
    });
    expect(result.state.status).toBe("completed");
  });
});
