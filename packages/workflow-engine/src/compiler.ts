import { createHash } from "node:crypto";
import { gameDefinitionSchema, type GameDefinition } from "@vbrpg/contracts";
import { validateGameDefinition } from "./validator.js";

export interface CompiledGame {
  definition: GameDefinition;
  entryNodeId: string;
  nodes: ReadonlyMap<string, GameDefinition["workflow"]["nodes"][number]>;
  definitionHash: string;
}

export class DefinitionCompileError extends Error {
  readonly code = "DEFINITION_COMPILE_ERROR";

  constructor(message: string) {
    super(message);
    this.name = "DefinitionCompileError";
  }
}

function stableJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJson(item)).join(",")}]`;
  }
  if (typeof value === "object" && value !== null) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableJson((value as Record<string, unknown>)[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

export function compileGameDefinition(input: unknown): CompiledGame {
  const parsed = gameDefinitionSchema.safeParse(input);
  if (!parsed.success) {
    throw new DefinitionCompileError(parsed.error.message);
  }
  if (parsed.data.manifest.dslVersion !== "v1") {
    throw new DefinitionCompileError(
      `Only the current DSL version v1 can be compiled; received ${parsed.data.manifest.dslVersion}`,
    );
  }

  const validation = validateGameDefinition(parsed.data);
  if (!validation.valid) {
    throw new DefinitionCompileError(
      validation.issues.map((issue) => `${issue.code}: ${issue.message}`).join("; "),
    );
  }

  const nodes = new Map(parsed.data.workflow.nodes.map((node) => [node.id, node]));
  const definitionHash = createHash("sha256").update(stableJson(parsed.data)).digest("hex");
  return {
    definition: parsed.data,
    entryNodeId: parsed.data.workflow.entryNodeId,
    nodes,
    definitionHash,
  };
}
