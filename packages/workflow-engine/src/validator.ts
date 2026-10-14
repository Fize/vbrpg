import type { GameDefinition } from "@vbrpg/contracts";
import { parseVisibilityRule } from "./projector.js";

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
    case "aiGenerate":
      stringConfig(node, "agentId", issues);
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
    case "setVariable":
      stringConfig(node, "key", issues);
      break;
    case "branch":
      stringConfig(node, "variable", issues);
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

  const active = new Set<string>();
  const checked = new Set<string>();
  const detectCycle = (nodeId: string): void => {
    if (active.has(nodeId)) {
      issues.push({ code: "IMPLICIT_CYCLE", nodeId, message: `Workflow contains a cycle at node: ${nodeId}` });
      return;
    }
    if (checked.has(nodeId) || !nodeById.has(nodeId)) return;
    active.add(nodeId);
    for (const target of edges.get(nodeId) ?? []) detectCycle(target);
    active.delete(nodeId);
    checked.add(nodeId);
  };
  detectCycle(definition.workflow.entryNodeId);
  validateVisibility(definition, issues);

  return { valid: issues.length === 0, issues };
}

export function assertValidGameDefinition(definition: GameDefinition): void {
  const result = validateGameDefinition(definition);
  if (!result.valid) {
    throw new Error(result.issues.map((issue) => `${issue.code}: ${issue.message}`).join("; "));
  }
}
