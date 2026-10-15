import { describe, expect, it } from "vitest";
import {
  gameEventSchema,
  parseExternalCommand,
  playerViewSchema,
} from "./domain.js";

describe("runtime contracts", () => {
  it("requires idempotency and logical time on events", () => {
    expect(() => gameEventSchema.parse({
      eventId: "event-1",
      instanceId: "instance-1",
      sequence: 1,
      type: "playerInputReceived",
      actor: null,
      payload: {},
    })).toThrow();
  });

  it("keeps external commands explicit and bounded", () => {
    const command = parseExternalCommand({
      commandId: "command-1",
      instanceId: "instance-1",
      type: "aiGenerate",
      agentId: "seer",
      input: { promptKey: "werewolf.vote" },
      timeoutMs: 10_000,
      maxAttempts: 2,
      fallbackNodeId: "fallback",
    });

    expect(command.type).toBe("aiGenerate");
    if (command.type !== "aiGenerate") {
      throw new Error("Expected an AI command");
    }
    expect(command.maxAttempts).toBe(2);
    expect(command.agentId).toBe("seer");
  });

  it("rejects an AI command without an agent", () => {
    expect(() => parseExternalCommand({
      commandId: "command-1",
      instanceId: "instance-1",
      type: "aiGenerate",
      input: {},
      timeoutMs: 10_000,
      maxAttempts: 1,
      fallbackNodeId: "fallback",
    })).toThrow();
  });

  it("accepts a degraded AI failure event", () => {
    const event = gameEventSchema.parse({
      eventId: "event-2",
      instanceId: "instance-1",
      sequence: 2,
      type: "aiFailed",
      actor: null,
      occurredAtMs: 0,
      idempotencyKey: "instance-1:2",
      payload: { reason: "PROVIDER_ERROR", attempts: 2 },
    });

    expect(event.type).toBe("aiFailed");
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
