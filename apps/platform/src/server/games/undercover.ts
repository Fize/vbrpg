import type { GameEvent, GameState, Participant } from "../../shared/index.js";
import { platformEventTypes } from "../../shared/index.js";
import { EngineError, type TransitionResult } from "../game/errors.js";
import {
  createBaseState,
  type ActionDefinition,
  type CreateInstanceInput,
  type GameModule,
  type SetupField,
} from "../game/module.js";
import type { Visibility } from "../game/projector.js";

/**
 * 「谁是卧底」：多数席位拿到同一个词，一名卧底拿到近义词。每回合先轮流描述、再全体投票，
 * 票高者出局；卧底出局则平民胜，卧底与最后两人同场则卧底胜。
 *
 * 隐藏信息只有两样：自己的词（`word:<participantId>`，只对该席位可见）与投票内容
 * （`votes` 不写进可见性，任何席位都看不到；只有结算后的 `summary` 公开）。
 */

const MIN_SEATS = 3;

/**
 * The words are not the game's: the creator gives a category, the platform's model turns it into a
 * pair, and the pair goes straight into the deal. Nobody sees the words before they are dealt.
 */
const SETUP: readonly SetupField[] = [
  {
    name: "category",
    label: "分类",
    description: "例如 水果、动物、三国人物",
    kind: "category",
  },
  { name: "civilianWord", label: "平民的词", description: "由分类生成", from: "pair.civilian" },
  { name: "undercoverWord", label: "卧底的词", description: "由分类生成", from: "pair.undercover" },
];

function requiredWord(variables: Record<string, unknown>, name: string): string {
  const value = variables[name];
  if (typeof value !== "string" || value.trim() === "") {
    throw new EngineError("WORDS_REQUIRED", `This round needs "${name}" before it can start`);
  }
  return value.trim();
}

type UndercoverVariables = {
  phase: "describe" | "vote" | "over";
  round: number;
  alive: string[];
  spoken: string[];
  votes: Record<string, string>;
  summary: {
    round: number;
    tally: Record<string, number>;
    eliminated: string | null;
    tie: boolean;
  } | null;
  winner: string | null;
};

function variablesOf(state: GameState): UndercoverVariables {
  return state.variables as unknown as UndercoverVariables;
}

/** Deterministic from the seed: `initialState` must not read a clock or a random source. */
function hash(input: string): number {
  let value = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    value ^= input.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return Math.abs(value);
}

const ACTIONS: readonly ActionDefinition[] = [
  {
    name: platformEventTypes.seatMessage,
    label: "描述",
    description: "用一句话描述你拿到的词，不要直接说出它。",
    args: { text: { description: "你要说的话" } },
    audience: "room",
  },
  {
    name: "vote",
    label: "投票",
    description: "投出你认为最像卧底的席位。",
    args: { target: { description: "要投的席位", kind: "seat" } },
    audience: "seat",
  },
];

/** The game's own vocabulary, so no screen has to show a machine word. */
const STEP_NAMES: Readonly<Record<string, string>> = {
  start: "开局",
  describe: "描述阶段",
  vote: "投票阶段",
  resolve: "结算",
  over: "对局结束",
};

const WORD_NAMES: Readonly<Record<string, string>> = {
  word: "你的词",
  category: "分类",
  phase: "阶段",
  round: "回合",
  alive: "在场席位",
  spoken: "已发言",
  votes: "选票",
  summary: "上轮结算",
  winner: "胜方",
  tally: "票数",
  eliminated: "出局席位",
  tie: "平票",
  civilian: "平民",
  undercover: "卧底",
  describe: "描述",
  vote: "投票",
  resolve: "结算",
  over: "结束",
  describePhaseEnded: "描述阶段结束",
  votesRevealed: "投票结算",
};

function waitingFor(stepId: "describe" | "vote", seats: string[]): GameState["waiting"] {
  return {
    kind: "collectInput",
    stepId,
    participantIds: seats,
    actions: stepId === "describe" ? [platformEventTypes.seatMessage] : ["vote"],
  };
}

function withStatus(participants: Participant[], eliminated: string | null): Participant[] {
  if (eliminated === null) return participants;
  return participants.map((seat) =>
    seat.participantId === eliminated ? { ...seat, status: "eliminated" as const } : seat,
  );
}

