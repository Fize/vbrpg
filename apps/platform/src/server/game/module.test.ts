import { describe, expect, it } from "vitest";
import type { GameEvent } from "../../shared/index.js";
import { replayEvents } from "./replay.js";
import { createBaseState, createGameRegistry, type GameModule } from "./module.js";

/** A two-event game: one seat answers, and the answer ends it. */
const greeting: GameModule = {
  id: "greeting",
  version: "1.0.0",
  engineVersion: "core-1",
  visibility: { answer: { participant: "p1" } },
  initialState: (input) => createBaseState(input, { answer: null }),
  transition(state, event) {
    if (event.type === "instanceCreated") {
      return {
        state: {
          ...state,
          sequence: event.sequence,
          status: "waiting",
          stepId: "ask",
          waiting: { kind: "playerInput", stepId: "ask", participantIds: ["p1"] },
        },
        events: [event],
        commands: [],
      };
    }
    return {
      state: {
        ...state,
        sequence: event.sequence,
        status: "completed",
        stepId: "done",
        waiting: null,
        variables: { ...state.variables, answer: event.payload["value"] },
      },
      events: [event],
      commands: [],
    };
  },
};

const participants = [
  { participantId: "p1", actorId: "u1", roleId: "player", control: "human" as const, status: "active" as const },
];

function event(sequence: number, type: GameEvent["type"], payload: Record<string, unknown> = {}): GameEvent {
  return {
    eventId: `event-${sequence}`,
    instanceId: "instance-1",
    sequence,
    type,
    actor: null,
    occurredAtMs: sequence,
    idempotencyKey: `key-${sequence}`,
    payload,
  };
}

describe("game module registry", () => {
  it("finds registered games by id and refuses duplicates", () => {
    const registry = createGameRegistry([greeting]);
    expect(registry.list().map((module) => module.id)).toEqual(["greeting"]);
    expect(registry.get("greeting")?.version).toBe("1.0.0");
    expect(registry.get("missing")).toBeUndefined();
    expect(() => registry.require("missing")).toThrowError(/Unknown game: missing/);
    expect(() => createGameRegistry([greeting, greeting])).toThrowError(/Duplicate game id: greeting/);
  });

  it("drives a game through the platform envelope", () => {
    const game = createGameRegistry([greeting]).require("greeting");
    const state = game.initialState({
      instanceId: "instance-1",
      gameVersionId: "greeting@1.0.0",
      engineVersion: game.engineVersion,
      randomSeed: "seed-1",
      participants,
    });
    expect(state).toMatchObject({ sequence: 0, status: "created", stepId: "start", waiting: null });

    const started = game.transition(state, event(1, "instanceCreated"));
    expect(started.state).toMatchObject({ status: "waiting", stepId: "ask" });
    expect(started.state.waiting?.participantIds).toEqual(["p1"]);

    const events = [event(1, "instanceCreated"), event(2, "playerInputReceived", { participantId: "p1", value: "hi" })];
    const replayed = replayEvents(game.transition, state, events);
    expect(replayed.state).toMatchObject({ status: "completed", stepId: "done", sequence: 2 });
    expect(replayed.state.variables).toEqual({ answer: "hi" });
  });
});
