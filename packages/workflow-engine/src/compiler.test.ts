import { describe, expect, it } from "vitest";
import { compileGameDefinition, DefinitionCompileError } from "./compiler.js";

function definition(version = "v1") {
  return {
    manifest: {
      gameId: "game-compile",
      slug: "compile-test",
      version: "1.0.0",
      dslVersion: version,
      engineVersion: "native-test",
      authorId: "user-1",
      license: "MIT",
    },
    workflow: {
      entryNodeId: "start",
      nodes: [
        { id: "start", type: "start", config: {}, next: ["end"] },
        { id: "end", type: "end", config: {}, next: [] },
      ],
    },
    roles: [],
    variables: {},
    visibility: {},
    presentation: {},
  };
}

describe("DSL v1 compiler", () => {
  it("compiles the current definition and produces a stable hash", () => {
    const first = compileGameDefinition(definition());
    const second = compileGameDefinition({
      ...definition(),
      presentation: { z: true, a: "stable" },
    });
    const third = compileGameDefinition({
      ...definition(),
      presentation: { a: "stable", z: true },
    });

    expect(first.entryNodeId).toBe("start");
    expect(first.nodes.get("end")?.type).toBe("end");
    expect(second.definitionHash).toBe(third.definitionHash);
    expect(second.definitionHash).not.toBe(first.definitionHash);
  });

  it("rejects non-current DSL versions and invalid graphs", () => {
    expect(() => compileGameDefinition(definition("v0"))).toThrow(DefinitionCompileError);
    expect(() => compileGameDefinition({
      ...definition(),
      workflow: {
        entryNodeId: "start",
        nodes: [{ id: "start", type: "start", config: {}, next: ["missing"] }],
      },
    })).toThrow(/UNKNOWN_NODE_REFERENCE/);
  });
});
