import { describe, expect, it, vi } from "vitest";
import { buildGameContext, createOpenAiCompatibleClient, estimateTokens } from "./ai.js";

describe("MVP AI context", () => {
  it("keeps context within the per-game token budget", () => {
    const context = buildGameContext(
      {
        instanceId: "instance",
        gameVersionId: "version",
        engineVersion: "test",
        sequence: 4,
        status: "waiting",
        currentNodeId: "ai",
        variables: { long: "x".repeat(500) },
        participants: [],
        waiting: { kind: "ai", nodeId: "ai", participantIds: [] },
        randomSeed: "seed",
      },
      [],
      256,
    );
    expect(estimateTokens(context)).toBeLessThanOrEqual(256);
    expect(context).toContain("Current state");
  });

  it("calls an OpenAI-compatible endpoint with only the current game context", async () => {
    const fetchMock = vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body)) as {
        model: string;
        stream: boolean;
        max_tokens: number;
        messages: Array<{ role: string; content: string }>;
      };
      expect(body.model).toBe("demo-model");
      expect(body.stream).toBe(false);
      expect(body.max_tokens).toBe(256);
      expect(body.messages[1]?.content).toContain('currentNodeId":"ai"');
      expect(body.messages[1]?.content).toContain('type":"playerChoice"');
      expect(body.messages[1]?.content).not.toContain("old-game-memory");
      return new Response(JSON.stringify({
        choices: [{ message: { content: '```json\n{"choice":"red"}\n```' } }],
      }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    try {
      const client = createOpenAiCompatibleClient({
        apiKey: "test-key",
        baseUrl: "https://example.test/v1",
        model: "demo-model",
        timeoutMs: 1_000,
        contextWindowTokens: 2_000,
        maxInputTokens: 1_536,
        reserveOutputTokens: 256,
      });
      const result = await client.generate({
        input: { prompt: "choose a color" },
        state: {
          instanceId: "game-1",
          gameVersionId: "version-1",
          engineVersion: "test",
          sequence: 1,
          status: "waiting",
          currentNodeId: "ai",
          variables: { color: "unknown" },
          participants: [],
          waiting: { kind: "ai", nodeId: "ai", participantIds: [] },
          randomSeed: "seed",
        },
        recentEvents: [{
          eventId: "event-1",
          instanceId: "game-1",
          sequence: 0,
          type: "playerChoice",
          actor: null,
          occurredAtMs: 1,
          idempotencyKey: "idempotency-1",
          payload: { choice: "red" },
        }],
      });

      expect(result).toEqual({ choice: "red" });
      expect(fetchMock).toHaveBeenCalledOnce();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
