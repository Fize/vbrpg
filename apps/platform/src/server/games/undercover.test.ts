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

const WORDS = { civilianWord: "咖啡", undercoverWord: "茶" };

function start(seed = "seed-1", variables: Record<string, unknown> = WORDS): GameState {
  return undercover.initialState({
    instanceId: "instance-1",
    gameVersionId: "undercover@1.0.0",
    engineVersion: undercover.engineVersion,
    randomSeed: seed,
    participants: SEATS,
    variables,
  });
}

/** Everyone describes in turn: the first phase owes the table one line per seat. */
function describeAll(state: GameState): GameState {
  return apply(
    state,
    (state.waiting?.participantIds ?? []).map((seat) => ({
      type: platformEventTypes.seatMessage,
      actor: seat,
      payload: { text: "..." },
    })),
  );
}

/** The table talks through `rounds` discussion rounds; a quiet seat passes instead of speaking. */
function discussAll(state: GameState, rounds = 3): GameState {
  let current = state;
  for (let round = 0; round < rounds; round += 1) {
    current = apply(
      current,
      (current.waiting?.participantIds ?? []).map((seat) => ({
        type: "skipDiscussion",
        actor: seat,
      })),
    );
  }
  return current;
}

function view(state: GameState, participantId: string) {
  return projectPlayerView(resolveVisibility(undercover.visibility, state), state, {
    kind: "participant",
    participantId,
  });
}

