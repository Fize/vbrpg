import type { GameState, SeatPersona } from "../../shared/index.js";
import { aiCallPayloadSchema } from "../../shared/index.js";
import {
  allowedActions,
  projectPlayerView,
  resolveVisibility,
  roomAudienceActions,
  type GameModule,
} from "../game/index.js";
import type { ChatMessage, ChatTool } from "./client.js";

/**
 * A seat's prompt, laid out so the prefix survives caching:
 *
 *   tools   — the game's whole action catalogue, identical for the match
 *   system  — the rules, who this seat is and what it alone knows, identical for the match
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
  /**
   * This seat's own persona, and nothing else. Who at the table has one must not reach the prompt:
   * only AI seats are dealt personas, so "has a persona" would read as "is an AI seat".
   */
  persona?: SeatPersona | null;
  /**
   * Which try this is at the current step, and how many the platform allows. `limit` is fixed for
   * the match and belongs in the cached header; `index` moves, so only it reaches the last message.
   */
  attempt: { index: number; limit: number };
}

export function buildSeatPrompt(input: BuildSeatPromptInput): SeatPrompt {
  const { game, state, participantId, seatKeys, record } = input;
  const roomTypes = new Set(roomAudienceActions(game));

  const tools = toTools(game);
  // The seat's own secrets are stable for the match, so they belong in the cached header.
  const own = projectPlayerView(resolveVisibility(game.visibility, state), state, {
    kind: "participant",
    participantId,
  });
  const system = [
    section("规则", game.briefing?.(state, participantId) ?? ""),
    section("你的角色", roleLine(game, state, participantId)),
    section("你的位置与席位表", position(input)),
    section("你的人格", ownPersona(input)),
    section("只有你知道的信息", ownSecrets(own.privateState, participantId, input)),
    section("行动约束", actionLimits(input.attempt.limit)),
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
        content: `[${seatKeys[row.participantId ?? ""] ?? "?"}] ${transcriptText(row, game, seatKeys)}`,
      });
    }
  }

  messages.push({ role: "user", content: turnInstruction(input) });

  return { tools, system, messages };
}

/** One heading and its body, or nothing at all: an empty section reads worse than no section. */
function section(title: string, body: string): string {
  const trimmed = body.trim();
  return trimmed.length === 0 ? "" : `## ${title}\n${trimmed}`;
}

function roleLine(game: GameModule, state: GameState, participantId: string): string {
  const role = state.participants.find((seat) => seat.participantId === participantId)?.roleId;
  if (role === undefined) return "";
  return `你是「${game.words?.[role] ?? role}」。`;
}

/**
 * The table's seats, in the game's own names, and where this seat sits. Ids never have to be
 * reproduced by the model: it names a seat, and the platform resolves it (see `resolveSeatReferences`).
 */
function position(input: BuildSeatPromptInput): string {
  const { seatKeys, participantId } = input;
  const keys = Object.keys(seatKeys).sort((left, right) =>
    (seatKeys[left] ?? left).localeCompare(seatKeys[right] ?? right),
  );
  const index = keys.indexOf(participantId);
  const mine = seatKeys[participantId] ?? participantId;
  const names = keys.map((key) => seatKeys[key] ?? key);
  if (names.length === 0) return "";
  return [
    index === -1
      ? `你的席位不在本桌的名单里。`
      : `你是「${mine}」，本桌 ${names.length} 席中的第 ${index + 1} 席。`,
    `桌上的席位：${names.join("、")}。`,
    "要指定某个席位（例如投票），参数里写它的席位名，例如「s2」；不要写内部 id。",
  ].join("\n");
}

/** A seat's own persona drives how it talks, so it gets all of it — MBTI included. */
function ownPersona(input: BuildSeatPromptInput): string {
  const persona = visibleParts(input.persona ?? null);
  return persona.length === 0 ? "" : persona.join(" · ");
}

/** Its own persona in full — nobody else's ever reaches the prompt, so there is no slice to make. */
function visibleParts(persona: SeatPersona | null): string[] {
  if (persona === null) return [];
  return [
    persona.mbti,
    persona.gender,
    persona.profession,
    persona.personality,
    persona.style,
  ].filter((part): part is string => part !== undefined && part !== "");
}

function ownSecrets(
  privateState: Record<string, unknown>,
  participantId: string,
  input: BuildSeatPromptInput,
): string {
  const words = input.game.words ?? {};
  return Object.entries(privateState)
    .map(([key, value]) => {
      const suffix = `:${participantId}`;
      const name = key.endsWith(suffix) ? key.slice(0, key.length - suffix.length) : key;
      return `${words[name] ?? name}：${renderValue(value, words, input.seatKeys)}`;
    })
    .join("\n");
}

