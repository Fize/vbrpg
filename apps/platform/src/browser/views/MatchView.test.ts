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
  },
  seats: [
    { participantId: me, key: "s1", control: "human", status: "active", actorUserId: me },
    { participantId: other, key: "s2", control: "human", status: "active", actorUserId: null },
    { participantId: aiSeat, key: "s3", control: "ai", status: "active", actorUserId: null },
  ],
  waiting: { kind: "collectInput", stepId: "describe", participantIds: [me], actions: ["seatMessage"] },
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
      sequence: 3,
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
      description: "用一句话描述你拿到的词，不要直接说出它。",
      args: { text: { description: "你要说的话" } },
      audience: "room",
    },
    {
      name: "vote",
      description: "投出你认为最像卧底的席位。",
      args: { target: { description: "要投的席位", kind: "seat" } },
      audience: "seat",
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
  sessionState: { user: { id: me, username: "alice", role: "admin", active: true } },
}));

/** The vote phase asks for a seat: the catalogue's `kind` decides the control, not the name. */
const voting: MatchDetail = {
  ...detail,
  summary: { ...detail.summary, stepId: "vote", sequence: 5 },
  waiting: { kind: "collectInput", stepId: "vote", participantIds: [me], actions: ["vote"] },
  view: {
    ...detail.view!,
    sequence: 5,
    publicState: { phase: "vote", round: 1 },
    availableActions: [{ actionId: "vote", input: { participantId: me } }],
  },
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

  it("shows the seats, the waiting point and the seat's own action form", async () => {
    const wrapper = await render();
    expect(readMatch).toHaveBeenCalledWith(instanceId);

    const text = wrapper.text();
    expect(text).toContain("s1");
    expect(text).toContain("AI");
    expect(text).toContain("等待 s1");
    expect(text).toContain("苹果");
    expect(text).toContain("你在玩「谁是卧底」");

    // The catalogue drives the form: no invented inputs, no hardcoded game knowledge.
    const inputs = wrapper.findAll("textarea, input");
    expect(inputs.length).toBeGreaterThan(0);
    expect(wrapper.find("[data-testid='my-actions']").exists()).toBe(true);
  });

  it("renders the record with the model's reasoning, tool call and usage", async () => {
    const wrapper = await render();
    const recordTab = wrapper.findAll(".el-tabs__item").find((item) => item.text() === "记录");
    expect(recordTab).toBeDefined();
    await recordTab?.trigger("click");
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain("模型调用");
    expect(text).toContain("冬天常见，但我不确定是不是卧底。");
    expect(text).toContain('seatMessage({"text":"我这东西冬天常见"})');
    expect(text).toContain("test-model · 500/120/620");
    expect(text).toContain("s2");
  });

  it("renders a seat picker for an action whose catalogue declares one", async () => {
    current = voting;
    const wrapper = await render();

    expect(wrapper.text()).toContain("vote");
    expect(wrapper.text()).toContain("投出你认为最像卧底的席位。");
    // A seat argument is a picker over this match's seats, not a free-text field.
    const picker = wrapper.find(".el-select");
    expect(wrapper.findAll(".el-select").length).toBe(1);
    expect(picker.text()).toContain("要投的席位");
    expect(picker.findAll(".el-select__wrapper").length).toBe(1);
  });
});
