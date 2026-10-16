import type { GameAction, GameVocabulary, MatchSummary } from "./api";

type MatchStatus = MatchSummary["status"];

/** The platform's lifecycle vocabulary, in one place: the API only ever sends these words. */
const STATUS_LABELS: Record<MatchStatus, string> = {
  created: "已创建",
  running: "进行中",
  waiting: "等待行动",
  paused: "已暂停",
  completed: "已结束",
  cancelled: "已取消",
};

const STATUS_TAGS: Record<MatchStatus, "success" | "info" | "warning" | "danger"> = {
  created: "info",
  running: "success",
  waiting: "warning",
  paused: "warning",
  completed: "info",
  cancelled: "danger",
};

/** Seat status is the platform's word too, so it reads in Chinese everywhere. */
const SEAT_STATUS_LABELS: Record<string, string> = {
  active: "在场",
  eliminated: "出局",
  disconnected: "掉线",
  finished: "已结束",
};

/** Rows the platform writes itself. A game's own events are named by the game's catalogue. */
const PLATFORM_EVENT_LABELS: Record<string, string> = {
  instanceCreated: "对局创建",
  playerInputReceived: "收到输入",
  aiCall: "模型调用",
  aiFailed: "模型失败",
  timerExpired: "超时",
  randomResolved: "随机结算",
  adminCommandApplied: "管理员指令",
};

export function statusLabel(status: MatchStatus): string {
  return STATUS_LABELS[status];
}

export function statusTag(status: MatchStatus): "success" | "info" | "warning" | "danger" {
  return STATUS_TAGS[status];
}

/** Whether the platform still accepts input for this match. */
export function isOpen(status: MatchStatus): boolean {
  return status === "created" || status === "running" || status === "waiting";
}

export function seatStatusLabel(status: string): string {
  return SEAT_STATUS_LABELS[status] ?? status;
}

/** A step the game declared reads by its name; anything else stays as the game wrote it. */
export function stepLabel(game: GameVocabulary, stepId: string): string {
  return game.steps[stepId] ?? stepId;
}

/** An event reads in the game's words when it named them, in the platform's otherwise. */
export function eventLabel(
  actions: readonly GameAction[],
  words: Record<string, string>,
  type: string,
): string {
  return (
    actions.find((action) => action.name === type)?.label ??
    words[type] ??
    PLATFORM_EVENT_LABELS[type] ??
    type
  );
}

export function formatTime(value: number | string): string {
  const date = typeof value === "number" ? new Date(value) : new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

/**
 * The game's own words, applied to whatever a screen is about to show: a value that is one of this
 * match's seats reads as its seat key, a word the game named reads in Chinese, and anything else is
 * shown exactly as it came from the backend.
 */
export function wordText(
  value: unknown,
  words: Record<string, string>,
  seatName: (participantId: string) => string,
): string {
  if (typeof value === "string") {
    const named = seatName(value);
    return named === value ? (words[value] ?? value) : named;
  }
  if (Array.isArray(value)) return value.map((item) => wordText(item, words, seatName)).join("、");
  if (typeof value === "boolean") return value ? "是" : "否";
  if (value === null) return "—";
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${words[key] ?? seatName(key)}：${wordText(item, words, seatName)}`)
      .join("、");
  }
  return JSON.stringify(value);
}

/**
 * One payload as a sentence: the action's own argument names, its own words, and its seat
 * arguments read by seat key. Nothing here knows a game.
 */
export function describePayload(input: {
  payload: Record<string, unknown>;
  action: GameAction | undefined;
  words: Record<string, string>;
  seatName: (participantId: string) => string;
}): string {
  const entries = Object.entries(input.payload);
  if (entries.length === 0) return "（无内容）";
  return entries
    .map(([key, value]) => {
      const arg = input.action?.args?.[key];
      const label = arg?.description ?? input.words[key] ?? key;
      const text =
        arg?.kind === "seat" && typeof value === "string"
          ? input.seatName(value)
          : wordText(value, input.words, input.seatName);
      return `${label}：${text}`;
    })
    .join(" · ");
}
