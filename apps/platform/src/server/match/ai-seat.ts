import type { Kysely } from "kysely";
import type { GameState } from "../../shared/index.js";
import { allowedActions, type GameRegistry } from "../game/index.js";
import {
  createModelClient,
  MODEL_CALL_TIMEOUT_MS,
  type ChatMessage,
  type ModelClient,
  type ModelUsage,
} from "../llm/client.js";
import { chooseModelBinding, type ModelBinding } from "../llm/binding.js";
import { buildSeatPrompt, retryInstruction } from "../llm/prompt.js";
import { AppError, type CredentialKey } from "../runtime/index.js";
import {
  findReadyAiSeats,
  getGameInstance,
  listGameEvents,
  listGameParticipants,
  type Database,
} from "../db/index.js";
import type { MatchService } from "./service.js";
import { readPersona } from "./persona.js";

/** A reasoning model spends a few hundred tokens thinking before it acts; leave room for both. */
const DEFAULT_MAX_TOKENS = 2048;
const DEFAULT_MAX_CALLS_PER_TURN = 3;

/** A seat plays with the platform's shared model binding. */
export type SeatBinding = ModelBinding;

export interface AiSeatRunner {
  runOnce(input?: { limit?: number }): Promise<{ turns: number; failures: number }>;
}

