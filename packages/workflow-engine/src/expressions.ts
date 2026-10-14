import type { GameState } from "@vbrpg/contracts";

/**
 * Whitelisted expressions (plan §5.1): comparison, boolean logic, collection
 * queries, counting, bounded aggregation and platform rule functions. The input
 * is a JSON AST rather than a string, so there is no parser to escape and every
 * operation is checked against an explicit allow-list.
 */
export type Expression =
  | { op: "lit"; value: unknown }
  | { op: "var"; name: string }
  | { op: "eq" | "ne" | "lt" | "lte" | "gt" | "gte" | "add" | "sub"; args: Expression[] }
  | { op: "and" | "or"; args: Expression[] }
  | { op: "not" | "count" | "sum" | "min" | "max" | "mode"; args: Expression[] }
  | { op: "includes"; args: Expression[] }
  | { op: "roleOf"; arg: Expression }
  | { op: "roleCount"; role: string; aliveOnly?: boolean }
  | { op: "if"; cond: Expression; then: Expression; else: Expression };

export const MAX_EXPRESSION_DEPTH = 32;
export const MAX_EXPRESSION_NODES = 256;

export class ExpressionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ExpressionError";
  }
}

export interface ExpressionContext {
  variables: Record<string, unknown>;
  state: GameState;
}

/** Ops that take a positional `args` array, with the number of operands they accept. */
const ARGS_OPS: Record<string, { arity?: number; minArity?: number }> = {
  eq: { arity: 2 },
  ne: { arity: 2 },
  lt: { arity: 2 },
  lte: { arity: 2 },
  gt: { arity: 2 },
  gte: { arity: 2 },
  add: { arity: 2 },
  sub: { arity: 2 },
  and: { minArity: 1 },
  or: { minArity: 1 },
  not: { arity: 1 },
  count: { arity: 1 },
  sum: { arity: 1 },
  min: { arity: 1 },
  max: { arity: 1 },
  mode: { arity: 1 },
  includes: { arity: 2 },
};

/** Ops with named fields instead of an args array. */
const NAMED_OPS: Record<string, readonly string[]> = {
  lit: ["value"],
  var: ["name"],
  roleOf: ["arg"],
  roleCount: ["role"],
  if: ["cond", "then", "else"],
};

const OPS: Record<string, unknown> = { ...ARGS_OPS, ...NAMED_OPS };

function asExpression(value: unknown): Expression {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ExpressionError("An expression must be an object");
  }
  const op = (value as { op?: unknown }).op;
  if (typeof op !== "string" || !(op in OPS)) {
    throw new ExpressionError(`Unsupported expression op: ${String(op)}`);
  }
  return value as Expression;
}

/**
 * Scalars and arrays inside an expression are literals; objects must be expressions.
 * That keeps the AST unambiguous without forcing `{"op":"lit"}` on every constant.
 */
function toExpression(value: unknown): Expression {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return { op: "lit", value };
  }
  return asExpression(value);
}

function argsOf(expression: Expression): Expression[] {
  const args = (expression as { args?: unknown }).args;
  if (!Array.isArray(args)) {
    throw new ExpressionError(`${expression.op} requires an args array`);
  }
  const shape = ARGS_OPS[expression.op];
  if (shape?.arity !== undefined && args.length !== shape.arity) {
    throw new ExpressionError(`${expression.op} expects ${shape.arity} arguments, received ${args.length}`);
  }
  if (shape?.arity === undefined && shape !== undefined && args.length < (shape.minArity ?? 1)) {
    throw new ExpressionError(`${expression.op} expects at least ${shape.minArity ?? 1} arguments`);
  }
  return args.map(toExpression);
}

function numeric(value: unknown, op: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ExpressionError(`${op} requires numbers`);
  }
  return value;
}

/** Collections are either arrays or the participant-keyed maps the collect nodes write. */
function collection(value: unknown, op: string): unknown[] {
  if (Array.isArray(value)) return value;
  if (typeof value === "object" && value !== null) return Object.values(value);
  throw new ExpressionError(`${op} requires a collection`);
}

function roleOf(state: GameState, participantId: unknown): string | undefined {
  if (typeof participantId !== "string") return undefined;
  return state.participants.find((participant) => participant.participantId === participantId)?.roleId;
}

function aliveRoleCount(state: GameState, role: string): number {
  return state.participants.filter(
    (participant) => participant.roleId === role && participant.status === "active",
  ).length;
}

/** Named fields may hold bare literals too, so normalise before recursing. */
function evalChild(value: unknown, context: ExpressionContext): unknown {
  return evaluateNode(toExpression(value), context);
}

