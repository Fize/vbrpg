import { describe, expect, it, vi } from "vitest";
import type { PlayerView } from "@vbrpg/contracts";
import { buildGameContext, createOpenAiCompatibleClient, estimateTokens } from "./ai.js";

function view(overrides: Partial<PlayerView> = {}): PlayerView {
  return {
    instanceId: "instance",
    gameVersionId: "version",
    sequence: 4,
    status: "waiting",
    publicState: {},
    privateState: {},
    availableActions: [],
    ...overrides,
  };
}

describe("MVP AI context", () => {
  it("keeps context within the per-game token budget", () => {
    const context = buildGameContext(view({ publicState: { long: "x".repeat(500) } }), [], 256);

    expect(estimateTokens(context)).toBeLessThanOrEqual(256);
    expect(context).toContain("Current public state");
  });

  it("sends only the seat's projection and no event payloads", () => {
    const context = buildGameContext(
      view({
        publicState: { dayNumber: 1 },
        privateState: { nightVotes: { p1: "p3" } },
      }),
      [
        {
          eventId: "event-1",
          instanceId: "game-1",
          sequence: 1,
          type: "playerInputReceived",
          actor: { userId: "u1", tenantId: "t1", participantId: "p1" },
          occurredAtMs: 1,
          idempotencyKey: "idempotency-1",
          payload: { participantId: "p1", value: "top-secret-vote" },
        },
      ],
      1_000,
    );

    expect(context).toContain('"dayNumber":1');
    expect(context).toContain('"nightVotes":{"p1":"p3"}');
    expect(context).toContain('"type":"playerInputReceived"');
    expect(context).toContain('"participantId":"p1"');
    expect(context).not.toContain("top-secret-vote");
    expect(context).not.toContain("payload");
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
      expect(body.messages[1]?.content).toContain('"dayNumber":1');
      expect(body.messages[1]?.content).toContain('"type":"playerChoice"');
      expect(body.messages[1]?.content).not.toContain("hidden-plan");
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
        view: view({ publicState: { dayNumber: 1 } }),
        recentEvents: [{
          eventId: "event-1",
          instanceId: "game-1",
          sequence: 0,
          type: "playerChoice",
          actor: null,
          occurredAtMs: 1,
          idempotencyKey: "idempotency-1",
          payload: { plan: "hidden-plan" },
        }],
      });

      expect(result).toEqual({ choice: "red" });
      expect(fetchMock).toHaveBeenCalledOnce();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
