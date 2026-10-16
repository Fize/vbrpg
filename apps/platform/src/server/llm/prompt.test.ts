import { describe, expect, it } from "vitest";
import { platformEventTypes } from "../../shared/index.js";
import { projectPlayerView, resolveVisibility } from "../game/index.js";
import { undercover } from "../games/undercover.js";
import { buildSeatPrompt } from "./prompt.js";

const SEATS = ["p1", "p2", "p3", "p4"].map((key) => ({
  participantId: key,
  control: "human" as const,
  status: "active" as const,
}));
const KEYS: Record<string, string> = { p1: "alice", p2: "bob", p3: "carol", p4: "dave" };

function started() {
  return undercover.initialState({
    instanceId: "instance-1",
    gameVersionId: "undercover@1.0.0",
    engineVersion: undercover.engineVersion,
    randomSeed: "seed-1",
    participants: SEATS,
    variables: { civilianWord: "咖啡", undercoverWord: "茶" },
  });
}

function seatId(state: ReturnType<typeof started>, index: number): string {
  return state.participants[index]!.participantId;
}

describe("seat prompt", () => {
  it("keeps the rules and the seat's own secret in the system block", () => {
    const state = started();
    const me = seatId(state, 1);
    const prompt = buildSeatPrompt({
      game: undercover,
      state,
      participantId: me,
      seatKeys: KEYS,
      record: [],
    });

    const view = projectPlayerView(resolveVisibility(undercover.visibility, state), state, {
      kind: "participant",
      participantId: me,
    });
    const word = Object.values(view.privateState)[0] as string;

    expect(prompt.system).toContain("谁是卧底");
    expect(prompt.system).toContain(KEYS[me]!);
    // The word comes from the projection, never from the raw state, and it is stable for the
    // match so it can live in the cached header.
    expect(prompt.system).toContain(word);
    expect(prompt.messages[prompt.messages.length - 1]?.content).not.toContain(word);
  });

  it("names the table's seats so no seat id has to be reproduced", () => {
    const state = started();
    const built = buildSeatPrompt({
      game: undercover,
      state,
      participantId: seatId(state, 1),
      seatKeys: KEYS,
      record: [],
    });
    expect(built.system).toContain("桌上的席位：alice、bob、carol、dave");
    expect(built.system).toContain("参数里写它的席位名");
    expect(built.system).toContain("不要写内部 id");
    // The seat table is part of the cacheable prefix: it must not be derived per turn.
    expect(built.system).not.toContain(seatId(state, 0));
  });

  it("offers the whole catalogue as tools, not just this step's subset", () => {
    const state = started();
    const prompt = buildSeatPrompt({
      game: undercover,
      state,
      participantId: seatId(state, 0),
      seatKeys: KEYS,
      record: [],
    });

    expect(prompt.tools.map((tool) => tool.name).sort()).toEqual(["seatMessage", "vote"]);
    expect(prompt.messages.at(-1)?.content).toContain("本步允许的动作：seatMessage");
    expect(prompt.tools.find((tool) => tool.name === "vote")?.parameters.required).toEqual([
      "target",
    ]);
  });

  it("renders speech as user turns, hides secret ballots, and replays its own call", () => {
    const state = started();
    const me = seatId(state, 0);
    const other = seatId(state, 1);
    const prompt = buildSeatPrompt({
      game: undercover,
      state,
      participantId: me,
      seatKeys: KEYS,
      record: [
        { sequence: 1, type: "instanceCreated", participantId: null, payload: {} },
        {
          sequence: 2,
          type: platformEventTypes.seatMessage,
          participantId: other,
          payload: { text: "我说说钢琴" },
        },
        { sequence: 3, type: "vote", participantId: other, payload: { target: "secret-target" } },
        {
          sequence: 4,
          type: "aiCall",
          participantId: me,
          payload: {
            content: null,
            reasoning: "先拥护 carol",
            toolCalls: [{ id: "call-1", name: "vote", arguments: '{"target":"carol"}' }],
          },
        },
      ],
    });

    expect(prompt.messages[0]).toEqual({ role: "user", content: "[bob] 我说说钢琴" });
    // A secret ballot from another seat must not appear anywhere in the prompt.
    expect(JSON.stringify(prompt.messages)).not.toContain("secret-target");
    expect(prompt.messages[1]).toMatchObject({
      role: "assistant",
      reasoningContent: "先拥护 carol",
      toolCalls: [{ id: "call-1", name: "vote", arguments: '{"target":"carol"}' }],
    });
    expect(prompt.messages[2]).toMatchObject({ role: "tool", toolCallId: "call-1" });
  });

  it("keeps the cacheable prefix byte-identical as the match goes on", () => {
    const state = started();
    const me = seatId(state, 0);
    const first = buildSeatPrompt({
      game: undercover,
      state,
      participantId: me,
      seatKeys: KEYS,
      record: [],
    });

    const later = buildSeatPrompt({
      game: undercover,
      state: {
        ...state,
        variables: { ...state.variables, round: 2, summary: { round: 1, eliminated: null } },
        waiting: { ...state.waiting!, stepId: "vote", actions: ["vote"] },
      },
      participantId: me,
      seatKeys: KEYS,
      record: [
        {
          sequence: 2,
          type: platformEventTypes.seatMessage,
          participantId: seatId(state, 1),
          payload: { text: "x" },
        },
      ],
    });

    // The tools and the system block never move, so the provider can reuse its cached prefix.
    expect(later.tools).toEqual(first.tools);
    expect(later.system).toBe(first.system);
    // Everything volatile lives in the last message.
    expect(later.messages.at(-1)?.content).toContain("本步允许的动作：vote");
    expect(later.messages.at(-1)?.content).toContain('"round":2');
    expect(JSON.stringify(later.messages.slice(0, -1))).not.toContain('"round"');
    expect(later.system).toContain("只有你知道自己的私有信息");
  });
});
