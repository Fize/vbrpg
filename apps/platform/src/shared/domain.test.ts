import { describe, expect, it } from "vitest";
import { gameEventSchema, platformEventTypes, playerViewSchema } from "./domain.js";

describe("runtime contracts", () => {
  it("requires idempotency and logical time on events", () => {
    expect(() =>
      gameEventSchema.parse({
        eventId: "event-1",
        instanceId: "instance-1",
        sequence: 1,
        type: "playerInputReceived",
        participantId: "p1",
        actorUserId: null,
        stepId: null,
        payload: {},
      }),
    ).toThrow();
  });

  it("carries a seat's reasoning and reply on a model-call row", () => {
    const row = gameEventSchema.parse({
      eventId: "event-2",
      instanceId: "instance-1",
      sequence: 2,
      type: platformEventTypes.aiCall,
      participantId: "p1",
      actorUserId: null,
      stepId: "night-1",
      occurredAtMs: 1_700_000_000_000,
      idempotencyKey: "instance-1:night-1:p1:0",
      payload: { content: "I will vote for p2", reasoning: "p2 spoke early" },
      usage: {
        providerId: "provider-1",
        modelId: "deepseek-chat",
        promptTokens: 1200,
        completionTokens: 42,
        totalTokens: 1242,
      },
    });

    expect(row.type).toBe("aiCall");
    expect(row.usage?.totalTokens).toBe(1242);
  });

  it("leaves usage empty on rows that are not model calls", () => {
    const row = gameEventSchema.parse({
      eventId: "event-3",
      instanceId: "instance-1",
      sequence: 3,
      type: platformEventTypes.seatMessage,
      participantId: "p1",
      actorUserId: "user-1",
      stepId: "day-1",
      occurredAtMs: 0,
      idempotencyKey: "instance-1:3",
      payload: { text: "good morning" },
      usage: null,
    });

    expect(row.usage).toBeNull();
    expect(row.actorUserId).toBe("user-1");
  });

  it("represents a player projection separately from authoritative state", () => {
    const view = playerViewSchema.parse({
      instanceId: "instance-1",
      gameVersionId: "version-1",
      sequence: 4,
      status: "waiting",
      publicState: { phase: "night" },
      privateState: { role: "seer" },
      availableActions: [],
    });

    expect(view.privateState).toEqual({ role: "seer" });
    expect(view.publicState).not.toBe(view.privateState);
  });
});
