import assert from "node:assert/strict";
import { describe, it } from "vitest";
import type { GameModule } from "../game/index.js";
import { resolveSeatReferences } from "./seat-reference.js";

const game = {
  actions: [
    {
      name: "vote",
      label: "投票",
      description: "投出你认为最像卧底的席位",
      args: { target: { description: "要投的席位", kind: "seat" } },
      audience: "seat",
    },
    {
      name: "seatMessage",
      label: "描述",
      description: "描述你的词",
      args: { text: { description: "话" } },
    },
  ],
} as unknown as GameModule;

const seats = { s1: "id-1", s2: "id-2", s3: "id-3" };

describe("seat references", () => {
  it("turns a seat name into the participant id the rules expect", () => {
    const resolved = resolveSeatReferences({
      game,
      actionType: "vote",
      payload: { target: "s2" },
      seats,
    });
    assert.deepEqual(resolved, { target: "id-2" });
  });

  it("leaves an id, an unknown name and non-seat arguments alone", () => {
    assert.deepEqual(
      resolveSeatReferences({ game, actionType: "vote", payload: { target: "id-3" }, seats }),
      { target: "id-3" },
      "an id resolves to itself",
    );
    assert.deepEqual(
      resolveSeatReferences({ game, actionType: "vote", payload: { target: "s9" }, seats }),
      { target: "s9" },
      "the game decides what to do with a name nobody has",
    );
    assert.deepEqual(
      resolveSeatReferences({
        game,
        actionType: "seatMessage",
        payload: { text: "s2" },
        seats,
      }),
      { text: "s2" },
      "only arguments the game declared as seats are touched",
    );
    assert.deepEqual(
      resolveSeatReferences({ game, actionType: "unknown", payload: { target: "s2" }, seats }),
      { target: "s2" },
      "an action nobody declared has no seat arguments to resolve",
    );
  });
});
