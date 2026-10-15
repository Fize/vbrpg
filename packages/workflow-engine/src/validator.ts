import type { GameDefinition } from "@vbrpg/contracts";
import { parseVisibilityRule } from "./projector.js";
import { validateExpression } from "./expressions.js";

export interface ValidationIssue {
  code: string;
  nodeId?: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

type Node = GameDefinition["workflow"]["nodes"][number];
type Config = Record<string, unknown>;

function configOf(node: Node): Config {
  return node.config;
}

function stringConfig(node: Node, key: string, issues: ValidationIssue[]): string | undefined {
  const value = configOf(node)[key];
  if (typeof value !== "string" || value.length === 0) {
    issues.push({
      code: "INVALID_CONFIG",
      nodeId: node.id,
      message: `${node.type} requires a non-empty string config: ${key}`,
    });
    return undefined;
  }
  return value;
}

function integerConfig(node: Node, key: string, issues: ValidationIssue[]): void {
  const value = configOf(node)[key];
  if (typeof value !== "number" || !Number.isInteger(value)) {
    issues.push({
      code: "INVALID_CONFIG",
      nodeId: node.id,
      message: `${node.type} requires an integer config: ${key}`,
    });
  }
}

function positiveIntegerConfig(node: Node, key: string, issues: ValidationIssue[]): void {
  const value = configOf(node)[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    issues.push({
      code: "INVALID_CONFIG",
      nodeId: node.id,
      message: `${node.type} requires a positive integer config: ${key}`,
    });
  }
}

function referencedNodeIds(node: Node, issues: ValidationIssue[]): string[] {
  const references = [...node.next];
  const config = configOf(node);
  if (node.type === "branch") {
    const whenTrue = stringConfig(node, "whenTrue", issues);
    const whenFalse = stringConfig(node, "whenFalse", issues);
    if (whenTrue) references.push(whenTrue);
    if (whenFalse) references.push(whenFalse);
  }
  if (node.type === "aiGenerate") {
    const fallback = stringConfig(node, "fallbackNodeId", issues);
    if (fallback) references.push(fallback);
  }
  if (node.type === "loop") {
    const body = stringConfig(node, "bodyNodeId", issues);
    if (body) references.push(body);
  }
  if (node.type === "subflow") {
    const entry = stringConfig(node, "entryNodeId", issues);
    if (entry) references.push(entry);
  }
  return [...new Set(references)];
}

function validateNodeConfig(node: Node, issues: ValidationIssue[]): void {
  const config = configOf(node);
  switch (node.type) {
    case "waitForPlayerInput":
      stringConfig(node, "inputKey", issues);
      if (config.participantId !== undefined) {
        stringConfig(node, "participantId", issues);
      }
      break;
    case "collectInput":
    case "vote":
      if (
        !Array.isArray(config.participantIds) ||
        config.participantIds.length === 0 ||
        config.participantIds.some((value) => typeof value !== "string" || value.length === 0)
      ) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: `${node.type} requires a non-empty participantIds string array`,
        });
      }
      break;
    case "timer":
      positiveIntegerConfig(node, "durationMs", issues);
      break;
    case "random":
      stringConfig(node, "key", issues);
      integerConfig(node, "min", issues);
      integerConfig(node, "max", issues);
      if (typeof config.min === "number" && typeof config.max === "number" && config.max < config.min) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: "random requires max >= min",
        });
      }
      break;
    // Not implemented yet: reject at publication instead of failing mid-game.
    case "subflow":
    case "parallel":
    case "join":
      issues.push({
        code: "UNSUPPORTED_NODE_TYPE",
        nodeId: node.id,
        message: `The engine does not implement node type yet: ${node.type}`,
      });
      break;
    case "aiGenerate":
      stringConfig(node, "agentId", issues);
      if (config.participantId !== undefined) {
        stringConfig(node, "participantId", issues);
      }
      positiveIntegerConfig(node, "timeoutMs", issues);
      positiveIntegerConfig(node, "maxAttempts", issues);
      if (typeof config.input !== "object" || config.input === null || Array.isArray(config.input)) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: "aiGenerate requires an object input config",
        });
      }
      break;
    case "loop":
      stringConfig(node, "counterKey", issues);
      stringConfig(node, "bodyNodeId", issues);
      positiveIntegerConfig(node, "maxIterations", issues);
      if (node.next.length === 0) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: "loop requires an exit node in next",
        });
      }
      break;
    case "setVariable":
      stringConfig(node, "key", issues);
      if (config.value === undefined && config.valueExpr === undefined) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: "setVariable requires value or valueExpr",
        });
      }
      break;
    case "branch":
      if (config.when === undefined) {
        stringConfig(node, "variable", issues);
      }
      break;
    case "emitEvent":
      stringConfig(node, "eventName", issues);
      if (typeof config.payload !== "object" || config.payload === null || Array.isArray(config.payload)) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: "emitEvent requires an object payload config",
        });
      }
      break;
    default:
      break;
  }
}

/** Expressions are checked against the definition's declared variables and roles. */
function validateNodeExpressions(definition: GameDefinition, issues: ValidationIssue[]): void {
  const scope = {
    variables: Object.keys(definition.variables),
    roles: definition.roles.map((role) => role.id),
  };
  for (const node of definition.workflow.nodes) {
    const config = configOf(node);
    const candidates: Array<[string, unknown]> = [];
    if (node.type === "branch" && config.when !== undefined) candidates.push(["when", config.when]);
    if (node.type === "loop" && config.while !== undefined) candidates.push(["while", config.while]);
    if (node.type === "setVariable" && config.valueExpr !== undefined) {
      candidates.push(["valueExpr", config.valueExpr]);
    }
    for (const [field, value] of candidates) {
      for (const message of validateExpression(value, scope, `${node.id}.${field}`)) {
        issues.push({ code: "INVALID_EXPRESSION", nodeId: node.id, message });
      }
    }
  }
}

