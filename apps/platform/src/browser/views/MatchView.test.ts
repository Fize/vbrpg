import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import type { MatchDetail } from "../services/api";

const instanceId = "11111111-1111-1111-1111-111111111111";
const me = "22222222-2222-2222-2222-222222222222";
const other = "33333333-3333-3333-3333-333333333333";
const aiSeat = "44444444-4444-4444-4444-444444444444";

const detail: MatchDetail = {
  summary: {
    instanceId,
    gameId: "undercover",
    gameVersion: "1.0.0",
    status: "waiting",
    sequence: 4,
    stepId: "describe",
    createdAt: "2026-10-15T00:00:00.000Z",
    mySeatKeys: ["s1"],
  },
  game: {
    title: "谁是卧底",
    steps: { describe: "描述阶段", vote: "投票阶段" },
    words: { round: "回合", winner: "胜方", civilian: "平民", text: "你要说的话" },
  },
  seats: [
    {
      participantId: me,
      key: "s1",
      control: "human",
      status: "active",
      actorUserId: me,
      persona: {
        gender: "女",
        mbti: "INTJ",
        profession: "架构师",
        personality: "冷静、讲究结构",
        style: "句子短，先给结论",
      },
    },
    {
      participantId: other,
      key: "s2",
      control: "human",
      status: "active",
      actorUserId: null,
      persona: { gender: "男" },
    },
    {
      participantId: aiSeat,
      key: "s3",
      control: "ai",
      status: "active",
      actorUserId: null,
      persona: { gender: "女" },
    },
  ],
  waiting: {
    kind: "collectInput",
    stepId: "describe",
    participantIds: [me],
    actions: ["seatMessage"],
  },
  view: {
    instanceId,
    gameVersionId: "undercover@1.0.0",
    sequence: 4,
    status: "waiting",
    publicState: { phase: "describe", round: 1 },
    privateState: { [`word:${me}`]: "苹果" },
    availableActions: [{ actionId: "seatMessage", input: { participantId: me } }],
  },
  briefing: "你在玩「谁是卧底」。",
  record: [
    {
      eventId: "e1",
      sequence: 1,
      type: "instanceCreated",
      participantId: null,
      actorUserId: null,
      stepId: "start",
      occurredAtMs: 1_760_000_000_000,
      idempotencyKey: "k1",
      payload: {},
      usage: null,
    },
    {
      eventId: "e2",
      sequence: 2,
      type: "aiCall",
      participantId: aiSeat,
      actorUserId: null,
      stepId: "describe",
      occurredAtMs: 1_760_000_001_000,
      idempotencyKey: "k2",
      payload: {
        content: null,
        reasoning: "冬天常见，但我不确定是不是卧底。",
        toolCalls: [{ id: "c1", name: "seatMessage", arguments: '{"text":"我这东西冬天常见"}' }],
      },
      usage: {
        providerId: "55555555-5555-5555-5555-555555555555",
        modelId: "test-model",
        promptTokens: 500,
        completionTokens: 120,
        totalTokens: 620,
      },
    },
    {
      eventId: "e3",
      sequence: 3,
      type: "seatMessage",
      participantId: aiSeat,
      actorUserId: null,
      stepId: "describe",
      occurredAtMs: 1_760_000_002_000,
      idempotencyKey: "k3",
      payload: { text: "我这东西冬天常见" },
      usage: null,
    },
    {
      eventId: "e4",
      sequence: 4,
      type: "vote",
      participantId: me,
      actorUserId: me,
      stepId: "vote",
      occurredAtMs: 1_760_000_003_000,
      idempotencyKey: "k4",
      payload: { target: other },
      usage: null,
    },
  ],
  actions: [
    {
      name: "seatMessage",
      label: "描述",
      description: "用一句话描述你拿到的词，不要直接说出它。",
      args: { text: { description: "你要说的话" } },
      audience: "room",
    },
    {
      name: "vote",
      label: "投票",
      description: "投出你认为最像卧底的席位。",
      args: { target: { description: "要投的席位", kind: "seat" } },
      audience: "seat",
    },
  ],
};

/**
 * The discussion phase: passing is a move of its own, and it carries no words, so a seat that has
 * already spoken keeps its line on the table.
 */
