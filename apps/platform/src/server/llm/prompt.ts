import type { GameState } from "../../shared/index.js";
import { aiCallPayloadSchema } from "../../shared/index.js";
import {
  allowedActions,
  projectPlayerView,
  resolveVisibility,
  type GameModule,
} from "../game/index.js";
import type { ChatMessage, ChatTool } from "./client.js";

/**
 * A seat's prompt, laid out so the prefix survives caching:
 *
 *   tools   — the game's whole action catalogue, identical for the match
 *   system  — the rules plus this seat's own private state, identical for the match
 *   messages— the transcript, then one instruction for the turn being taken
 *
 * Nothing that changes per turn may leak into the first two: the current round, the allowed
 * subset and the situation all belong to the last message.
 */
export interface SeatPrompt {
  tools: ChatTool[];
  system: string;
  messages: ChatMessage[];
}

export interface TranscriptRow {
  sequence: number;
  type: string;
  participantId: string | null;
  payload: Record<string, unknown>;
}

export interface BuildSeatPromptInput {
  game: GameModule;
  state: GameState;
  participantId: string;
  /** Seat keys, so the transcript reads as names instead of ids. */
  seatKeys: Record<string, string>;
  record: readonly TranscriptRow[];
}

export function buildSeatPrompt(input: BuildSeatPromptInput): SeatPrompt {
  const { game, state, participantId, seatKeys, record } = input;
  const seatKey = seatKeys[participantId] ?? participantId;
  const roomTypes = new Set(
    (game.actions ?? [])
      .filter((action) => (action.audience ?? "room") === "room")
      .map((action) => action.name),
  );

  const tools = toTools(game);
  // The seat's own secrets are stable for the match, so they belong in the cached header.
  const own = projectPlayerView(resolveVisibility(game.visibility, state), state, {
    kind: "participant",
    participantId,
  });
  const system = [
    game.briefing?.(state, participantId) ?? "",
    `只有你知道自己的私有信息：${JSON.stringify(own.privateState)}`,
    "你正在通过工具行动：每次只能调用一个工具，调用完就结束本轮。",
    `你的席位居于房间中的名字是「${seatKey}」。`,
  ]
    .filter((part) => part.length > 0)
    .join("\n\n");

  const messages: ChatMessage[] = [];
  for (const row of record) {
    if (row.participantId === participantId) {
      // Its own model call: an assistant turn with the reasoning the provider wants back,
      // followed by the result of the tool it asked for.
      if (row.type === "aiCall") {
        const payload = aiCallPayloadSchema.safeParse(row.payload);
        if (payload.success && payload.data.toolCalls.length > 0) {
          const [call] = payload.data.toolCalls;
          if (call) {
            messages.push({
              role: "assistant",
              content: payload.data.content ?? null,
              toolCalls: [call],
              reasoningContent: payload.data.reasoning ?? null,
            });
            messages.push({
              role: "tool",
              toolCallId: call.id,
              content: "已记录。",
            });
          }
        }
        continue;
      }
      // Its own accepted action is already represented by the tool result above.
      continue;
    }

    if (roomTypes.has(row.type)) {
      messages.push({
        role: "user",
        content: `[${seatKeys[row.participantId ?? ""] ?? "?"}] ${renderPayload(row.payload)}`,
      });
    }
  }

  messages.push({ role: "user", content: turnInstruction(input) });

  return { tools, system, messages };
}

/** The only part of the prompt that moves: what is happening now and what is allowed now. */
export function turnInstruction(input: BuildSeatPromptInput): string {
  const { game, state, participantId } = input;
  const allowed = allowedActions(game, state).map((action) => action.name);
  const view = projectPlayerView(resolveVisibility(game.visibility, state), state, {
    kind: "participant",
    participantId,
  });

  return [
    "现在轮到你行动。",
    `当前公开状态：${JSON.stringify(view.publicState)}`,
    `本步允许的动作：${allowed.length === 0 ? "（无）" : allowed.join(", ")}`,
    "用一次工具调用来完成你的动作；如果调用的动作现在不被允许，你会收到提示，然后可以重试。",
  ].join("\n");
}

function toTools(game: GameModule): ChatTool[] {
  return (game.actions ?? []).map((action) => {
    const properties: Record<string, { type: "string"; description: string }> = {};
    for (const [name, arg] of Object.entries(action.args ?? {})) {
      properties[name] = { type: "string", description: arg.description };
    }
    return {
      name: action.name,
      description: action.description,
      parameters: {
        type: "object",
        properties,
        required: Object.keys(action.args ?? {}),
      },
    };
  });
}

/** Render a payload for the transcript without inventing semantics: values as they are. */
function renderPayload(payload: Record<string, unknown>): string {
  const entries = Object.entries(payload);
  if (entries.length === 0) return "(无内容)";
  if (entries.length === 1) return String(entries[0]?.[1]);
  return entries
    .map(([key, value]) => `${key}=${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join(" ");
}
