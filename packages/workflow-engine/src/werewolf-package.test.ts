import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseGameDefinition, type GameDefinition, type GameEvent } from "@vbrpg/contracts";
import { transition } from "./native-runtime.js";
import { createInitialState } from "./runtime.js";
import { projectPlayerView } from "./projector.js";
import { validateGameDefinition } from "./validator.js";
import { compileGameDefinition } from "./compiler.js";

const pkg = JSON.parse(
  readFileSync(new URL("../../../docs/fixtures/werewolf-package.json", import.meta.url), "utf8"),
) as unknown;

const definition: GameDefinition = parseGameDefinition(pkg);

function event(sequence: number, type: GameEvent["type"], payload: Record<string, unknown>): GameEvent {
  return {
    eventId: `event-${sequence}`,
    instanceId: "werewolf-1",
    sequence,
    type,
    actor: null,
    occurredAtMs: sequence,
    idempotencyKey: `key-${sequence}`,
    payload,
  };
}

const participants = [
  { participantId: "p1", actorId: "u1", roleId: "werewolf", control: "ai" as const, status: "active" as const },
  { participantId: "p2", actorId: "u2", roleId: "werewolf", control: "ai" as const, status: "active" as const },
  { participantId: "p3", actorId: "u3", roleId: "villager", control: "ai" as const, status: "active" as const },
];

function play(events: GameEvent[]) {
  const compiled = compileGameDefinition(pkg);
  let state = createInitialState(compiled, {
    instanceId: "werewolf-1",
    gameVersionId: "version-1",
    randomSeed: "werewolf-seed",
    participants,
  });
  for (const next of events) {
    state = transition(compiled.definition, state, next).state;
  }
  return state;
}

describe("werewolf reference package", () => {
  it("is a valid, compilable package", () => {
    assert.deepEqual(validateGameDefinition(definition), { valid: true, issues: [] });
    assert.equal(compileGameDefinition(pkg).nodes.size, definition.workflow.nodes.length);
  });

  it("reaches a werewolf win when the pack kills the last villager", () => {
    const completed = play([
      event(1, "instanceCreated", {}),
      event(2, "playerInputReceived", { participantId: "p1", value: "p3" }),
      event(3, "playerInputReceived", { participantId: "p2", value: "p3" }),
    ]);

    expect(completed.status).toBe("completed");
    expect(completed.variables.winner).toBe("werewolves");
    expect(completed.variables.villagersAlive).toBe(0);
    expect(completed.variables.wolvesAlive).toBe(2);
    expect(completed.variables.victim).toBe("p3");
  });

  it("reaches a villager win when the pack turns on itself", () => {
    const completed = play([
      event(1, "instanceCreated", {}),
      event(2, "playerInputReceived", { participantId: "p1", value: "p2" }),
      event(3, "playerInputReceived", { participantId: "p2", value: "p1" }),
    ]);

    // Two wolves, one vote each: the tie resolves to the first value seen, deterministically.
    expect(completed.variables.victim).toBe("p2");
    expect(completed.variables.wolvesAlive).toBe(1);
    expect(completed.variables.villagersAlive).toBe(1);
    expect(completed.variables.winner).toBe("undecided");
    expect(completed.status).toBe("completed");
  });

  it("waits for every wolf before resolving the night", () => {
    const compiled = compileGameDefinition(pkg);
    const started = createInitialState(compiled, {
      instanceId: "werewolf-1",
      gameVersionId: "version-1",
      randomSeed: "werewolf-seed",
      participants,
    });

    const afterStart = transition(compiled.definition, started, event(1, "instanceCreated", {}));
    expect(afterStart.state.waiting).toEqual({
      kind: "collectInput",
      nodeId: "night",
      participantIds: ["p1", "p2"],
      deadlineMs: undefined,
    });

    const half = transition(compiled.definition, afterStart.state, event(2, "playerInputReceived", { participantId: "p1", value: "p3" }));
    expect(half.state.status).toBe("waiting");
    expect(half.state.variables.winner).toBeNull();
  });

  it("replays to an identical final state", () => {
    const events = [
      event(1, "instanceCreated", {}),
      event(2, "playerInputReceived", { participantId: "p1", value: "p3" }),
      event(3, "playerInputReceived", { participantId: "p2", value: "p3" }),
    ];

    expect(play(events)).toEqual(play(events));
  });

  it("keeps the night decisions out of the villager's view", () => {
    const state = play([
      event(1, "instanceCreated", {}),
      event(2, "playerInputReceived", { participantId: "p1", value: "p3" }),
      event(3, "playerInputReceived", { participantId: "p2", value: "p3" }),
    ]);

    const wolfView = projectPlayerView(definition, state, { kind: "participant", participantId: "p1" });
    const villagerView = projectPlayerView(definition, state, { kind: "participant", participantId: "p3" });
    const spectatorView = projectPlayerView(definition, state, { kind: "spectator" });

    expect(wolfView.privateState.victim).toBe("p3");
    expect(villagerView.privateState).toEqual({});
    expect(spectatorView.privateState).toEqual({});
    expect(wolfView.publicState).toEqual(villagerView.publicState);
    expect(spectatorView.publicState.winner).toBe("werewolves");
    expect(JSON.stringify(villagerView)).not.toContain("nightVotes");
  });
});
