import assert from "node:assert/strict";
import { describe, it } from "vitest";
import type { ChatToolCall, ModelCallInput, ModelCallOutput } from "./client.js";
import type { ModelBinding } from "./binding.js";
import { buildWordPairPrompt, generateWordPair } from "./word-pair.js";

const binding = {
  providerId: "provider-1",
  modelId: "model-1",
  endpoint: { url: new URL("https://api.example.com/v1"), hostname: "api.example.com" },
  apiKey: "sk-test",
  maxTokens: 256,
} satisfies ModelBinding;

function reply(call: ChatToolCall | null): ModelCallOutput {
  return {
    content: null,
    reasoning: null,
    reasoningSignature: null,
    toolCalls: call === null ? [] : [call],
    usage: null,
    finishReason: "tool_calls",
    latencyMs: 1,
  };
}

function stub(output: ModelCallOutput) {
  const seen: ModelCallInput[] = [];
  return {
    seen,
    client: {
      async call(input: ModelCallInput): Promise<ModelCallOutput> {
        seen.push(input);
        return output;
      },
    },
  };
}

describe("word pair generation", () => {
  it("asks the model for a category and reads the pair out of the tool call", async () => {
    const stubClient = stub(
      reply({ id: "c1", name: "giveWordPair", arguments: '{"civilian":"苹果","undercover":"梨"}' }),
    );
    const pair = await generateWordPair({
      client: stubClient.client,
      binding,
      category: "水果",
    });

    assert.deepEqual(pair, { civilian: "苹果", undercover: "梨" });
    const sent = stubClient.seen[0];
    assert.ok(sent);
    assert.equal(sent.tools?.[0]?.name, "giveWordPair");
    assert.deepEqual(
      sent.tools?.[0]?.parameters.required,
      ["civilian", "undercover"],
      "the reply shape is a tool schema, not a hopeful JSON parse",
    );
    assert.equal(sent.messages[0]?.role, "system");
    assert.match(String(sent.messages[1]?.content), /水果/);
  });

  it("refuses a reply that is not two different words", async () => {
    const noTool = stub(reply(null));
    await assert.rejects(
      () => generateWordPair({ client: noTool.client, binding, category: "水果" }),
      /did not return a word pair/,
    );

    const same = stub(
      reply({ id: "c1", name: "giveWordPair", arguments: '{"civilian":"梨","undercover":"梨"}' }),
    );
    await assert.rejects(
      () => generateWordPair({ client: same.client, binding, category: "水果" }),
      /unusable word pair/,
    );

    const junk = stub(reply({ id: "c1", name: "giveWordPair", arguments: "not json" }));
    await assert.rejects(
      () => generateWordPair({ client: junk.client, binding, category: "水果" }),
      /unreadable word pair/,
    );

    const empty = stub(reply({ id: "c1", name: "giveWordPair", arguments: '{"civilian":"  "}' }));
    await assert.rejects(
      () => generateWordPair({ client: empty.client, binding, category: "水果" }),
      /unusable word pair/,
    );
  });

  it("states the rules of the pair in the prompt", () => {
    const prompt = buildWordPairPrompt("动物");
    const system = String(prompt.messages[0]?.content);
    assert.match(system, /相近但不相同/);
    assert.match(system, /只能用工具调用/);
  });
});
