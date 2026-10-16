import type { GameAction, GameVocabulary, MatchRecordRow } from "./api";
import { describePayload, eventLabel } from "./match-labels";

/**
 * How a row reads in the room's log. The kind comes from the platform's vocabulary and the game's
 * action catalogue — `room` content is the table's, `seat` content is one seat's — never from a
 * game's own event names, which the platform does not know.
 */
export type LogKind = "speech" | "private" | "phase" | "model" | "system";

export interface LogEntry {
  eventId: string;
  sequence: number;
  kind: LogKind;
  label: string;
  seat: string;
  text: string;
  /** Set on model rows: what the seat was thinking, what it asked for and what it cost. */
  model: {
    reasoning: string;
    toolCalls: Array<{ name: string; label: string; text: string }>;
    usage: string;
  } | null;
}

const PLATFORM_KINDS: Record<string, LogKind> = {
  instanceCreated: "system",
  playerInputReceived: "system",
  adminCommandApplied: "system",
  timerExpired: "system",
  randomResolved: "system",
  aiCall: "model",
  aiFailed: "model",
};

function textOf(row: MatchRecordRow, key: string): string {
  const value = row.payload[key];
  if (value === undefined || value === null) return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}

function usageText(row: MatchRecordRow): string {
  if (row.usage === null) return "";
  return `${row.usage.modelId} · 输入 ${row.usage.promptTokens} · 输出 ${row.usage.completionTokens} · 合计 ${row.usage.totalTokens}`;
}

function toolsOf(
  row: MatchRecordRow,
): Array<{ name: string; id: string; payload: Record<string, unknown> }> {
  const raw = row.payload["toolCalls"];
  if (!Array.isArray(raw)) return [];
  const calls: Array<{ name: string; id: string; payload: Record<string, unknown> }> = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) continue;
    const call = item as Record<string, unknown>;
    let payload: Record<string, unknown> = {};
    try {
      const parsed: unknown = JSON.parse(String(call["arguments"] ?? "{}"));
      if (typeof parsed === "object" && parsed !== null)
        payload = parsed as Record<string, unknown>;
    } catch {
      payload = {};
    }
    calls.push({ name: String(call["name"] ?? ""), id: String(call["id"] ?? ""), payload });
  }
  return calls;
}

export function buildLog(input: {
  record: readonly MatchRecordRow[];
  actions: readonly GameAction[];
  game: GameVocabulary;
  seatName: (participantId: string | null) => string;
}): LogEntry[] {
  const byName = new Map(input.actions.map((action) => [action.name, action]));
  const seatName = (participantId: string | null): string =>
    participantId === null ? "平台" : input.seatName(participantId);

  return input.record.map((row) => {
    const action = byName.get(row.type);
    const kind: LogKind =
      PLATFORM_KINDS[row.type] ??
      ((action?.audience ?? "room") === "seat" ? "private" : action ? "speech" : "phase");

    return {
      eventId: row.eventId,
      sequence: row.sequence,
      kind,
      label: eventLabel(input.actions, input.game.words, row.type),
      seat: seatName(row.participantId),
      text:
        kind === "model"
          ? ""
          : describePayload({
              payload: row.payload,
              action,
              words: input.game.words,
              seatName,
            }),
      model:
        kind === "model"
          ? {
              reasoning: textOf(row, "reasoning"),
              toolCalls: toolsOf(row).map((call) => ({
                name: call.name,
                label: eventLabel(input.actions, input.game.words, call.name),
                text: describePayload({
                  payload: call.payload,
                  action: byName.get(call.name),
                  words: input.game.words,
                  seatName,
                }),
              })),
              usage: usageText(row),
            }
          : null,
    };
  });
}
