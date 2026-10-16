import { describe, expect, it } from "vitest";
import type { GameEvent, GameState, Participant } from "../../shared/index.js";
import { platformEventTypes } from "../../shared/index.js";
import { EngineError, projectPlayerView, resolveVisibility } from "../game/index.js";
import { undercover } from "./undercover.js";

const SEATS: Participant[] = ["p1", "p2", "p3", "p4"].map((key) => ({
  participantId: key,
  control: "human",
  status: "active",
}));

/** The platform's loop, in miniature: assign the sequence, apply the rule, follow derived events. */
function apply(
  state: GameState,
  events: Array<{ type: string; actor?: string; payload?: Record<string, unknown> }>,
): GameState {
  let current = state;
  for (const input of events) {
    const queue: GameEvent[] = [
      {
        eventId: `${input.type}-${current.sequence + 1}`,
        instanceId: current.instanceId,
        sequence: current.sequence + 1,
        type: input.type,
        participantId: input.actor ?? null,
        actorUserId: null,
        stepId: current.stepId,
        occurredAtMs: 0,
        idempotencyKey: `${input.type}-${current.sequence + 1}`,
        payload: input.payload ?? {},
        usage: null,
      },
    ];
    while (queue.length > 0) {
      const event = queue.shift();
      if (!event) break;
      const row = { ...event, sequence: current.sequence + 1 };
      const result = undercover.transition(current, row);
      current = { ...result.state, sequence: row.sequence };
      for (const extra of result.events) queue.push(extra);
    }
  }
  return current;
}

function start(seed = "seed-1"): GameState {
  return undercover.initialState({
    instanceId: "instance-1",
    gameVersionId: "undercover@1.0.0",
    engineVersion: undercover.engineVersion,
    randomSeed: seed,
    participants: SEATS,
  });
}

function view(state: GameState, participantId: string) {
  return projectPlayerView(resolveVisibility(undercover.visibility, state), state, {
    kind: "participant",
    participantId,
  });
}

describe("undercover rules", () => {
  it("starts with everyone describing and deals exactly one undercover", () => {
    const state = start();
    expect(state.status).toBe("waiting");
    expect(state.stepId).toBe("describe");
    expect(state.waiting?.participantIds).toEqual(["p1", "p2", "p3", "p4"]);
    expect(state.participants.filter((seat) => seat.roleId === "undercover")).toHaveLength(1);
  });

  it("is deterministic for the same seed and different for another", () => {
    const deals = ["seed-1", "seed-1", "seed-2"].map((seed) => {
      const state = start(seed);
      return state.participants.map((seat) => seat.roleId).join(",");
    });
    expect(deals[0]).toBe(deals[1]);
    expect(deals[0]).not.toBe(deals[2]);
  });

  it("moves to the vote phase once every active seat has described", () => {
    const described = apply(
      start(),
      SEATS.map((seat) => ({
        type: platformEventTypes.seatMessage,
        actor: seat.participantId,
        payload: { text: "..." },
      })),
    );

    expect(described.stepId).toBe("vote");
    expect(described.waiting).toMatchObject({ stepId: "vote" });
    expect(described.variables["phase"]).toBe("vote");
    // The phase change is its own row, so the record explains why it happened.
    expect(described.sequence).toBe(SEATS.length + 1);
  });

  it("eliminates the most voted seat and ends the match when the undercover leaves", () => {
    const started = start();
    const undercoverSeat = started.participants.find((seat) => seat.roleId === "undercover")!;
    const others = started.participants.filter(
      (seat) => seat.participantId !== undercoverSeat.participantId,
    );

    const described = apply(
      started,
      SEATS.map((seat) => ({ type: platformEventTypes.seatMessage, actor: seat.participantId })),
    );
    const finished = apply(described, [
      ...others.map((seat) => ({
        type: "vote",
        actor: seat.participantId,
        payload: { target: undercoverSeat.participantId },
      })),
      {
        type: "vote",
        actor: undercoverSeat.participantId,
        payload: { target: others[0]!.participantId },
      },
    ]);

    expect(finished.status).toBe("completed");
    expect(finished.stepId).toBe("over");
    expect(finished.variables["winner"]).toBe("civilian");
    expect(
      finished.participants.find((seat) => seat.participantId === undercoverSeat.participantId)
        ?.status,
    ).toBe("eliminated");
  });

  it("keeps each word private and the ballots hidden from every seat", () => {
    const state = start();
    const words = state.participants.map((seat) => view(state, seat.participantId).privateState);
    // One private word per seat, and the undercover is the only one holding a different word.
    for (const [index, seat] of state.participants.entries()) {
      expect(Object.keys(words[index]!)).toEqual([`word:${seat.participantId}`]);
    }
    const distinct = new Set(words.map((entry) => Object.values(entry)[0]));
    expect(distinct.size).toBe(2);

    const voted = apply(
      state,
      SEATS.map((seat) => ({ type: platformEventTypes.seatMessage, actor: seat.participantId })),
    );
    const afterFirstVote = apply(voted, [{ type: "vote", actor: "p1", payload: { target: "p2" } }]);
    for (const seat of state.participants) {
      const projection = view(afterFirstVote, seat.participantId);
      expect(projection.publicState["votes"]).toBeUndefined();
      expect(projection.privateState["votes"]).toBeUndefined();
      expect(JSON.stringify(projection)).not.toContain('"votes"');
    }
  });

  it("shows the tally to everyone only after the round resolves", () => {
    const started = start();
    const described = apply(
      started,
      SEATS.map((seat) => ({ type: platformEventTypes.seatMessage, actor: seat.participantId })),
    );
    const resolved = apply(described, [
      { type: "vote", actor: "p1", payload: { target: "p2" } },
      { type: "vote", actor: "p2", payload: { target: "p1" } },
      { type: "vote", actor: "p3", payload: { target: "p1" } },
      { type: "vote", actor: "p4", payload: { target: "p1" } },
    ]);

    const summary = view(resolved, "p1").publicState["summary"] as { eliminated: string | null };
    expect(summary.eliminated).toBe("p1");
  });

  it("rejects illegal moves with the rule's own code", () => {
    const described = apply(
      start(),
      SEATS.map((seat) => ({ type: platformEventTypes.seatMessage, actor: seat.participantId })),
    );

    expect(() =>
      apply(described, [{ type: "vote", actor: "p1", payload: { target: "p1" } }]),
    ).toThrowError(EngineError);
    expect(() =>
      apply(described, [{ type: "vote", actor: "p1", payload: { target: "p9" } }]),
    ).toThrow(/not an active seat/);
    expect(() =>
      apply(start(), [{ type: "vote", actor: "p1", payload: { target: "p2" } }]),
    ).toThrow(/only accepted in the vote phase/);
  });

  it("records an unknown event type without touching the state", () => {
    const started = start();
    const after = apply(started, [{ type: "aiCall", payload: { content: "thinking" } }]);
    expect(after.variables).toEqual(started.variables);
    expect(after.stepId).toBe(started.stepId);
  });
});
