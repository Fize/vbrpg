import { AppError } from "./errors.js";
import type { GameEvent, GameState } from "@vbrpg/contracts";

const systemPrompt = "You are a game AI. Use only the current game context. Return the smallest useful JSON value or plain answer.";

export interface AiConfig {
  apiKey?: string;
  baseUrl: string;
  model: string;
  timeoutMs: number;
  contextWindowTokens: number;
  maxInputTokens: number;
  reserveOutputTokens: number;
}

export interface AiRequest {
  input: Record<string, unknown>;
  state: GameState;
  recentEvents: readonly GameEvent[];
}

export interface AiClient {
  generate(request: AiRequest): Promise<unknown>;
}

/** Conservative estimate used because the MVP does not bundle a model-specific tokenizer. */
export function estimateTokens(text: string): number {
  let estimate = 0;
  for (const character of text) {
    const codePoint = character.codePointAt(0) ?? 0;
    if (
      (codePoint >= 0x4e00 && codePoint <= 0x9fff)
      || (codePoint >= 0x3400 && codePoint <= 0x4dbf)
      || (codePoint >= 0x3040 && codePoint <= 0x30ff)
      || (codePoint >= 0xac00 && codePoint <= 0xd7af)
    ) {
      estimate += 1;
    } else if (/\s/.test(character)) {
      estimate += 0.25;
    } else if (/[A-Za-z0-9]/.test(character)) {
      estimate += 0.25;
    } else {
      estimate += 0.5;
    }
  }
  // Leave headroom for tokenizer differences, JSON punctuation, and provider framing.
  return Math.max(1, Math.ceil(estimate * 1.25));
}

function trimTextToTokens(text: string, maxTokens: number): string {
  if (maxTokens <= 0) return "";
  if (estimateTokens(text) <= maxTokens) return text;
  const marker = "\n...[truncated]";
  const available = Math.max(0, maxTokens - estimateTokens(marker));
  let low = 0;
  let high = text.length;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (estimateTokens(text.slice(0, middle)) <= available) low = middle;
    else high = middle - 1;
  }
  return `${text.slice(0, low)}${marker}`;
}

function gameStateJson(state: GameState): string {
  return JSON.stringify({
    sequence: state.sequence,
    status: state.status,
    currentNodeId: state.currentNodeId,
    variables: state.variables,
    participants: state.participants,
    waiting: state.waiting,
  });
}

/**
 * Builds a cache-friendly, current-game-only context window.
 * The append-only history is placed before the changing current state so the
 * provider can reuse the stable prompt prefix across turns.
 */
export function buildGameContext(
  state: GameState,
  recentEvents: readonly GameEvent[],
  maxContextTokens: number,
): string {
  const budget = Math.max(256, maxContextTokens);
  const stablePrefix = [
    "Game context v1 (current game only)",
    `Instance: ${state.instanceId}`,
    `Game version: ${state.gameVersionId}`,
    "Past events (oldest to newest):",
  ].join("\n") + "\n";
  const eventLines = recentEvents
    .slice()
    .sort((left, right) => left.sequence - right.sequence)
    .map((event) => JSON.stringify({ sequence: event.sequence, type: event.type, payload: event.payload }));
  const currentStateLabel = "\nCurrent state:\n";
  const currentState = gameStateJson(state);

  let firstEvent = 0;
  while (firstEvent < eventLines.length) {
    const eventText = eventLines.slice(firstEvent).join("\n");
    if (estimateTokens(`${stablePrefix}${eventText}${currentStateLabel}${currentState}`) <= budget) break;
    firstEvent += 1;
  }
  const omittedMarker = firstEvent > 0 ? "...[older events omitted]\n" : "";
  const eventText = eventLines.slice(firstEvent).join("\n");
  const fixed = `${stablePrefix}${omittedMarker}${eventText}${currentStateLabel}`;
  const remainingTokens = budget - estimateTokens(fixed);
  const stateText = trimTextToTokens(currentState, remainingTokens);
  return trimTextToTokens(`${fixed}${stateText}`, budget);
}

function parseModelContent(content: unknown): unknown {
  if (typeof content !== "string") return content;
  const cleaned = content.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    return content;
  }
}

export function createOpenAiCompatibleClient(config: AiConfig): AiClient {
  return {
    async generate(request) {
      if (!config.apiKey) {
        throw new AppError(503, "AI_NOT_CONFIGURED", "An AI API key is required for the AI demo");
      }
      const requestedAction = `Requested action:\n${JSON.stringify(request.input)}`;
      const fixedPromptTokens = estimateTokens(systemPrompt) + estimateTokens(requestedAction);
      const contextBudget = Math.max(
        256,
        Math.min(
          config.maxInputTokens,
          config.contextWindowTokens - config.reserveOutputTokens - fixedPromptTokens,
        ),
      );
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), config.timeoutMs);
      try {
        const response = await fetch(`${config.baseUrl.replace(/\/$/, "")}/chat/completions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${config.apiKey}`,
          },
          body: JSON.stringify({
            model: config.model,
            messages: [
              { role: "system", content: systemPrompt },
              {
                role: "user",
                content: `${buildGameContext(request.state, request.recentEvents, contextBudget)}\n\n${requestedAction}`,
              },
            ],
            max_tokens: config.reserveOutputTokens,
            stream: false,
          }),
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new AppError(502, "AI_PROVIDER_ERROR", `AI provider returned HTTP ${response.status}`);
        }
        const body = await response.json() as { choices?: Array<{ message?: { content?: unknown } }> };
        return parseModelContent(body.choices?.[0]?.message?.content);
      } catch (error) {
        if (error instanceof AppError) throw error;
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new AppError(504, "AI_TIMEOUT", "AI provider timed out");
        }
        throw new AppError(502, "AI_PROVIDER_ERROR", "AI provider request failed");
      } finally {
        clearTimeout(timeout);
      }
    },
  };
}
