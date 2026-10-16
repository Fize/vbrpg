import type { GameAction, MatchRecordRow } from "./api";
import { eventLabel, payloadText } from "./match-labels";

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
  /** Set on model rows: what the seat was thinking and what it cost. */
  model: {
    reasoning: string;
    toolCalls: Array<{ name: string; arguments: string }>;
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

function toolCallsOf(row: MatchRecordRow): Array<{ name: string; arguments: string }> {
  const raw = row.payload["toolCalls"];
  if (!Array.isArray(raw)) return [];
  const calls: Array<{ name: string; arguments: string }> = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) continue;
    const call = item as Record<string, unknown>;
    calls.push({ name: String(call["name"] ?? ""), arguments: String(call["arguments"] ?? "") });
  }
  return calls;
}

function usageOf(row: MatchRecordRow): string {
  if (row.usage === null) return "";
  return `${row.usage.modelId} · ${row.usage.promptTokens}/${row.usage.completionTokens}/${row.usage.totalTokens}`;
}

export function buildLog(input: {
  record: readonly MatchRecordRow[];
  actions: readonly GameAction[];
  seatName: (participantId: string | null) => string;
}): LogEntry[] {
  const audience = new Map(input.actions.map((action) => [action.name, action.audience ?? "room"]));
  /** Payload fields the catalogue declares as seats, so a log line reads `target: s2`. */
  const seatArgs = new Map(
    input.actions.map((action) => [
      action.name,
      new Set(
        Object.entries(action.args ?? {})
          .filter(([, arg]) => arg.kind === "seat")
          .map(([name]) => name),
      ),
    ]),
  );

  return input.record.map((row) => {
    const kind: LogKind =
      PLATFORM_KINDS[row.type] ??
      (audience.get(row.type) === "seat" ? "private" : audience.has(row.type) ? "speech" : "phase");
    const calls = toolCallsOf(row);

    return {
      eventId: row.eventId,
      sequence: row.sequence,
      kind,
      label: eventLabel(row.type),
      seat: input.seatName(row.participantId),
      text:
        kind === "model"
          ? ""
          : payloadText(row.payload, (key, value) =>
              seatArgs.get(row.type)?.has(key) === true && typeof value === "string"
                ? input.seatName(value)
                : null,
            ),
      model:
        kind === "model"
          ? {
              reasoning: textOf(row, "reasoning"),
              toolCalls: calls,
              usage: usageOf(row),
            }
          : null,
    };
  });
}