/** A derived event reports why the phase changed; the platform gives it a sequence and a key. */
function derived(state: GameState, type: string, payload: Record<string, unknown>): GameEvent {
  const sequence = state.sequence + 1;
  return {
    eventId: `${state.instanceId}:${sequence}:${type}`,
    instanceId: state.instanceId,
    sequence,
    type,
    participantId: null,
    actorUserId: null,
    stepId: state.stepId,
    occurredAtMs: 0,
    idempotencyKey: `${state.instanceId}:${sequence}:${type}`,
    payload,
    usage: null,
  };
}

function requireActor(state: GameState, participantId: string | null): string {
  if (participantId === null) {
    throw new EngineError("SEAT_REQUIRED", "This event must come from a seat");
  }
  if (!state.participants.some((seat) => seat.participantId === participantId)) {
    throw new EngineError("UNKNOWN_SEAT", "That seat is not in this match");
  }
  if (!variablesOf(state).alive.includes(participantId)) {
    throw new EngineError("SEAT_NOT_ACTIVE", "That seat is not part of the round");
  }
  return participantId;
}

export const undercover: GameModule = {
  id: "undercover",
  title: "谁是卧底",
  version: "1.0.0",
  engineVersion: "core-1",
  actions: ACTIONS,
  steps: STEP_NAMES,
  setup: SETUP,
  words: WORD_NAMES,

  /** The rules, in the game's own words. Stable for the match, so it can sit in the prompt head. */
  briefing(state: GameState, participantId: string): string {
    const seat = state.participants.find((candidate) => candidate.participantId === participantId);
    if (!seat) throw new EngineError("UNKNOWN_SEAT", "That seat is not in this match");
    return [
      "你在玩「谁是卧底」。大多数席位拿到同一个词，只有一名卧底拿到近义词。",
      "每回合先由所有在世席位轮流用一句话描述自己的词，然后全体投票，得票最多的席位出局。",
      "卧底出局则平民获胜；卧底留到最后两人则卧底获胜。平票时不淘汰，直接进入下一回合。",
      `你在这局里的角色是 ${seat.roleId === "undercover" ? "卧底" : "平民"}。`,
      "不要直接说出你的词，用一句话让别人猜不出又让同伴认得出。",
    ].join("\n");
  },

  /**
   * Rules are computed from the state because a seat's secret is only addressable once the seats
   * exist. Everything absent from the map — including `votes` — is visible to nobody.
   */
  visibility(state: GameState): Visibility {
    const rules: Visibility = {
      category: "public",
      phase: "public",
      round: "public",
      alive: "public",
      summary: "public",
      winner: "public",
    };
    for (const seat of state.participants) {
      rules[`word:${seat.participantId}`] = { participant: seat.participantId };
    }
    return rules;
  },

  initialState(input: CreateInstanceInput): GameState {
    if (input.participants.length < MIN_SEATS) {
      throw new EngineError("TOO_FEW_SEATS", `At least ${MIN_SEATS} seats are required`);
    }

    const civilianWord = requiredWord(input.variables ?? {}, "civilianWord");
    const undercoverWord = requiredWord(input.variables ?? {}, "undercoverWord");
    if (civilianWord === undercoverWord) {
      throw new EngineError("WORDS_IDENTICAL", "The two words must differ");
    }
    const undercoverIndex = hash(`${input.randomSeed}#u`) % input.participants.length;
    const alive = input.participants.map((seat) => seat.participantId);

    const category = input.variables?.["category"];
    const variables: Record<string, unknown> = {
      ...(typeof category === "string" && category.trim() !== ""
        ? { category: category.trim() }
        : {}),
      phase: "describe",
      round: 1,
      alive,
      spoken: [],
      votes: {},
      summary: null,
      winner: null,
    };
    for (const [index, seat] of input.participants.entries()) {
      variables[`word:${seat.participantId}`] =
        index === undercoverIndex ? undercoverWord : civilianWord;
    }

    const state = createBaseState(
      {
        ...input,
        participants: input.participants.map((seat, index) => ({
          ...seat,
          roleId: index === undercoverIndex ? "undercover" : "civilian",
        })),
      },
      variables,
    );

    return {
      ...state,
      status: "waiting",
      stepId: "describe",
      waiting: waitingFor("describe", alive),
    };
  },

  transition(state: GameState, event): TransitionResult {
    const variables = variablesOf(state);

    switch (event.type) {
      case platformEventTypes.instanceCreated: {
        return { state: { ...state, status: "waiting", stepId: "describe" }, events: [] };
      }

      case platformEventTypes.seatMessage: {
        if (variables.phase !== "describe") {
          throw new EngineError(
            "NOT_DESCRIBING",
            "Descriptions are only accepted in the describe phase",
          );
        }
        const speaker = requireActor(state, event.participantId);
        const spoken = variables.spoken.includes(speaker)
          ? variables.spoken
          : [...variables.spoken, speaker];
        const pending = variables.alive.filter((seat) => !spoken.includes(seat));
        if (pending.length > 0) {
          return {
            state: {
              ...state,
              variables: { ...state.variables, spoken },
              waiting: waitingFor("describe", pending),
            },
            events: [],
          };
        }
        // Everyone has described; the phase change gets its own row so the record explains itself.
        return {
          state: {
            ...state,
            stepId: "vote",
            waiting: waitingFor("vote", variables.alive),
            variables: { ...state.variables, spoken, phase: "vote", votes: {} },
          },
          events: [derived(state, "describePhaseEnded", { round: variables.round })],
        };
      }

      case "describePhaseEnded": {
        return {
          state: { ...state, stepId: "vote", waiting: waitingFor("vote", variables.alive) },
          events: [],
        };
      }

      case "vote": {
        if (variables.phase !== "vote") {
          throw new EngineError("NOT_VOTING", "Votes are only accepted in the vote phase");
        }
        const voter = requireActor(state, event.participantId);
        const target = String(event.payload["target"] ?? "");
        if (!variables.alive.includes(target)) {
          throw new EngineError("UNKNOWN_TARGET", "The target is not an active seat");
        }
        if (target === voter) {
          throw new EngineError("SELF_VOTE", "A seat cannot vote for itself");
        }
        if (variables.votes[voter] !== undefined) {
          throw new EngineError("ALREADY_VOTED", "That seat already voted this round");
        }

        const votes = { ...variables.votes, [voter]: target };
        const pending = variables.alive.filter((seat) => votes[seat] === undefined);
        if (pending.length > 0) {
          return {
            state: {
              ...state,
              variables: { ...state.variables, votes },
              waiting: waitingFor("vote", pending),
            },
            events: [],
          };
        }
        return {
          state: {
            ...state,
            stepId: "resolve",
            waiting: null,
            variables: { ...state.variables, votes },
          },
          events: [derived(state, "votesRevealed", { round: variables.round })],
        };
      }

      case "votesRevealed": {
        return resolveRound(state);
      }

      default: {
        // Unknown types are recorded and ignored: the same record also carries platform rows that
        // no rule needs to understand.
        return { state, events: [] };
      }
    }
  },
};

