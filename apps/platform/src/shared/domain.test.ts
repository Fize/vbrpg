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

  it("bounded external commands keep the platform's two side effects", () => {
    const scheduled = parseExternalCommand({
      commandId: "command-1",
      instanceId: "instance-1",
      type: "schedule",
      runAtMs: 1_700_000_000_000,
      job: "timerExpired",
    });
    expect(scheduled.type).toBe("schedule");

    const emitted = parseExternalCommand({
      commandId: "command-2",
      instanceId: "instance-1",
      type: "emit",
      eventName: "night-started",
      payload: { day: 2 },
    });
    expect(emitted.type).toBe("emit");

    // The platform cannot execute an AI command yet, so it is not part of the contract.
    expect(() => parseExternalCommand({
      commandId: "command-3",
      instanceId: "instance-1",
      type: "aiGenerate",
      agentId: "seer",
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