describe("undercover rules", () => {
  it("refuses to start without the table's words", () => {
    expect(() => start("seed-1", {})).toThrowError(/civilianWord/);
    expect(() => start("seed-1", { civilianWord: "咖啡" })).toThrowError(/undercoverWord/);
    expect(() => start("seed-1", { civilianWord: "  ", undercoverWord: "茶" })).toThrowError(
      /civilianWord/,
    );
    expect(() => start("seed-1", { civilianWord: "咖啡", undercoverWord: "咖啡" })).toThrowError(
      /must differ/,
    );
  });

  it("deals the words it was given", () => {
    const state = start("seed-1", { civilianWord: "地铁", undercoverWord: "公交" });
    const words = SEATS.map((seat) => state.variables[`word:${seat.participantId}`]);
    expect(words.filter((word) => word === "公交")).toHaveLength(1);
    expect(words.filter((word) => word === "地铁")).toHaveLength(3);
  });

  it("starts with everyone describing and deals exactly one undercover", () => {
    const state = start();
    expect(state.status).toBe("waiting");
    expect(state.stepId).toBe("describe");
    expect(state.waiting?.participantIds).toEqual(["p1", "p2", "p3", "p4"]);
    // The describe phase owes a line: passing is a discussion move, not a describe move.
    expect(state.waiting?.actions).toEqual([platformEventTypes.seatMessage]);
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

  it("moves to the discussion once every active seat has described", () => {
    const described = describeAll(start());

    expect(described.stepId).toBe("discuss");
    expect(described.waiting).toMatchObject({ stepId: "discuss" });
    expect(described.variables["phase"]).toBe("discuss");
    expect(described.variables["discussRound"]).toBe(1);
    // The discussion offers both moves: say something, or pass this round.
    expect(described.waiting?.actions).toEqual([platformEventTypes.seatMessage, "skipDiscussion"]);
    // The phase change is its own row, so the record explains why it happened.
    expect(described.sequence).toBe(SEATS.length + 1);
  });

  it("ends the discussion after three rounds and narrows the table to a vote", () => {
    const described = describeAll(start());
    const roundOne = apply(described, [
      { type: platformEventTypes.seatMessage, actor: "p1", payload: { text: "第一个说" } },
      { type: "skipDiscussion", actor: "p2" },
      { type: "skipDiscussion", actor: "p3" },
      { type: "skipDiscussion", actor: "p4" },
    ]);

    expect(roundOne.variables["discussRound"]).toBe(2);
    // The round change is a row of its own, and it resets who has been heard.
    expect(roundOne.variables["discussed"]).toEqual([]);
    expect(roundOne.waiting?.participantIds).toEqual(["p1", "p2", "p3", "p4"]);

    const lastRound = discussAll(described, 2);
    expect(lastRound.variables["discussRound"]).toBe(3);
    const voted = discussAll(lastRound, 1);
    expect(voted.stepId).toBe("vote");
    expect(voted.variables["phase"]).toBe("vote");
    expect(voted.waiting?.actions).toEqual(["vote"]);
  });

  it("refuses a second line in the same discussion round and any line after it", () => {
    const described = describeAll(start());
    const spoke = apply(described, [
      { type: platformEventTypes.seatMessage, actor: "p1", payload: { text: "我说了" } },
    ]);

    expect(() =>
      apply(spoke, [
        { type: platformEventTypes.seatMessage, actor: "p1", payload: { text: "又说" } },
      ]),
    ).toThrow(/already spoken this round/);
    expect(() =>
      apply(spoke, [
        { type: "skipDiscussion", actor: "p2" },
        { type: "skipDiscussion", actor: "p2" },
      ]),
    ).toThrow(/already spoken this round/);
    expect(() =>
      apply(discussAll(described, 3), [
        { type: platformEventTypes.seatMessage, actor: "p1", payload: { text: "还想说" } },
      ]),
    ).toThrow(/discussion is over/);
    expect(() =>
      apply(discussAll(described, 3), [{ type: "skipDiscussion", actor: "p1" }]),
    ).toThrow(/Only a discussion round can be skipped/);
    expect(() => apply(start(), [{ type: "skipDiscussion", actor: "p1" }])).toThrow(
      /Only a discussion round can be skipped/,
    );
  });

  it("counts only the seats still in the round, and a round resets on elimination", () => {
    const described = describeAll(start());
    const undercoverSeat = described.participants.find((seat) => seat.roleId === "undercover")!;
    const alive = described.variables["alive"] as string[];
    const doomed = alive.find((seat) => seat !== undercoverSeat.participantId)!;

    const resolved = apply(
      discussAll(described, 3),
      alive.map((seat) => ({
        type: "vote",
        actor: seat,
        payload: { target: seat === doomed ? undercoverSeat.participantId : doomed },
      })),
    );

    expect(resolved.variables["phase"]).toBe("describe");
    expect(resolved.variables["alive"]).not.toContain(doomed);
    expect(resolved.variables["discussRound"]).toBe(1);
    // The seat that left is never waited for again — not in the describe round, not in discussions.
    expect(resolved.waiting?.participantIds).toEqual(alive.filter((seat) => seat !== doomed));
    expect(() =>
      apply(resolved, [
        { type: platformEventTypes.seatMessage, actor: doomed, payload: { text: "?" } },
      ]),
    ).toThrow(/not part of the round/);
  });

  it("eliminates the most voted seat and ends the match when the undercover leaves", () => {
    const started = start();
    const undercoverSeat = started.participants.find((seat) => seat.roleId === "undercover")!;
    const others = started.participants.filter(
      (seat) => seat.participantId !== undercoverSeat.participantId,
    );

    const described = discussAll(describeAll(started), 3);
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

    const voted = discussAll(describeAll(state), 3);
    const afterFirstVote = apply(voted, [{ type: "vote", actor: "p1", payload: { target: "p2" } }]);
    for (const seat of state.participants) {
      const projection = view(afterFirstVote, seat.participantId);
      expect(projection.publicState["votes"]).toBeUndefined();
      expect(projection.privateState["votes"]).toBeUndefined();
      expect(JSON.stringify(projection)).not.toContain('"votes"');
    }
  });

  it("shows the tally to everyone only after the round resolves", () => {
    const described = discussAll(describeAll(start()), 3);
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
    const described = discussAll(describeAll(start()), 3);

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