function evaluateNode(expression: Expression, context: ExpressionContext): unknown {
  switch (expression.op) {
    case "lit":
      return expression.value;
    case "var":
      return context.variables[expression.name];
    case "eq":
    case "ne": {
      const [left, right] = argsOf(expression).map((arg) => evaluateNode(arg, context));
      const equal = JSON.stringify(left ?? null) === JSON.stringify(right ?? null);
      return expression.op === "eq" ? equal : !equal;
    }
    case "lt":
    case "lte":
    case "gt":
    case "gte": {
      const [left, right] = argsOf(expression).map((arg) => evaluateNode(arg, context));
      const a = numeric(left, expression.op);
      const b = numeric(right, expression.op);
      if (expression.op === "lt") return a < b;
      if (expression.op === "lte") return a <= b;
      if (expression.op === "gt") return a > b;
      return a >= b;
    }
    case "add":
    case "sub": {
      const [left, right] = argsOf(expression).map((arg) => evaluateNode(arg, context));
      const a = numeric(left, expression.op);
      const b = numeric(right, expression.op);
      return expression.op === "add" ? a + b : a - b;
    }
    case "and":
      return argsOf(expression).every((arg) => evaluateNode(arg, context) === true);
    case "or":
      return argsOf(expression).some((arg) => evaluateNode(arg, context) === true);
    case "not":
      return evaluateNode(argsOf(expression)[0]!, context) !== true;
    case "count":
      return collection(evaluateNode(argsOf(expression)[0]!, context), "count").length;
    case "sum":
    case "min":
    case "max": {
      const values = collection(evaluateNode(argsOf(expression)[0]!, context), expression.op).map((value) =>
        numeric(value, expression.op),
      );
      if (values.length === 0) return expression.op === "sum" ? 0 : null;
      if (expression.op === "sum") return values.reduce((total, value) => total + value, 0);
      return expression.op === "min" ? Math.min(...values) : Math.max(...values);
    }
    case "mode": {
      const values = collection(evaluateNode(argsOf(expression)[0]!, context), "mode");
      const counts = new Map<string, { value: unknown; count: number }>();
      for (const value of values) {
        const key = JSON.stringify(value ?? null);
        const entry = counts.get(key);
        counts.set(key, { value, count: (entry?.count ?? 0) + 1 });
      }
      let best: { value: unknown; count: number } | undefined;
      // Ties resolve to the first value seen, so the result stays deterministic.
      for (const entry of counts.values()) {
        if (!best || entry.count > best.count) best = entry;
      }
      return best?.value ?? null;
    }
    case "includes": {
      const [haystack, needle] = argsOf(expression).map((arg) => evaluateNode(arg, context));
      return collection(haystack, "includes").some(
        (value) => JSON.stringify(value ?? null) === JSON.stringify(needle ?? null),
      );
    }
    case "roleOf":
      return roleOf(context.state, evalChild(expression.arg, context)) ?? null;
    case "roleCount": {
      const role = expression.role;
      if (typeof role !== "string" || role === "") {
        throw new ExpressionError("roleCount requires a role id");
      }
      return expression.aliveOnly === false
        ? context.state.participants.filter((participant) => participant.roleId === role).length
        : aliveRoleCount(context.state, role);
    }
    case "if":
      return evalChild(expression.cond, context) === true
        ? evalChild(expression.then, context)
        : evalChild(expression.else, context);
    default:
      throw new ExpressionError(`Unsupported expression op: ${(expression as { op: string }).op}`);
  }
}

function assertBounded(expression: Expression, depth = 1, counter = { nodes: 0 }): void {
  if (depth > MAX_EXPRESSION_DEPTH) {
    throw new ExpressionError(`Expression nested deeper than ${MAX_EXPRESSION_DEPTH}`);
  }
  counter.nodes += 1;
  if (counter.nodes > MAX_EXPRESSION_NODES) {
    throw new ExpressionError(`Expression has more than ${MAX_EXPRESSION_NODES} nodes`);
  }
  for (const child of childExpressions(expression)) {
    assertBounded(child, depth + 1, counter);
  }
}

function childExpressions(expression: Expression): Expression[] {
  const record = expression as unknown as Record<string, unknown>;
  const children: Expression[] = [];
  if (Array.isArray(record.args)) {
    for (const arg of record.args) children.push(toExpression(arg));
  }
  for (const key of ["arg", "cond", "then", "else"] as const) {
    if (record[key] !== undefined) children.push(toExpression(record[key]));
  }
  return children;
}

export function evaluateExpression(expression: unknown, context: ExpressionContext): unknown {
  const parsed = asExpression(expression);
  assertBounded(parsed);
  return evaluateNode(parsed, context);
}

export interface ExpressionScope {
  variables: readonly string[];
  roles: readonly string[];
  /** Roles whose participants may be checked with roleCount/aliveRoleCount. */
  allowParticipantQueries?: boolean;
}

/** Publication-time check: unknown ops, variables or roles must fail before a game starts. */
export function validateExpression(
  expression: unknown,
  scope: ExpressionScope,
  path = "expression",
): string[] {
  const issues: string[] = [];
  let parsed: Expression;
  try {
    parsed = asExpression(expression);
    assertBounded(parsed);
  } catch (error) {
    return [`${path}: ${error instanceof Error ? error.message : String(error)}`];
  }

  const walk = (node: Expression, at: string): void => {
    if (node.op === "var" && !scope.variables.includes(node.name)) {
      issues.push(`${at}: unknown variable "${node.name}"`);
    }
    if (node.op === "roleCount" && !scope.roles.includes(node.role)) {
      issues.push(`${at}: unknown role "${node.role}"`);
    }
    if (node.op === "roleOf" && scope.allowParticipantQueries === false) {
      issues.push(`${at}: roleOf is not enabled for this definition`);
    }
    const shape = ARGS_OPS[node.op];
    if (shape) {
      const args = (node as { args?: unknown }).args;
      if (!Array.isArray(args)) {
        issues.push(`${at}: ${node.op} expects an args array`);
      } else if (shape.arity !== undefined && args.length !== shape.arity) {
        issues.push(`${at}: ${node.op} expects ${shape.arity} arguments, received ${args.length}`);
      } else if (shape.arity === undefined && args.length < (shape.minArity ?? 1)) {
        issues.push(`${at}: ${node.op} expects at least ${shape.minArity ?? 1} arguments`);
      }
    }
    for (const field of NAMED_OPS[node.op] ?? []) {
      if ((node as Record<string, unknown>)[field] === undefined) {
        issues.push(`${at}: ${node.op} requires "${field}"`);
      }
    }
    for (const child of childExpressions(node)) walk(child, at);
  };
  walk(parsed, path);
  return issues;
}
