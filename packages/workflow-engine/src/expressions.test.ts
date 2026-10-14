import { describe, expect, it } from "vitest";
import type { GameState } from "@vbrpg/contracts";
import {
  evaluateExpression,
  MAX_EXPRESSION_DEPTH,
  validateExpression,
  type ExpressionContext,
} from "./expressions.js";

const state: GameState = {
  instanceId: "instance-1",
  gameVersionId: "version-1",
  engineVersion: "native-test",
  sequence: 1,
  status: "waiting",
  currentNodeId: "night",
  variables: {},
  participants: [
    { participantId: "p1", actorId: "u1", roleId: "werewolf", control: "ai", status: "active" },
    { participantId: "p2", actorId: "u2", roleId: "werewolf", control: "ai", status: "eliminated" },
    { participantId: "p3", actorId: "u3", roleId: "villager", control: "ai", status: "active" },
  ],
  waiting: null,
  randomSeed: "seed-1",
};

const context: ExpressionContext = {
  state,
  variables: { day: 2, votes: { p1: "p3", p2: "p3" }, roles: ["werewolf", "villager"], alive: 1 },
};

function evaluate(expression: unknown): unknown {
  return evaluateExpression(expression, context);
}

describe("whitelisted expressions", () => {
  it("compares and combines", () => {
    expect(evaluate({ op: "eq", args: [{ op: "var", name: "day" }, 2] })).toBe(true);
    expect(evaluate({ op: "ne", args: [{ op: "var", name: "day" }, 3] })).toBe(true);
    expect(evaluate({ op: "gt", args: [2, 1] })).toBe(true);
    expect(evaluate({ op: "and", args: [true, { op: "lte", args: [{ op: "var", name: "day" }, 2] }] })).toBe(true);
    expect(evaluate({ op: "or", args: [false, false] })).toBe(false);
    expect(evaluate({ op: "not", args: [false] })).toBe(true);
  });

  it("does arithmetic and conditionals", () => {
    expect(evaluate({ op: "add", args: [{ op: "var", name: "day" }, 1] })).toBe(3);
    expect(evaluate({ op: "sub", args: [{ op: "var", name: "day" }, 5] })).toBe(-3);
    expect(
      evaluate({ op: "if", cond: { op: "eq", args: [1, 1] }, then: "yes", else: "no" }),
    ).toBe("yes");
    expect(
      evaluate({ op: "if", cond: { op: "eq", args: [1, 2] }, then: "yes", else: "no" }),
    ).toBe("no");
  });

  it("queries and aggregates collections, including the maps the collect nodes write", () => {
    expect(evaluate({ op: "count", args: [{ op: "var", name: "votes" }] })).toBe(2);
    expect(evaluate({ op: "mode", args: [{ op: "var", name: "votes" }] })).toBe("p3");
    expect(evaluate({ op: "count", args: [{ op: "var", name: "roles" }] })).toBe(2);
    expect(evaluate({ op: "includes", args: [{ op: "var", name: "roles" }, "villager"] })).toBe(true);
    expect(evaluate({ op: "sum", args: [[1, 2, 3]] })).toBe(6);
    expect(evaluate({ op: "min", args: [[4, 2, 9]] })).toBe(2);
    expect(evaluate({ op: "max", args: [[4, 2, 9]] })).toBe(9);
    expect(evaluate({ op: "sum", args: [[]] })).toBe(0);
    expect(evaluate({ op: "min", args: [[]] })).toBeNull();
  });

  it("resolves ties deterministically", () => {
    const tied = { p1: "p2", p2: "p1" };
    const resolved = evaluateExpression({ op: "mode", args: [{ op: "var", name: "votes" }] }, {
      state,
      variables: { votes: tied },
    });

    expect(resolved).toBe("p2");
    expect(
      evaluateExpression({ op: "mode", args: [{ op: "var", name: "votes" }] }, {
        state,
        variables: { votes: tied },
      }),
    ).toBe(resolved);
  });

  it("looks up platform rule facts about participants", () => {
    expect(evaluate({ op: "roleOf", arg: "p1" })).toBe("werewolf");
    expect(evaluate({ op: "roleOf", arg: "nobody" })).toBeNull();
    expect(evaluate({ op: "roleCount", role: "werewolf" })).toBe(1);
    expect(evaluate({ op: "roleCount", role: "werewolf", aliveOnly: false })).toBe(2);
    expect(evaluate({ op: "roleCount", role: "villager" })).toBe(1);
  });

  it("rejects unknown operations and malformed operands", () => {
    expect(() => evaluate({ op: "exec", args: [] })).toThrowError(/Unsupported expression op/);
    expect(() => evaluate({ op: "count", args: [] })).toThrowError(/expects 1 arguments/);
    expect(() => evaluate({ op: "add", args: ["a", 1] })).toThrowError(/requires numbers/);
    expect(() => evaluate({ op: "min", args: [5] })).toThrowError(/requires a collection/);
    expect(() => evaluate(42)).toThrowError(/must be an object/);
  });

  it("refuses expressions nested beyond the limit", () => {
    let expression: Record<string, unknown> = { op: "lit", value: 1 };
    for (let depth = 0; depth < MAX_EXPRESSION_DEPTH + 2; depth += 1) {
      expression = { op: "not", args: [expression] };
    }

    expect(() => evaluate(expression)).toThrowError(/nested deeper than/);
  });

  it("validates against declared variables and roles at publication time", () => {
    const scope = { variables: ["day"], roles: ["werewolf"] };

    expect(validateExpression({ op: "eq", args: [{ op: "var", name: "day" }, 1] }, scope)).toEqual([]);
    expect(validateExpression({ op: "var", name: "unknown" }, scope)[0]).toMatch(/unknown variable "unknown"/);
    expect(validateExpression({ op: "roleCount", role: "ghost" }, scope)[0]).toMatch(/unknown role "ghost"/);
    expect(validateExpression({ op: "if", cond: true, then: 1 }, scope)).toHaveLength(1);
    expect(validateExpression({ op: "exec" }, scope)[0]).toMatch(/Unsupported expression op/);
  });
});
