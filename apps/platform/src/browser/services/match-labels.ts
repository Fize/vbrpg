import type { MatchSummary } from "./api";

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

/** Event types a reader sees often; anything else is shown by its own name. */
const EVENT_LABELS: Record<string, string> = {
  instanceCreated: "对局创建",
  seatMessage: "席位发言",
  vote: "投票",
  aiCall: "模型调用",
  aiFailed: "模型失败",
  playerInputReceived: "收到输入",
  describePhaseEnded: "描述阶段结束",
  votesRevealed: "投票结算",
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

export function eventLabel(type: string): string {
  return EVENT_LABELS[type] ?? type;
}

export function formatTime(value: number | string): string {
  const date = typeof value === "number" ? new Date(value) : new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

/** Payload values as they are: no invented semantics, no hidden fields. */
export function payloadText(payload: Record<string, unknown>): string {
  const entries = Object.entries(payload);
  if (entries.length === 0) return "（无内容）";
  return entries
    .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join(" · ");
}
