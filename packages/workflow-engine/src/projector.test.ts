import assert from "node:assert/strict";
import { describe, expect, it } from "vitest";
import type { GameDefinition, GameState } from "@vbrpg/contracts";
import { parseVisibilityRule, projectPlayerView, type Viewer } from "./projector.js";

const HIDDEN_VALUE = "do-not-leak";

function definition(visibility: Record<string, unknown> = defaultVisibility): GameDefinition {
  return {
    manifest: {
      gameId: "werewolf",
      slug: "werewolf",
      version: "1.0.0",
      dslVersion: "v1",
      engineVersion: "native-test",
      authorId: "author-1",
      license: "MIT",
    },
    workflow: {
      entryNodeId: "start",
      nodes: [
        { id: "start", type: "start", config: {}, next: ["ask"] },
        {
          id: "ask",
          type: "waitForPlayerInput",
          config: { inputKey: "answer", participantId: "p2" },
          next: ["end"],
        },
        { id: "end", type: "end", config: {}, next: [] },
      ],
    },
    roles: [
      { id: "werewolf", name: "Werewolf" },
      { id: "villager", name: "Villager" },
      { id: "seer", name: "Seer" },
    ],
    variables: {},
    visibility,
    presentation: {},
  };
}

const defaultVisibility = {
  dayNumber: "public",
  wolfTeam: { role: "werewolf" },
  seerResult: { participant: "p3" },
};

function state(overrides: Partial<GameState> = {}): GameState {
  return {
    instanceId: "instance-1",
    gameVersionId: "version-1",
    engineVersion: "native-test",
    sequence: 3,
    status: "waiting",
    currentNodeId: "ask",
    variables: {
      dayNumber: 2,
      wolfTeam: ["p1"],
      seerResult: "p1 is a werewolf",
      hiddenSeed: HIDDEN_VALUE,
    },
    participants: [
      { participantId: "p1", actorId: "u1", roleId: "werewolf", control: "ai", status: "active" },
      { participantId: "p2", actorId: "u2", roleId: "villager", control: "human", status: "active" },
      { participantId: "p3", actorId: "u3", roleId: "seer", control: "human", status: "active" },
    ],
    waiting: { kind: "playerInput", nodeId: "ask", participantIds: ["p2"], deadlineMs: undefined },
    randomSeed: "seed-1",
    ...overrides,
  };
}

const werewolf: Viewer = { kind: "participant", participantId: "p1" };
const villager: Viewer = { kind: "participant", participantId: "p2" };
const seer: Viewer = { kind: "participant", participantId: "p3" };
const spectator: Viewer = { kind: "spectator" };
const allViewers = [werewolf, villager, seer, spectator];

describe("player view projection", () => {
  it("shows the same public state to every viewer", () => {
    const views = allViewers.map((viewer) => projectPlayerView(definition(), state(), viewer));

    for (const view of views) {
      assert.deepEqual(view.publicState, { dayNumber: 2 });
    }
  });

  it("keeps role secrets in the private bucket of the matching role only", () => {
    const wolfView = projectPlayerView(definition(), state(), werewolf);
    const seerView = projectPlayerView(definition(), state(), seer);
    const villagerView = projectPlayerView(definition(), state(), villager);

    assert.deepEqual(wolfView.privateState, { wolfTeam: ["p1"] });
    assert.deepEqual(seerView.privateState, { seerResult: "p1 is a werewolf" });
    assert.deepEqual(villagerView.privateState, {});
  });

  it("never projects a variable the definition does not declare", () => {
    for (const viewer of allViewers) {
      const view = projectPlayerView(definition(), state(), viewer);
      assert.ok(!("hiddenSeed" in view.publicState));
      assert.ok(!("hiddenSeed" in view.privateState));
      assert.ok(!JSON.stringify(view).includes(HIDDEN_VALUE));
    }
  });

  it("gives a spectator public state only", () => {
    const view = projectPlayerView(definition(), state(), spectator);

    assert.deepEqual(view.privateState, {});
    assert.deepEqual(view.availableActions, []);
    assert.equal(view.instanceId, "instance-1");
    assert.equal(view.sequence, 3);
  });

  it("rejects a viewer that is not part of the instance", () => {
    expect(() =>
      projectPlayerView(definition(), state(), { kind: "participant", participantId: "p9" }),
    ).toThrowError(/not part of the instance/);
  });

  it("only offers an action to the participant whose turn it is", () => {
    const waitingOnVillager = state();
    assert.deepEqual(projectPlayerView(definition(), waitingOnVillager, villager).availableActions, [
      { actionId: "ask", input: { participantId: "p2" } },
    ]);
    assert.deepEqual(projectPlayerView(definition(), waitingOnVillager, werewolf).availableActions, []);

    const waitingOnEveryone = state({
      waiting: { kind: "collectInput", nodeId: "ask", participantIds: [], deadlineMs: undefined },
    });
    assert.equal(projectPlayerView(definition(), waitingOnEveryone, werewolf).availableActions.length, 1);
    assert.deepEqual(projectPlayerView(definition(), waitingOnEveryone, spectator).availableActions, []);
  });

  it("does not offer actions while nobody is being waited on", () => {
    const running = state({ status: "running", waiting: null });

    assert.deepEqual(projectPlayerView(definition(), running, villager).availableActions, []);
  });

  it("refuses to guess at an unparseable rule", () => {
    const bad = [{}, { role: "" }, { roleId: "werewolf" }, { role: "werewolf", extra: 1 }, "private", 42, []];

    for (const rule of bad) {
      expect(() => parseVisibilityRule("secret", rule)).toThrowError(/Visibility rule for "secret"/);
      expect(() => projectPlayerView(definition({ secret: rule }), state(), werewolf)).toThrow();
    }
  });
});