const discussing: MatchDetail = {
  ...detail,
  summary: { ...detail.summary, stepId: "discuss", sequence: 5 },
  waiting: {
    kind: "collectInput",
    stepId: "discuss",
    participantIds: [other],
    actions: ["seatMessage", "skipDiscussion"],
  },
  view: {
    ...detail.view,
    sequence: 5,
    publicState: { phase: "discuss", round: 1, discussRound: 1 },
    availableActions: [],
  },
  record: [
    ...detail.record,
    {
      eventId: "e5",
      sequence: 5,
      type: "skipDiscussion",
      participantId: aiSeat,
      actorUserId: null,
      stepId: "discuss",
      occurredAtMs: 1_760_000_004_000,
      idempotencyKey: "k5",
      payload: {},
      usage: null,
    },
  ],
  actions: [
    ...detail.actions,
    {
      name: "skipDiscussion",
      label: "这轮不说",
      description: "这一轮你不发言，直接轮到下一位。",
      audience: "room",
    },
  ],
};

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { instanceId } }),
}));

const readMatch = vi.fn(async (_instanceId: string) => current);
vi.mock("../services/api", () => ({
  api: {
    readMatch: (id: string) => readMatch(id),
    submitMatchEvent: vi.fn(),
    setMatchStatus: vi.fn(),
  },
  apiRequestId: () => null,
}));

vi.mock("../stores/session", () => ({
  sessionState: { user: { id: me, username: "alice", role: "user", active: true } },
}));

/** The vote step asks for a seat: the catalogue's `kind` decides the control, not the name. */
const voting: MatchDetail = {
  ...detail,
  summary: { ...detail.summary, stepId: "vote", sequence: 5 },
  waiting: { kind: "collectInput", stepId: "vote", participantIds: [me], actions: ["vote"] },
  view: {
    ...detail.view,
    sequence: 5,
    publicState: { phase: "vote", round: 1 },
    availableActions: [{ actionId: "vote", input: { participantId: me } }],
  },
};

/**
 * What a watcher gets: the same public state, no private state, no actions, no rules.
 * The summary is the only place that says whether the caller is playing or watching.
 */
const watching: MatchDetail = {
  ...detail,
  summary: { ...detail.summary, mySeatKeys: [] },
  // No seat belongs to the caller: s1 and s2 are other people's, s3 is the AI's.
  seats: detail.seats.map((seat) => ({ ...seat, actorUserId: null })),
  view: {
    ...detail.view,
    privateState: {},
    availableActions: [],
  },
  briefing: null,
};

let current: MatchDetail = detail;

const MatchView = (await import("./MatchView.vue")).default;

async function render() {
  const wrapper = mount(MatchView, { global: { plugins: [ElementPlus] } });
  await flushPromises();
  return wrapper;
}

