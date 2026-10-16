import type { GameState, PlayerView } from "../../shared/index.js";
import { EngineError } from "./errors.js";

/**
 * Visibility rules are fail-closed: a variable that the definition does not list
 * is never projected. Unparseable rules are hard errors rather than a silent
 * "visible", so a typo cannot leak hidden state.
 */
export type VisibilityRule =
  | { kind: "public" }
  | { kind: "role"; roleId: string }
  | { kind: "participant"; participantId: string };

export type Viewer = { kind: "participant"; participantId: string } | { kind: "spectator" };

export function parseVisibilityRule(variable: string, raw: unknown): VisibilityRule {
  if (raw === "public") return { kind: "public" };
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    const keys = Object.keys(raw);
    if (keys.length === 1 && keys[0] === "role") {
      const roleId = (raw as { role: unknown }).role;
      if (typeof roleId === "string" && roleId.length > 0) return { kind: "role", roleId };
    }
    if (keys.length === 1 && keys[0] === "participant") {
      const participantId = (raw as { participant: unknown }).participant;
      if (typeof participantId === "string" && participantId.length > 0) {
        return { kind: "participant", participantId };
      }
    }
  }
  throw new EngineError(
    "INVALID_VISIBILITY_RULE",
    `Visibility rule for "${variable}" must be "public", {"role": id} or {"participant": id}`,
  );
}

/** The visibility map a game declares: variable name to rule. Absent means nobody sees it. */
export type Visibility = Record<string, unknown>;

export function parseVisibilityRules(visibility: Visibility): Map<string, VisibilityRule> {
  const rules = new Map<string, VisibilityRule>();
  for (const [variable, raw] of Object.entries(visibility)) {
    rules.set(variable, parseVisibilityRule(variable, raw));
  }
  return rules;
}

function roleOf(state: GameState, participantId: string): string | undefined {
  const participant = state.participants.find(
    (candidate) => candidate.participantId === participantId,
  );
  if (!participant) {
    throw new EngineError(
      "UNKNOWN_PARTICIPANT",
      `Participant is not part of the instance: ${participantId}`,
    );
  }
  return participant.roleId;
}

function isVisibleTo(
  rule: VisibilityRule,
  viewer: Viewer,
  viewerRole: string | undefined,
): boolean {
  if (rule.kind === "public") return true;
  if (viewer.kind === "spectator") return false;
  if (rule.kind === "participant") return rule.participantId === viewer.participantId;
  return viewerRole === rule.roleId;
}

/**
 * Projects the authoritative state for one viewer. `publicState` holds rules that
 * resolve to public, `privateState` holds everything else the viewer may see — so
 * a private value can never appear in the public bucket.
 */
export function projectPlayerView(
  visibility: Visibility,
  state: GameState,
  viewer: Viewer,
): PlayerView {
  const rules = parseVisibilityRules(visibility);
  const viewerRole =
    viewer.kind === "participant" ? roleOf(state, viewer.participantId) : undefined;

  const publicState: Record<string, unknown> = {};
  const privateState: Record<string, unknown> = {};
  for (const [variable, rule] of rules) {
    if (!(variable in state.variables)) continue;
    if (!isVisibleTo(rule, viewer, viewerRole)) continue;
    if (rule.kind === "public") {
      publicState[variable] = state.variables[variable];
    } else {
      privateState[variable] = state.variables[variable];
    }
  }

  return {
    instanceId: state.instanceId,
    gameVersionId: state.gameVersionId,
    sequence: state.sequence,
    status: state.status,
    publicState,
    privateState,
    availableActions: projectAvailableActions(state, viewer),
  };
}

function projectAvailableActions(state: GameState, viewer: Viewer): PlayerView["availableActions"] {
  const waiting = state.waiting;
  if (!waiting || viewer.kind === "spectator") return [];
  if (waiting.participantIds.length > 0 && !waiting.participantIds.includes(viewer.participantId)) {
    return [];
  }
  // Human and AI see the same vocabulary: the action names the game allows at this step.
  return waiting.actions.map((name) => ({
    actionId: name,
    input: { participantId: viewer.participantId },
  }));
}
