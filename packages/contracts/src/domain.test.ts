import { describe, expect, it } from "vitest";
import {
  gameDefinitionSchema,
  gameEventSchema,
  parseCreateInstanceRequest,
  parseExternalCommand,
  parseSubmitEventRequest,
  playerViewSchema,
} from "./domain.js";

const definition = {
  manifest: {
    gameId: "werewolf",
    slug: "werewolf",
    version: "1.0.0",
    dslVersion: "0.1",
    engineVersion: "native-0.1",
    authorId: "author-1",
    license: "CC-BY-4.0",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", next: ["wait"], config: {} },
      { id: "wait", type: "waitForPlayerInput", next: ["end"], config: {} },
      { id: "end", type: "end", next: [], config: {} },
    ],
  },
};

describe("contracts v0", () => {
  it("parses a minimal game definition and applies defaults", () => {
    const parsed = gameDefinitionSchema.parse(definition);

    expect(parsed.roles).toEqual([]);
    expect(parsed.workflow.nodes[0]?.next).toEqual(["wait"]);
  });

  it("keeps agent declarations version-scoped and bounded", () => {
    const parsed = gameDefinitionSchema.parse({
      ...definition,
      agents: [{
        id: "seer",
        roleId: "seer",
        systemPrompt: "You are the seer.",
        limits: { timeoutMs: 5_000, maxAttempts: 2, tokenBudget: 131_072 },
      }],
    });
    expect(parsed.agents[0]?.limits.tokenBudget).toBe(131_072);

    // An agent without limits cannot be bounded at runtime, so it cannot be published.
    expect(() => gameDefinitionSchema.parse({
      ...definition,
      agents: [{ id: "seer", roleId: "seer", systemPrompt: "You are the seer." }],
    })).toThrow();
    expect(gameDefinitionSchema.parse(definition).agents).toEqual([]);
  });

  it("rejects a definition with an invalid game slug", () => {
    expect(() => gameDefinitionSchema.parse({
      ...definition,
      manifest: { ...definition.manifest, slug: "Werewolf Game" },
    })).toThrow();
  });

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

  it("keeps AI commands explicit and bounded", () => {
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

  it("rejects an AI command without an agent binding target", () => {
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

  it("derives nothing client-side: instance and event requests are strict", () => {
    const create = parseCreateInstanceRequest({ gameVersionId: "version-1" });
    expect(create.participants).toEqual([]);
    expect(create.randomSeed).toBeUndefined();

    expect(() => parseCreateInstanceRequest({ gameVersionId: "version-1", instanceId: "mine" })).toThrow();
    expect(() =>
      parseCreateInstanceRequest({ gameVersionId: "version-1", randomSeed: "" }),
    ).toThrow();

    expect(parseSubmitEventRequest({ type: "playerInputReceived", payload: { nodeId: "vote" } })).toEqual({
      type: "playerInputReceived",
      payload: { nodeId: "vote" },
    });
    // Timers, AI results and admin commands are server-side only.
    expect(() => parseSubmitEventRequest({ type: "timerExpired", payload: {} })).toThrow();
    expect(() => parseSubmitEventRequest({ type: "playerInputReceived", payload: {}, sequence: 9 })).toThrow();
  });

  it("represents a player projection separately from authority state", () => {
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