/** A room row with no payload is the game's own word for it: "passed", "voted", whatever it says. */
function transcriptText(
  row: TranscriptRow,
  game: GameModule,
  seatKeys: Record<string, string>,
): string {
  const entries = Object.entries(row.payload);
  if (entries.length === 0) return game.words?.[row.type] ?? "(无内容)";
  const words = game.words ?? {};
  if (entries.length === 1) return renderValue(entries[0]?.[1], words, seatKeys);
  return entries
    .map(([key, value]) => `${words[key] ?? key}=${renderValue(value, words, seatKeys)}`)
    .join(" ");
}

/**
 * Values as this table reads them: a seat reads as its name, a word the game named reads in
 * Chinese. Anything else is shown as it is, so nothing is invented on the way.
 */
function renderValue(
  value: unknown,
  words: Record<string, string>,
  seatKeys: Record<string, string>,
): string {
  if (typeof value === "string") return seatKeys[value] ?? words[value] ?? value;
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (value === null) return "—";
  if (Array.isArray(value)) {
    return value.length === 0
      ? "（空）"
      : value.map((item) => renderValue(item, words, seatKeys)).join("、");
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return "（空）";
    return entries
      .map(([key, item]) => `${words[key] ?? key}=${renderValue(item, words, seatKeys)}`)
      .join("、");
  }
  return JSON.stringify(value);
}

/** The only part of the prompt that moves: what is happening now and what is allowed now. */
export function turnInstruction(input: BuildSeatPromptInput): string {
  const { game, state, participantId, seatKeys } = input;
  const allowed = allowedActions(game, state).map((action) => action.name);
  const view = projectPlayerView(resolveVisibility(game.visibility, state), state, {
    kind: "participant",
    participantId,
  });
  const words = game.words ?? {};
  const waiting = (state.waiting?.participantIds ?? [])
    .filter((seat) => seat !== participantId)
    .map((seat) => seatKeys[seat] ?? seat);
  const situation = Object.entries(view.publicState)
    .map(([key, value]) => `${words[key] ?? key}：${renderValue(value, words, seatKeys)}`)
    .join("；");

  return [
    "## 现在",
    `轮到你行动了。当前步骤：${words[state.stepId] ?? state.stepId}。`,
    waiting.length > 0 ? `这一步还在等：${waiting.join("、")}。` : "",
    "## 现在的局面",
    situation.length === 0 ? "（没有公开状态）" : situation,
    allowedSection(allowed),
    budgetSection(input.attempt),
    "## 输出要求",
    "用一次工具调用完成你的动作，参数按工具定义填写。",
    "发言会原样播给全桌，包括（笑）（小声）（叹气）这类括号语气。",
  ]
    .filter((line) => line.length > 0)
    .join("\n");
}

/**
 * What the seat gets after a try that did not land. Same budget block as the opening
 * instruction, so the countdown is never the model's job to guess.
 */
export function retryInstruction(input: BuildSeatPromptInput, reason: string): string {
  const allowed = allowedActions(input.game, input.state).map((action) => action.name);
  return [
    "## 上一次没有成功",
    reason,
    allowedSection(allowed),
    budgetSection(input.attempt),
    "## 输出要求",
    allowed.length === 0
      ? "本步没有可用的动作。"
      : `改为调用「${allowed.join("、")}」之一，不要重复刚才那个动作。`,
  ].join("\n");
}

function allowedSection(allowed: readonly string[]): string {
  const body = allowed.length === 0 ? "（无）" : allowed.join("、");
  return `## 本步允许的动作\n${body}\n除此之外的动作现在一律无效，调用会被拒绝。`;
}

/**
 * The platform's hard limits, stated once. `limit` is fixed for the whole match, so it sits in the
 * cached header with the rules; only the tries already spent move (see `budgetSection`).
 */
function actionLimits(limit: number): string {
  return [
    "你只能通过工具行动：每次只能调用一个工具。",
    `这次行动最多尝试 ${limit} 次；次数用完仍没有一个动作被接受，这一步就作废，你会失去这次行动，本局继续。`,
    "只有最后一条消息里「本步允许的动作」列出的动作现在有效，其余动作会被拒绝。",
  ].join("\n");
}

/** Just the moving part of the budget: the limit itself is a rule and never travels here. */
function budgetSection(attempt: { index: number; limit: number }): string {
  const left = Math.max(attempt.limit - attempt.index + 1, 0);
  return [
    "## 你的尝试预算",
    `现在是这次行动的第 ${attempt.index} 次，还剩 ${left} 次（含这一次）。`,
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