export function createAiSeatRunner(deps: {
  db: Kysely<Database>;
  registry: GameRegistry;
  service: MatchService;
  credentialKey: CredentialKey;
  client?: ModelClient;
  logger?: { info(fields: Record<string, unknown>, message: string): void };
  maxTokens?: number;
  maxCallsPerTurn?: number;
}): AiSeatRunner {
  const { db, registry, service, credentialKey } = deps;
  const client = deps.client ?? createModelClient();
  const logger = deps.logger ?? console;
  const maxTokens = deps.maxTokens ?? DEFAULT_MAX_TOKENS;
  const maxCallsPerTurn = deps.maxCallsPerTurn ?? DEFAULT_MAX_CALLS_PER_TURN;

  /** Which model an AI seat plays with: the platform's shared binding. */
  async function chooseBinding(): Promise<SeatBinding | null> {
    return chooseModelBinding({ db, credentialKey, maxTokens });
  }

  function usageOf(binding: SeatBinding, usage: ModelUsage | null) {
    if (usage === null) return null;
    return { providerId: binding.providerId, modelId: binding.modelId, ...usage };
  }

  async function runTurn(target: {
    instanceId: string;
    participantId: string;
  }): Promise<"acted" | "failed" | "skipped"> {
    const seats = await listGameParticipants(db, target.instanceId);
    const seat = seats.find((candidate) => candidate.id === target.participantId);
    if (!seat || seat.control !== "ai" || seat.status !== "active") return "skipped";

    const instance = await getGameInstance(db, target.instanceId);
    if (!instance) return "skipped";
    const state = instance.state_json as GameState;
    // Somebody may have advanced the match since the scan; the waiting point is the truth.
    if (!(state.waiting?.participantIds ?? []).includes(seat.id)) return "skipped";

    const game = registry.get(instance.game_id);
    if (!game) {
      logger.info(
        { instanceId: target.instanceId, gameId: instance.game_id },
        "unknown game, skipping",
      );
      return "skipped";
    }
    const binding = await chooseBinding();
    if (!binding) {
      logger.info({ instanceId: target.instanceId }, "no enabled provider, nothing to play with");
      return "skipped";
    }

    const rows = await listGameEvents(db, target.instanceId);
    const seatKeys = Object.fromEntries(seats.map((row) => [row.id, row.participant_key]));
    // Only its own persona: a seat that could see the others' would learn who here is not an AI.
    const persona = readPersona(seat.persona);
    const promptInput = {
      game,
      state,
      participantId: seat.id,
      seatKeys,
      persona,
      record: rows.map((row) => ({
        sequence: row.sequence,
        type: row.type,
        participantId: row.participant_id,
        payload: row.payload,
      })),
      attempt: { index: 1, limit: maxCallsPerTurn },
    };
    const prompt = buildSeatPrompt(promptInput);

    // Deterministic per turn: a retry, or a second worker racing on the same turn, replays.
    const turnKey = `ai:${seat.id}:${instance.current_sequence}:${state.stepId}`;
    const allowed = allowedActions(game, state).map((action) => action.name);
    let messages: ChatMessage[] = [{ role: "system", content: prompt.system }, ...prompt.messages];

    /** Advances the counter the prompt reads, so every retry states its own remaining budget. */
    function nextAttempt(reason: string): string {
      promptInput.attempt.index += 1;
      return retryInstruction(promptInput, reason);
    }

    /** Never worth another call: the next one would be the (limit + 1)th. */
    const exhausted = (callIndex: number) => callIndex + 1 >= maxCallsPerTurn;

    for (let callIndex = 0; callIndex < maxCallsPerTurn; callIndex += 1) {
      const result = await client.call({
        endpoint: binding.endpoint,
        apiKey: binding.apiKey,
        model: binding.modelId,
        messages,
        tools: prompt.tools,
        maxTokens: binding.maxTokens,
        timeoutMs: MODEL_CALL_TIMEOUT_MS,
      });
      const call = {
        payload: {
          content: result.content,
          reasoning: result.reasoning,
          reasoningSignature: null,
          finishReason: result.finishReason,
          toolCalls: result.toolCalls,
        },
        usage: usageOf(binding, result.usage),
      };

      const toolCall = result.toolCalls[0];
      if (toolCall === undefined) {
        await service.recordTurn({
          instanceId: target.instanceId,
          participantId: seat.id,
          turnKey,
          callIndex,
          call,
        });
        if (result.finishReason === "length") {
          await service.recordFailure({
            instanceId: target.instanceId,
            participantId: seat.id,
            turnKey,
            code: "TOKEN_BUDGET_EXHAUSTED",
            message: "The model ran out of tokens while thinking and never acted",
          });
          return "failed";
        }
        // It answered in prose: record the call and ask for an action once more.
        if (exhausted(callIndex)) break;
        messages = [
          ...messages,
          { role: "assistant", content: result.content, reasoningContent: result.reasoning },
          { role: "user", content: nextAttempt("你用普通文字回答，没有调用任何工具。") },
        ];
        continue;
      }

      if (!allowed.includes(toolCall.name)) {
        await service.recordTurn({
          instanceId: target.instanceId,
          participantId: seat.id,
          turnKey,
          callIndex,
          call,
        });
        if (exhausted(callIndex)) break;
        messages = [
          ...messages,
          {
            role: "assistant",
            content: result.content,
            toolCalls: [toolCall],
            reasoningContent: result.reasoning,
          },
          {
            role: "tool",
            toolCallId: toolCall.id,
            content: nextAttempt(`「${toolCall.name}」不在本步允许的动作里。`),
          },
        ];
        continue;
      }

      const outcome = await service.recordTurn({
        instanceId: target.instanceId,
        participantId: seat.id,
        turnKey,
        callIndex,
        call,
        action: { type: toolCall.name, payload: parseArguments(toolCall.arguments) },
      });
      if (outcome.accepted) return "acted";

      // The rule refused the action: the call is kept, and the model gets the reason to try again.
      if (exhausted(callIndex)) break;
      messages = [
        ...messages,
        {
          role: "assistant",
          content: result.content,
          toolCalls: [toolCall],
          reasoningContent: result.reasoning,
        },
        {
          role: "tool",
          toolCallId: toolCall.id,
          content: nextAttempt(`动作被拒绝：${outcome.message}`),
        },
      ];
    }

    await service.recordFailure({
      instanceId: target.instanceId,
      participantId: seat.id,
      turnKey,
      code: "ITERATION_LIMIT",
      message: `The seat did not produce an accepted action in ${maxCallsPerTurn} calls`,
    });
    return "failed";
  }

  return {
    async runOnce(input = {}) {
      const limit = input.limit ?? 5;
      const ready = await findReadyAiSeats(db, limit);
      let turns = 0;
      let failures = 0;
      for (const target of ready) {
        try {
          const outcome = await runTurn(target);
          if (outcome === "acted") turns += 1;
          if (outcome === "failed") failures += 1;
        } catch (error) {
          failures += 1;
          // A provider outage must not take the worker down: the seat stays pending and retries.
          logger.info(
            {
              instanceId: target.instanceId,
              participantId: target.participantId,
              code: error instanceof AppError ? error.code : "UNEXPECTED",
              message: error instanceof Error ? error.message : String(error),
            },
            "ai seat turn failed",
          );
        }
      }
      return { turns, failures };
    },
  };
}

function parseArguments(raw: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Fall through: a model may send junk, and the rule will refuse the empty payload.
  }
  return {};
}