function resolveRound(state: GameState): TransitionResult {
  const variables = variablesOf(state);
  const tally: Record<string, number> = {};
  for (const target of Object.values(variables.votes)) {
    tally[target] = (tally[target] ?? 0) + 1;
  }

  const ranked = Object.entries(tally).sort((left, right) =>
    right[1] === left[1] ? left[0].localeCompare(right[0]) : right[1] - left[1],
  );
  const top = ranked[0];
  const tied = top !== undefined && ranked[1] !== undefined && ranked[1][1] === top[1];
  const eliminated = top === undefined || tied ? null : top[0];

  const alive =
    eliminated === null ? variables.alive : variables.alive.filter((seat) => seat !== eliminated);
  const undercoverAlive = state.participants.some(
    (seat) => seat.roleId === "undercover" && alive.includes(seat.participantId),
  );
  const summary = { round: variables.round, tally, eliminated, tie: tied };

  const winner =
    eliminated === null
      ? null
      : !undercoverAlive
        ? "civilian"
        : alive.length <= 2
          ? "undercover"
          : null;

  if (winner !== null) {
    return {
      state: {
        ...state,
        status: "completed",
        stepId: "over",
        waiting: null,
        participants: withStatus(state.participants, eliminated),
        variables: { ...state.variables, phase: "over", alive, votes: {}, summary, winner },
      },
      events: [],
    };
  }

  return {
    state: {
      ...state,
      participants: withStatus(state.participants, eliminated),
      stepId: "describe",
      waiting: waitingFor("describe", alive),
      variables: {
        ...state.variables,
        phase: "describe",
        round: variables.round + 1,
        alive,
        spoken: [],
        votes: {},
        summary,
        winner: null,
      },
    },
    events: [],
  };
}
