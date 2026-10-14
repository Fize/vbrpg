import { describe, expect, it } from "vitest";
import type { GameDefinition } from "@vbrpg/contracts";
import { validateGameDefinition } from "./validator.js";

function definition(overrides: Partial<GameDefinition["workflow"]> = {}): GameDefinition {
  return {
    manifest: {
      gameId: "game-1",
      slug: "validator-test",
      version: "1.0.0",
      dslVersion: "v0",
      engineVersion: "native-test",
      authorId: "user-1",
      license: "MIT",
    },
    workflow: {
      entryNodeId: "start",
      nodes: [
        { id: "start", type: "start", config: {}, next: ["wait"] },
        {
          id: "wait",
          type: "waitForPlayerInput",
          config: { inputKey: "answer", participantId: "p1" },
          next: ["end"],
        },
        { id: "end", type: "end", config: {}, next: [] },
      ],
      ...overrides,
    },
    roles: [],
    variables: {},
    visibility: {},
    presentation: {},
  };
}

describe("workflow definition validator", () => {
  it("accepts a reachable workflow with a terminal node", () => {
    expect(validateGameDefinition(definition())).toEqual({ valid: true, issues: [] });
  });

  it("rejects missing references and unreachable nodes", () => {
    const result = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["missing"] },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );
    expect(result.valid).toBe(false);
    expect(result.issues.map((issue) => issue.code)).toEqual(
      expect.arrayContaining(["UNKNOWN_NODE_REFERENCE", "UNREACHABLE_NODE", "NO_REACHABLE_END"]),
    );
  });

  it("requires an agent on every AI node", () => {
    const result = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["ai"] },
          {
            id: "ai",
            type: "aiGenerate",
            config: { timeoutMs: 5_000, maxAttempts: 1, fallbackNodeId: "end", input: {}, resultKey: "out" },
            next: ["end"],
          },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );

    expect(result.valid).toBe(false);
    expect(result.issues.map((issue) => issue.code)).toContain("INVALID_CONFIG");
  });

  it("rejects implicit cycles and invalid AI configuration", () => {
    const result = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["ai"] },
          {
            id: "ai",
            type: "aiGenerate",
            config: { agentId: "seer", timeoutMs: 0, maxAttempts: 1, fallbackNodeId: "start", input: [] },
            next: ["start"],
          },
        ],
      }),
    );
    expect(result.valid).toBe(false);
    expect(result.issues.map((issue) => issue.code)).toEqual(
      expect.arrayContaining(["INVALID_CONFIG", "IMPLICIT_CYCLE", "NO_REACHABLE_END"]),
    );
  });
});
