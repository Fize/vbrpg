import { describe, expect, it } from "vitest";
import {
  gameDefinitionSchema,
  gameEventSchema,
  parseExternalCommand,
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