/** Unparseable visibility rules block publication: the projector refuses them at runtime too. */
function validateVisibility(definition: GameDefinition, issues: ValidationIssue[]): void {
  const roleIds = new Set(definition.roles.map((role) => role.id));
  for (const [variable, raw] of Object.entries(definition.visibility)) {
    let rule;
    try {
      rule = parseVisibilityRule(variable, raw);
    } catch (error) {
      issues.push({
        code: "INVALID_CONFIG",
        message: error instanceof Error ? error.message : `Invalid visibility rule for ${variable}`,
      });
      continue;
    }
    if (rule.kind === "role" && !roleIds.has(rule.roleId)) {
      issues.push({
        code: "INVALID_CONFIG",
        message: `Visibility rule for "${variable}" references undeclared role: ${rule.roleId}`,
      });
    }
  }
}

/** Each write key a node assigns. Used to keep loop counters out of any other node's reach. */
function writtenKeys(node: Node): unknown[] {
  const config = configOf(node);
  switch (node.type) {
    case "setVariable":
    case "random":
      return [config.key];
    case "waitForPlayerInput":
      return [config.inputKey];
    case "collectInput":
    case "vote":
      return [config.collectionKey];
    default:
      return [];
  }
}

/** A loop owns its counter: any other node writing it would remove the only termination bound. */
function validateLoopCounters(nodes: Node[], issues: ValidationIssue[]): void {
  const counterKeys = new Set<string>();
  for (const node of nodes) {
    const counterKey = configOf(node).counterKey;
    if (node.type === "loop" && typeof counterKey === "string" && counterKey.length > 0) {
      counterKeys.add(counterKey);
    }
  }

  for (const node of nodes) {
    if (node.type === "loop") continue;
    for (const key of writtenKeys(node)) {
      if (typeof key === "string" && counterKeys.has(key)) {
        issues.push({
          code: "INVALID_CONFIG",
          nodeId: node.id,
          message: `A loop counter can only be written by its loop node: ${key}`,
        });
      }
    }
  }
}

export function validateGameDefinition(definition: GameDefinition): ValidationResult {
  const issues: ValidationIssue[] = [];
  const nodes = definition.workflow.nodes;
  const nodeById = new Map<string, Node>();

  for (const node of nodes) {
    if (nodeById.has(node.id)) {
      issues.push({ code: "DUPLICATE_NODE", nodeId: node.id, message: `Duplicate node id: ${node.id}` });
    }
    nodeById.set(node.id, node);
    validateNodeConfig(node, issues);
  }

  if (!nodeById.has(definition.workflow.entryNodeId)) {
    issues.push({
      code: "UNKNOWN_ENTRY",
      message: `Workflow entry node does not exist: ${definition.workflow.entryNodeId}`,
    });
  }

  const edges = new Map<string, string[]>();
  for (const node of nodes) {
    const references = referencedNodeIds(node, issues);
    edges.set(node.id, references);
    for (const target of references) {
      if (!nodeById.has(target)) {
        issues.push({
          code: "UNKNOWN_NODE_REFERENCE",
          nodeId: node.id,
          message: `Node ${node.id} references missing node: ${target}`,
        });
      }
    }
  }

  const reachable = new Set<string>();
  const visit = (nodeId: string): void => {
    if (reachable.has(nodeId) || !nodeById.has(nodeId)) return;
    reachable.add(nodeId);
    for (const target of edges.get(nodeId) ?? []) visit(target);
  };
  visit(definition.workflow.entryNodeId);

  for (const node of nodes) {
    if (!reachable.has(node.id)) {
      issues.push({ code: "UNREACHABLE_NODE", nodeId: node.id, message: `Node is unreachable: ${node.id}` });
    }
  }
  if (!nodes.some((node) => node.type === "end" && reachable.has(node.id))) {
    issues.push({ code: "NO_REACHABLE_END", message: "Workflow has no reachable end node" });
  }

  // A cycle is legal only when it passes through an explicit loop node, so cycle detection
  // runs on the graph with every loop node removed and every node as a root.
  const loopNodeIds = new Set(nodes.filter((node) => node.type === "loop").map((node) => node.id));
  const active = new Set<string>();
  const checked = new Set<string>();
  const detectCycle = (nodeId: string): void => {
    if (active.has(nodeId)) {
      issues.push({ code: "IMPLICIT_CYCLE", nodeId, message: `Workflow contains a cycle at node: ${nodeId}` });
      return;
    }
    if (checked.has(nodeId) || !nodeById.has(nodeId) || loopNodeIds.has(nodeId)) return;
    active.add(nodeId);
    for (const target of edges.get(nodeId) ?? []) detectCycle(target);
    active.delete(nodeId);
    checked.add(nodeId);
  };
  for (const node of nodes) detectCycle(node.id);
  validateLoopCounters(nodes, issues);
  validateVisibility(definition, issues);
  validateNodeExpressions(definition, issues);

  return { valid: issues.length === 0, issues };
}

export function assertValidGameDefinition(definition: GameDefinition): void {
  const result = validateGameDefinition(definition);
  if (!result.valid) {
    throw new Error(result.issues.map((issue) => `${issue.code}: ${issue.message}`).join("; "));
  }
}
