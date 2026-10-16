import { describe, expect, it } from "vitest";
import { parseProviderEndpoint } from "../provider-endpoint.js";
import { AppError } from "../runtime/index.js";
import { chatCompletionsPath, createModelClient, type ModelTransport } from "./client.js";

const PUBLIC_IP = "93.184.216.34";
const resolver = async () => [PUBLIC_IP];

function endpoint(raw = "https://api.example.com/v1") {
  return parseProviderEndpoint(raw);
}

interface Captured {
  calls: Array<{ headers: Record<string, string>; body: string; url: string }>;
}

function recordingTransport(response: { status: number; body: string }): ModelTransport & Captured {
  const calls: Captured["calls"] = [];
  const transport = (async (request) => {
    calls.push({
      headers: request.headers,
      body: request.body,
      url: `${request.endpoint.url.origin}${chatCompletionsPath(request.endpoint.url)}`,
    });
    return response;
  }) as ModelTransport & Captured;
  transport.calls = calls;
  return transport;
}

function json(body: unknown): string {
  return JSON.stringify(body);
}

describe("model client", () => {
  it("posts an OpenAI-compatible chat completion with tools and parses the answer", async () => {
    const transport = recordingTransport({
      status: 200,
      body: json({
        choices: [
          {
            finish_reason: "tool_calls",
            message: {
              content: null,
              reasoning_content: "p2 说得很含糊",
              tool_calls: [
                { id: "call-1", function: { name: "vote", arguments: '{"target":"p2"}' } },
              ],
            },
          },
        ],
        usage: { prompt_tokens: 1200, completion_tokens: 42, total_tokens: 1242 },
      }),
    });
    const client = createModelClient({ transport, resolver, now: () => 1_000 });

    const result = await client.call({
      endpoint: endpoint(),
      apiKey: "sk-secret",
      model: "deepseek-chat",
      messages: [
        { role: "system", content: "rules" },
        { role: "user", content: "现在轮到你" },
      ],
      tools: [
        {
          name: "vote",
          description: "投出一票",
          parameters: {
            type: "object",
            properties: { target: { type: "string", description: "目标" } },
            required: ["target"],
          },
        },
      ],
    });

    expect(transport.calls).toHaveLength(1);
    expect(transport.calls[0]?.url).toBe("https://api.example.com/v1/chat/completions");
    const sent = JSON.parse(transport.calls[0]?.body ?? "{}") as Record<string, unknown>;
    expect(sent["model"]).toBe("deepseek-chat");
    expect(sent["tool_choice"]).toBe("auto");
    expect((sent["tools"] as unknown[]).length).toBe(1);
    expect((sent["messages"] as Array<Record<string, unknown>>)[0]).toEqual({
      role: "system",
      content: "rules",
    });
    // The credential travels in the header, never in the body.
    expect(transport.calls[0]?.body).not.toContain("sk-secret");
    expect(transport.calls[0]?.headers["authorization"]).toBe("Bearer sk-secret");

    expect(result.content).toBeNull();
    expect(result.reasoning).toBe("p2 说得很含糊");
    expect(result.toolCalls).toEqual([
      { id: "call-1", name: "vote", arguments: '{"target":"p2"}' },
    ]);
    expect(result.usage).toEqual({ promptTokens: 1200, completionTokens: 42, totalTokens: 1242 });
    expect(result.finishReason).toBe("tool_calls");
  });

  it("reports missing usage as absent instead of inventing numbers", async () => {
    const transport = recordingTransport({
      status: 200,
      body: json({ choices: [{ message: { content: "好的" } }] }),
    });
    const result = await createModelClient({ transport, resolver }).call({
      endpoint: endpoint(),
      apiKey: "sk-x",
      model: "m",
      messages: [{ role: "user", content: "hi" }],
    });

    expect(result.content).toBe("好的");
    expect(result.usage).toBeNull();
    expect(result.toolCalls).toEqual([]);
  });

  it("refuses a private destination before opening anything", async () => {
    const transport = recordingTransport({ status: 200, body: json({}) });
    const client = createModelClient({ transport });

    await expect(
      client.call({
        endpoint: endpoint("https://127.0.0.1:11434/v1"),
        apiKey: "sk-x",
        model: "m",
        messages: [{ role: "user", content: "hi" }],
      }),
    ).rejects.toThrowError(/blocked/);
    expect(transport.calls).toHaveLength(0);
  });

  it("fails loudly on an HTTP error, a timeout and a malformed body", async () => {
    const failing = (status: number, body: string) =>
      createModelClient({ transport: recordingTransport({ status, body }), resolver });

    await expect(
      failing(401, json({ error: "unauthorized" })).call({
        endpoint: endpoint(),
        apiKey: "sk-x",
        model: "m",
        messages: [{ role: "user", content: "hi" }],
      }),
    ).rejects.toMatchObject({ statusCode: 502, code: "MODEL_CALL_FAILED" });

    await expect(
      createModelClient({
        transport: async () => {
          const error = new Error("timed out") as NodeJS.ErrnoException;
          error.code = "ETIMEDOUT";
          throw error;
        },
        resolver,
      }).call({
        endpoint: endpoint(),
        apiKey: "sk-x",
        model: "m",
        messages: [{ role: "user", content: "hi" }],
      }),
    ).rejects.toMatchObject({ statusCode: 504, code: "MODEL_TIMEOUT" });

    await expect(
      failing(200, "not json").call({
        endpoint: endpoint(),
        apiKey: "sk-x",
        model: "m",
        messages: [{ role: "user", content: "hi" }],
      }),
    ).rejects.toMatchObject({ statusCode: 502, code: "MODEL_BAD_RESPONSE" });
  });

  it("rejects a well-formed JSON body of the wrong shape", async () => {
    const client = createModelClient({
      transport: recordingTransport({ status: 200, body: json({ choices: "nope" }) }),
      resolver,
    });

    const failure = await client
      .call({
        endpoint: endpoint(),
        apiKey: "sk-x",
        model: "m",
        messages: [{ role: "user", content: "hi" }],
      })
      .catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(AppError);
    expect((failure as AppError).code).toBe("MODEL_BAD_RESPONSE");
  });
});
