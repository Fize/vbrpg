import { describe, expect, it } from "vitest";
import type { GameAction, MatchRecordRow } from "./api";
import { buildLog } from "./match-log";

const actions: GameAction[] = [
  { name: "seatMessage", description: "描述你的词", args: { text: { description: "话" } }, audience: "room" },
  {
    name: "vote",
    description: "投票",
    args: { target: { description: "席位", kind: "seat" } },
    audience: "seat",
  },
];

const names: Record<string, string> = { "p-1": "s1", "p-2": "s2" };
const seatName = (id: string | null) => (id === null ? "平台" : (names[id] ?? id));

function row(overrides: Partial<MatchRecordRow> & Pick<MatchRecordRow, "type">): MatchRecordRow {
  return {
    eventId: overrides.type,
    sequence: 1,
    participantId: null,
    actorUserId: null,
    stepId: "describe",
    occurredAtMs: 0,
    idempotencyKey: "k",
    payload: {},
    usage: null,
    ...overrides,
  };
}

describe("match log", () => {
  it("names each row by the platform's vocabulary and the game's catalogue", () => {
    const entries = buildLog({
      record: [
        row({ type: "instanceCreated" }),
        row({ type: "seatMessage", participantId: "p-1", payload: { text: "很甜" } }),
        row({ type: "vote", participantId: "p-1", payload: { target: "p-2" } }),
        row({ type: "describePhaseEnded", payload: { round: 1 } }),
        row({
          type: "aiCall",
          participantId: "p-2",
          payload: { reasoning: "他在描述水果", toolCalls: [{ id: "c1", name: "vote", arguments: "{}" }] },
          usage: { providerId: "pv", modelId: "m", promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        }),
      ],
      actions,
      seatName,
    });

    expect(entries.map((entry) => entry.kind)).toEqual([
      "system",
      "speech",
      "private",
      "phase",
      "model",
    ]);
    // A seat declared by the catalogue reads as a seat, not as a raw id.
    expect(entries[2]?.text).toBe("target: s2");
    expect(entries[1]?.text).toBe("text: 很甜");
    expect(entries[4]?.model?.reasoning).toBe("他在描述水果");
    expect(entries[4]?.model?.toolCalls).toEqual([{ name: "vote", arguments: "{}" }]);
    expect(entries[4]?.model?.usage).toBe("m · 10/5/15");
    expect(entries[4]?.seat).toBe("s2");
  });

  it("keeps derived game events out of the model's or the seats' buckets", () => {
    const [entry] = buildLog({
      record: [row({ type: "votesRevealed", payload: { round: 2 } })],
      actions,
      seatName,
    });
    expect(entry?.kind).toBe("phase");
    expect(entry?.label).toBe("投票结算");
    expect(entry?.text).toBe("round: 2");
  });

  it("does not invent a kind for a type nobody declared", () => {
    const [entry] = buildLog({ record: [row({ type: "somethingNew" })], actions, seatName });
    expect(entry?.kind).toBe("phase");
    expect(entry?.label).toBe("somethingNew");
  });
});