describe("match room", () => {
  beforeEach(() => {
    current = detail;
  });

  it("seats everyone around the table and says who the match is waiting for", async () => {
    const wrapper = await render();
    expect(readMatch).toHaveBeenCalledWith(instanceId);

    const text = wrapper.text();
    expect(wrapper.findAll("[data-testid='seat']")).toHaveLength(3);
    expect(text).toContain("s1");
    expect(text).toContain("s3");
    expect(text).toContain("我");
    expect(text).toContain("3席在场");
    expect(text).toContain("等 s1");
    // The seat's own material: the rules it is playing by and its private word.
    expect(text).toContain("你在玩「谁是卧底」");
    expect(text).toContain("苹果");
    // The word leads the column at display size — it is the seat's identity for the match.
    const secret = wrapper.find("[data-testid='my-secret']");
    expect(secret.text()).toContain("苹果");
    expect(secret.text()).not.toContain("只给你看的信息");
    // The rules are folded away: a wall of text must not push the word down the column.
    expect(wrapper.find("[data-testid='my-seat']").text()).toContain("这一局的规则");
    // Its latest line in the shared transcript is on the seat.
    expect(wrapper.find(".bubble").text()).toContain("我这东西冬天常见");
    // Its own persona, MBTI included; the table only ever sees the gender of the others.
    const card = wrapper.find("[data-testid='my-persona']").text();
    expect(card).toContain("INTJ");
    expect(card).toContain("架构师");
    expect(card).toContain("女");
    expect(wrapper.findAll("[data-testid='seat']").map((seat) => seat.text())).toContainEqual(
      expect.stringContaining("男"),
    );
  });

  it("promotes nothing when a seat holds more than one secret", async () => {
    current = {
      ...detail,
      view: {
        ...detail.view,
        privateState: { [`word:${me}`]: "苹果", [`hint:${me}`]: "水果" },
      },
    };
    const wrapper = await render();

    expect(wrapper.find("[data-testid='my-secret']").exists()).toBe(false);
    expect(wrapper.text()).toContain("其他只有你知道的信息");
    expect(wrapper.text()).toContain("苹果");
    expect(wrapper.text()).toContain("水果");
  });

  it("offers the seat's own action and describes it from the catalogue", async () => {
    const wrapper = await render();
    const dock = wrapper.find("[data-testid='my-actions']");

    expect(dock.text()).toContain("描述");
    expect(dock.text()).toContain("用一句话描述你拿到的词");
    expect(wrapper.find("input[placeholder='你要说的话']").exists()).toBe(true);
    expect(dock.find("button").text()).toContain("提交");
  });

  it("reads the record as a log, and only expands the model's thinking on demand", async () => {
    const wrapper = await render();
    const log = wrapper.find("[data-testid='match-log']");

    expect(log.text()).toContain("发言");
    expect(log.text()).toContain("模型");
    // Everything a reader sees is in the game's own words: the payload keys are the action's
    // argument names, and the usage is labelled instead of being three anonymous numbers.
    expect(log.text()).toContain("你要说的话：我这东西冬天常见");
    expect(log.text()).toContain("描述");
    expect(log.text()).toContain("test-model · 输入 500 · 输出 120 · 合计 620");
    // A secret ballot is a seat-audience row, so the log names the seat it came from.
    expect(log.text()).toContain("s2");
    expect(log.text()).not.toContain("冬天常见，但我不确定是不是卧底。");

    const detailed = wrapper.find("input[value='detailed']");
    await detailed.setValue();
    expect(wrapper.find("[data-testid='match-log']").text()).toContain(
      "冬天常见，但我不确定是不是卧底。",
    );
  });

  it("tells a watcher it is watching and offers it no action", async () => {
    current = watching;
    const wrapper = await render();

    const text = wrapper.text();
    expect(text).toContain("观战中");
    expect(text).not.toContain("只给你看的信息");
    expect(text).not.toContain("你在玩「谁是卧底」");
    expect(wrapper.find("[data-testid='my-actions']").text()).toContain("旁观没有动作可提交");
    expect(wrapper.find("[data-testid='my-actions'] button").exists()).toBe(false);
    expect(wrapper.find("[data-testid='my-persona']").exists()).toBe(false);
    // The table, the waiting point and the log stay available to a watcher.
    expect(wrapper.findAll("[data-testid='seat']")).toHaveLength(3);
    expect(text).toContain("等 s1");
    expect(wrapper.find("[data-testid='match-log']").text()).toContain("发言");
    // Public state is not a seat's secret: the phase shows, the word does not.
    expect(text).toContain("describe");
    expect(text).not.toContain("苹果");
  });

  it("renders a seat picker for an action whose catalogue declares one", async () => {
    current = voting;
    const wrapper = await render();

    const dock = wrapper.find("[data-testid='my-actions']");
    expect(dock.text()).toContain("投票");
    expect(dock.text()).toContain("投出你认为最像卧底的席位。");
    expect(dock.text()).toContain("私密");
    // A seat argument is a picker over this match's seats, not a free-text field.
    expect(dock.findAll(".el-select")).toHaveLength(1);
    expect(dock.find(".el-select").text()).toContain("要投的席位");
  });

  it("keeps a seat's line on the table when it passes a discussion round", async () => {
    current = discussing;
    const wrapper = await render();

    // The pass is recorded, but it must not push aside what the seat already said.
    expect(wrapper.find("[data-testid='match-log']").text()).toContain("这轮不说");
    expect(wrapper.find(".bubble").text()).toContain("我这东西冬天常见");
    expect(wrapper.text()).not.toContain("（无内容）");
  });
});
