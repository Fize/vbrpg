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
    agents: [],
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

  it("validates random nodes and rejects unimplemented node types", () => {
    const randomNode = { id: "roll", type: "random" as const, config: { key: "roll", min: 1, max: 6 }, next: ["end"] };
    const valid = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["roll"] },
          randomNode,
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );
    expect(valid).toEqual({ valid: true, issues: [] });

    const inverted = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["roll"] },
          { ...randomNode, config: { key: "roll", min: 6, max: 1 } },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );
    expect(inverted.issues.map((issue) => issue.message)).toContain("random requires max >= min");

    const missingBounds = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["roll"] },
          { ...randomNode, config: { key: "roll" } },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );
    expect(missingBounds.issues.filter((issue) => issue.code === "INVALID_CONFIG")).toHaveLength(2);

    for (const type of ["subflow", "parallel", "join"] as const) {
      const unsupported = validateGameDefinition(
        definition({
          nodes: [
            { id: "start", type: "start", config: {}, next: ["node"] },
            { id: "node", type, config: {}, next: ["end"] },
            { id: "end", type: "end", config: {}, next: [] },
          ],
        }),
      );
      expect(unsupported.issues.map((issue) => issue.code)).toContain("UNSUPPORTED_NODE_TYPE");
    }
  });

  it("validates visibility rules at publication time", () => {
    const valid = validateGameDefinition({
      ...definition(),
      roles: [{ id: "werewolf", name: "Werewolf" }],
      visibility: { day: "public", wolfTeam: { role: "werewolf" }, seerResult: { participant: "p3" } },
    });
    expect(valid).toEqual({ valid: true, issues: [] });

    const undeclaredRole = validateGameDefinition({
      ...definition(),
      visibility: { wolfTeam: { role: "ghost" } },
    });
    expect(undeclaredRole.valid).toBe(false);
    expect(undeclaredRole.issues.map((issue) => issue.code)).toContain("INVALID_CONFIG");
    expect(undeclaredRole.issues[0]?.message).toMatch(/undeclared role: ghost/);

    const unparseable = validateGameDefinition({
      ...definition(),
      visibility: { secret: { visible: true } },
    });
    expect(unparseable.valid).toBe(false);
    expect(unparseable.issues[0]?.message).toMatch(/Visibility rule for "secret"/);
  });

  it("requires an AI node to name a declared agent and a seat", () => {
    const nodes = [
      { id: "start", type: "start" as const, config: {}, next: ["ai"] },
      {
        id: "ai",
        type: "aiGenerate" as const,
        config: { agentId: "seer", fallbackNodeId: "end", input: {}, resultKey: "out" },
        next: ["end"],
      },
      { id: "end", type: "end" as const, config: {}, next: [] },
    ];
    const roles = [{ id: "seer", name: "Seer" }];
    const agent = {
      id: "seer",
      roleId: "seer",
      systemPrompt: "You are the seer.",
      limits: { timeoutMs: 5_000, maxAttempts: 1, tokenBudget: 2_048 },
    };

    // No participantId: an agent without a seat has no session key.
    const missingSeat = validateGameDefinition({
      ...definition({ nodes }),
      roles,
      agents: [agent],
    });
    expect(missingSeat.valid).toBe(false);
    expect(missingSeat.issues.map((issue) => issue.code)).toContain("INVALID_CONFIG");

    // Decked out: agent declared, seat declared.
    expect(
      validateGameDefinition({
        ...definition({
          nodes: [
            nodes[0]!,
            {
              ...nodes[1]!,
              config: { ...nodes[1]!.config, participantId: "p1" },
            },
            nodes[2]!,
          ],
        }),
        roles,
        agents: [agent],
      }),
    ).toEqual({ valid: true, issues: [] });

    // Unknown agent reference.
    const unknown = validateGameDefinition({
      ...definition({
        nodes: [
          nodes[0]!,
          { ...nodes[1]!, config: { ...nodes[1]!.config, participantId: "p1", agentId: "ghost" } },
          nodes[2]!,
        ],
      }),
      roles,
      agents: [agent],
    });
    expect(unknown.issues.map((issue) => issue.code)).toContain("UNKNOWN_AGENT");

    // Agent pointing at an undeclared role.
    const unknownRole = validateGameDefinition({
      ...definition({
        nodes: [
          nodes[0]!,
          { ...nodes[1]!, config: { ...nodes[1]!.config, participantId: "p1" } },
          nodes[2]!,
        ],
      }),
      agents: [agent],
    });
    expect(unknownRole.issues.map((issue) => issue.code)).toContain("INVALID_CONFIG");
  });

  it("accepts an explicit loop and still rejects cycles that skip it", () => {
    const loopNode = {
      id: "loop",
      type: "loop" as const,
      config: { bodyNodeId: "body", counterKey: "round", maxIterations: 3 },
      next: ["end"],
    };
    const body = { id: "body", type: "setVariable" as const, config: { key: "tally", value: 1 }, next: ["loop"] };

    expect(
      validateGameDefinition(
        definition({
          nodes: [
            { id: "start", type: "start", config: {}, next: ["loop"] },
            loopNode,
            body,
            { id: "end", type: "end", config: {}, next: [] },
          ],
        }),
      ),
    ).toEqual({ valid: true, issues: [] });

    const innerCycle = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["loop"] },
          loopNode,
          { id: "body", type: "branch", config: { when: { op: "lit", value: true }, whenTrue: "again", whenFalse: "loop" }, next: [] },
          { id: "again", type: "setVariable", config: { key: "tally", value: 1 }, next: ["body"] },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );
    expect(innerCycle.issues.map((issue) => issue.code)).toContain("IMPLICIT_CYCLE");
  });

  it("rejects a loop without a counter or an exit", () => {
    const result = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["loop"] },
          { id: "loop", type: "loop", config: { bodyNodeId: "body" }, next: ["end"] },
          { id: "body", type: "setVariable", config: { key: "round", value: 1 }, next: ["loop"] },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );

    expect(result.issues.filter((issue) => issue.code === "INVALID_CONFIG")).toHaveLength(2);
    expect(result.issues.map((issue) => issue.message).join(" ")).toMatch(/counterKey/);
    expect(result.issues.map((issue) => issue.message).join(" ")).toMatch(/maxIterations/);
  });

  it("keeps a loop counter out of every other node's reach", () => {
    const result = validateGameDefinition(
      definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["loop"] },
          {
            id: "loop",
            type: "loop",
            config: { bodyNodeId: "body", counterKey: "round", maxIterations: 2 },
            next: ["end"],
          },
          { id: "body", type: "setVariable", config: { key: "round", value: 0 }, next: ["loop"] },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
    );

    expect(result.issues.map((issue) => issue.code)).toEqual(["INVALID_CONFIG"]);
    expect(result.issues[0]?.message).toMatch(/loop counter can only be written/);
  });

  it("checks the loop condition against declared variables", () => {
    const result = validateGameDefinition({
      ...definition({
        nodes: [
          { id: "start", type: "start", config: {}, next: ["loop"] },
          {
            id: "loop",
            type: "loop",
            config: {
              bodyNodeId: "body",
              counterKey: "round",
              maxIterations: 2,
              while: { op: "eq", args: [{ op: "var", name: "ghost" }, { op: "lit", value: true }] },
            },
            next: ["end"],
          },
          { id: "body", type: "setVariable", config: { key: "tally", value: 1 }, next: ["loop"] },
          { id: "end", type: "end", config: {}, next: [] },
        ],
      }),
      variables: { round: 0, tally: 0 },
    });

    expect(result.valid).toBe(false);
    expect(result.issues.map((issue) => issue.code)).toContain("INVALID_EXPRESSION");
    expect(result.issues.map((issue) => issue.message).join(" ")).toMatch(/unknown variable "ghost"/);
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
