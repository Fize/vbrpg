import type { GameEvent, GameState, Participant } from "../../shared/index.js";
import { platformEventTypes } from "../../shared/index.js";
import { EngineError, type TransitionResult } from "../game/errors.js";
import { seededIndex } from "../game/seeded.js";
import {
  createBaseState,
  type ActionDefinition,
  type CreateInstanceInput,
  type GameModule,
  type SetupField,
} from "../game/module.js";
import type { Visibility } from "../game/projector.js";

/**
 * 「谁是卧底」：多数席位拿到同一个词，一名卧底拿到近义词。每回合先按席位顺序轮流描述、再讨论
 * 至多三轮、然后全体投票，票高者出局（平票则重投一次，仍平票不淘汰）；卧底出局则平民胜，
 * 卧底留到最后两人则卧底胜。
 *
 * 隐藏信息只有两样：自己的词（`word:<participantId>`，只对该席位可见）与投票内容
 * （`votes` 不写进可见性，任何席位都看不到；只有结算后的 `summary` 公开）。
 */

const MIN_SEATS = 3;
const MAX_SEATS = 12;
/** Talking stops when the rules say so: after this many rounds comes the vote, not another round. */
const DISCUSSION_ROUNDS = 3;

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
  // The other way in: the creator types both words, and then may only watch. Which of the two the
  // undercover gets is a coin flip from the seed, so knowing the words is not knowing the roles.
  { name: "wordA", label: "词一", description: "与词二相近", kind: "word" },
  { name: "wordB", label: "词二", description: "与词一相近", kind: "word" },
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
  phase: "describe" | "discuss" | "vote" | "over";
  round: number;
  /** Which discussion round is running, 1 to `DISCUSSION_ROUNDS`. */
  discussRound: number;
  alive: string[];
  spoken: string[];
  /** Seats handled in the current discussion round — speaking and skipping count the same. */
  discussed: string[];
  votes: Record<string, string>;
  /** A tie sends the table back to the vote once; the second tie lets the round go by. */
  revoted: boolean;
  /** When a revote is running, only the seats that tied may be voted for. */
  revoteTargets: string[];
  /** What each seat did, so the end of the match can be read back seat by seat. */
  stats: Record<string, { spoke: number; votesAgainst: number; survivedRounds: number }>;
  summary: {
    round: number;
    tally: Record<string, number>;
    eliminated: string | null;
    tie: boolean;
    revote: boolean;
  } | null;
  winner: string | null;
  /** Seat-by-seat report, written once when the match ends. */
  scores: Array<{
    seat: string;
    role: string;
    spoke: number;
    votesAgainst: number;
    survivedRounds: number;
    won: boolean;
  }> | null;
};

function variablesOf(state: GameState): UndercoverVariables {
  return state.variables as unknown as UndercoverVariables;
}

const ACTIONS: readonly ActionDefinition[] = [
  {
    name: platformEventTypes.seatMessage,
    label: "发言",
    description:
      "用一句话说给全桌听：描述阶段用一句话描述你的词，讨论阶段可以质疑、辩解、给人理由。不要直接说出自己的词。",
    args: { text: { description: "你要说的话" } },
    audience: "room",
  },
  {
    name: "skipDiscussion",
    label: "这轮不说",
    description: "讨论时你这一轮不发言，直接轮到下一位；轮次照常推进。",
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
  discuss: "讨论阶段",
  vote: "投票阶段",
  resolve: "结算",
  over: "对局结束",
};

const WORD_NAMES: Readonly<Record<string, string>> = {
  word: "你的词",
  category: "分类",
  phase: "阶段",
  round: "回合",
  discussRound: "讨论轮次",
  alive: "在场席位",
  spoken: "已发言",
  discussed: "本轮已说话",
  votes: "选票",
  summary: "上轮结算",
  winner: "胜方",
  tally: "票数",
  eliminated: "出局席位",
  tie: "平票",
  revoted: "已重投",
  revoteTargets: "重投候选人",
  scores: "表现",
  seat: "席位",
  role: "身份",
  spoke: "发言次数",
  votesAgainst: "被投票",
  survivedRounds: "存活回合",
  won: "胜负",
  civilian: "平民",
  undercover: "卧底",
  describe: "描述",
  discuss: "讨论",
  vote: "投票",
  resolve: "结算",
  over: "结束",
  describePhaseEnded: "描述阶段结束",
  discussRoundEnded: "讨论轮次结束",
  discussionEnded: "讨论结束",
  revoteStarted: "开始重投",
  votesRevealed: "投票结算",
  skipDiscussion: "（跳过）",
};

function waitingFor(
  stepId: "describe" | "discuss" | "vote",
  seats: string[],
): GameState["waiting"] {
  const actions =
    stepId === "describe"
      ? [platformEventTypes.seatMessage]
      : stepId === "discuss"
        ? [platformEventTypes.seatMessage, "skipDiscussion"]
        : ["vote"];
  return { kind: "collectInput", stepId, participantIds: seats, actions };
}

/** Speaking is what the end-of-match report counts; sitting out a discussion round is not. */
function countSpeak(
  stats: UndercoverVariables["stats"],
  seat: string,
): UndercoverVariables["stats"] {
  const current = stats[seat] ?? { spoke: 0, votesAgainst: 0, survivedRounds: 0 };
  return { ...stats, [seat]: { ...current, spoke: current.spoke + 1 } };
}

/**
 * The description phase runs in a fixed order: only the next seat in line is asked, so nobody can
 * jump the queue and no seat is asked for a line it already gave.
 */
function describeWaiting(alive: string[], spoken: string[]): GameState["waiting"] {
  const next = alive.find((seat) => !spoken.includes(seat));
  return waitingFor("describe", next === undefined ? alive : [next]);
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
  minSeats: MIN_SEATS,
  maxSeats: MAX_SEATS,
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
      "每回合分三段：所有在世席位按席位表顺序、一人一句描述自己的词；然后讨论至多三轮，每轮每人最多说一次，",
      "也可以选择这轮不说；最后全体投票，得票最多的席位出局。第三轮讨论结束后只能投票，不能再发言。",
      "投票出现平票时立刻重投一次，且只能投平票的那几个席位；重投仍然平票就不淘汰，直接进入下一回合。",
      "出局的席位不再发言，身份要到对局结束才公开。卧底出局则平民获胜；卧底留到最后两人则卧底获胜。",
      `你在这局里的角色是 ${seat.roleId === "undercover" ? "卧底" : "平民"}。`,
      "不要直接说出你的词，用一句话让别人猜不出又让同伴认得出。",
      "说话可以带（笑）（小声）（叹气）这类括号语气，平台会原样播出。",
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
      discussRound: "public",
      alive: "public",
      discussed: "public",
      summary: "public",
      winner: "public",
      scores: "public",
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
    if (input.participants.length > MAX_SEATS) {
      throw new EngineError("TOO_MANY_SEATS", `At most ${MAX_SEATS} seats are supported`);
    }

    const civilianWord = requiredWord(input.variables ?? {}, "civilianWord");
    const undercoverWord = requiredWord(input.variables ?? {}, "undercoverWord");
    if (civilianWord === undercoverWord) {
      throw new EngineError("WORDS_IDENTICAL", "The two words must differ");
    }
    const undercoverIndex = seededIndex(input.randomSeed, "u", input.participants.length);
    const alive = input.participants.map((seat) => seat.participantId);

    const category = input.variables?.["category"];
    const stats: UndercoverVariables["stats"] = {};
    for (const seat of alive) {
      stats[seat] = { spoke: 0, votesAgainst: 0, survivedRounds: 0 };
    }
    const variables: Record<string, unknown> = {
      ...(typeof category === "string" && category.trim() !== ""
        ? { category: category.trim() }
        : {}),
      phase: "describe",
      round: 1,
      discussRound: 1,
      alive,
      spoken: [],
      discussed: [],
      votes: {},
      revoted: false,
      revoteTargets: [],
      stats,
      summary: null,
      winner: null,
      scores: null,
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
      waiting: describeWaiting(alive, []),
    };
  },

  transition(state: GameState, event): TransitionResult {
    const variables = variablesOf(state);

    switch (event.type) {
      case platformEventTypes.instanceCreated: {
        return { state: { ...state, status: "waiting", stepId: "describe" }, events: [] };
      }

      case platformEventTypes.seatMessage: {
        const speaker = requireActor(state, event.participantId);
        const stats = countSpeak(variables.stats, speaker);
        if (variables.phase === "describe") {
          const next = variables.alive.find((seat) => !variables.spoken.includes(seat));
          if (next !== speaker) {
            throw new EngineError("OUT_OF_ORDER", "The description phase runs in seat order");
          }
          const spoken = [...variables.spoken, speaker];
          const pending = variables.alive.filter((seat) => !spoken.includes(seat));
          if (pending.length > 0) {
            return {
              state: {
                ...state,
                variables: { ...state.variables, spoken, stats },
                waiting: describeWaiting(variables.alive, spoken),
              },
              events: [],
            };
          }
          // Everyone has described; the phase change gets its own row so the record explains itself.
          return {
            state: {
              ...state,
              stepId: "discuss",
              waiting: waitingFor("discuss", variables.alive),
              variables: {
                ...state.variables,
                spoken,
                stats,
                phase: "discuss",
                discussRound: 1,
                discussed: [],
              },
            },
            events: [derived(state, "describePhaseEnded", { round: variables.round })],
          };
        }
        if (variables.phase !== "discuss") {
          throw new EngineError(
            "NOT_DISCUSSING",
            "The discussion is over: only votes are accepted now",
          );
        }
        if (variables.discussed.includes(speaker)) {
          throw new EngineError("ALREADY_DISCUSSED", "That seat has already spoken this round");
        }
        return advanceDiscussion({ ...state, variables: { ...state.variables, stats } }, [
          ...variables.discussed,
          speaker,
        ]);
      }

      case "skipDiscussion": {
        if (variables.phase !== "discuss") {
          throw new EngineError("NOT_DISCUSSING", "Only a discussion round can be skipped");
        }
        const seat = requireActor(state, event.participantId);
        if (variables.discussed.includes(seat)) {
          throw new EngineError("ALREADY_DISCUSSED", "That seat has already spoken this round");
        }
        return advanceDiscussion(state, [...variables.discussed, seat]);
      }

      case "describePhaseEnded": {
        return {
          state: {
            ...state,
            stepId: "discuss",
            waiting: waitingFor("discuss", variables.alive),
            variables: { ...state.variables, phase: "discuss", discussRound: 1, discussed: [] },
          },
          events: [],
        };
      }

      case "discussRoundEnded": {
        // Derived from the row, not from the state, so re-applying it cannot count a round twice.
        const round = Number(event.payload["round"] ?? variables.discussRound);
        return {
          state: {
            ...state,
            waiting: waitingFor("discuss", variables.alive),
            variables: { ...state.variables, discussRound: round + 1, discussed: [] },
          },
          events: [],
        };
      }

      case "discussionEnded": {
        return {
          state: {
            ...state,
            stepId: "vote",
            waiting: waitingFor("vote", variables.alive),
            variables: { ...state.variables, phase: "vote", votes: {} },
          },
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
        if (variables.revoteTargets.length > 0 && !variables.revoteTargets.includes(target)) {
          throw new EngineError("NOT_ON_BALLOT", "A revote may only pick a seat that tied");
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
  const stats = countVotes(variables);

  // A tie gets one revote, restricted to the seats that tied. A second tie lets the round go by:
  // the table has said what it thinks, and repeating it forever is not a rule.
  if (tied && top !== undefined && !variables.revoted) {
    const targets = ranked.filter(([, count]) => count === top[1]).map(([seat]) => seat);
    return {
      state: {
        ...state,
        stepId: "vote",
        waiting: waitingFor("vote", variables.alive),
        variables: {
          ...state.variables,
          phase: "vote",
          votes: {},
          revoted: true,
          revoteTargets: targets,
          stats,
          // The table has to see why it is voting again, and over whom.
          summary: {
            round: variables.round,
            tally,
            eliminated: null,
            tie: true,
            revote: false,
          },
        },
      },
      events: [derived(state, "revoteStarted", { round: variables.round, targets, tally })],
    };
  }

  const eliminated = top === undefined || tied ? null : top[0];

  const alive =
    eliminated === null ? variables.alive : variables.alive.filter((seat) => seat !== eliminated);
  const undercoverAlive = state.participants.some(
    (seat) => seat.roleId === "undercover" && alive.includes(seat.participantId),
  );
  const summary = {
    round: variables.round,
    tally,
    eliminated,
    tie: tied,
    revote: variables.revoted,
  };

  // Whitespace for the reader: the winner is decided by who is left, not by who was voted out.
  const winner = !undercoverAlive ? "civilian" : alive.length <= 2 ? "undercover" : null;

  if (winner !== null) {
    return {
      state: {
        ...state,
        status: "completed",
        stepId: "over",
        waiting: null,
        participants: withStatus(state.participants, eliminated),
        variables: {
          ...state.variables,
          phase: "over",
          alive,
          votes: {},
          stats,
          summary,
          winner,
          scores: buildScores(state, stats, winner),
        },
      },
      events: [],
    };
  }

  return {
    state: {
      ...state,
      participants: withStatus(state.participants, eliminated),
      stepId: "describe",
      waiting: describeWaiting(alive, []),
      variables: {
        ...state.variables,
        phase: "describe",
        round: variables.round + 1,
        discussRound: 1,
        alive,
        spoken: [],
        discussed: [],
        votes: {},
        revoted: false,
        revoteTargets: [],
        stats,
        summary,
        winner: null,
      },
    },
    events: [],
  };
}

/** Tally and rounds survived are facts about the round, so it is the round's job to add them up. */
function countVotes(variables: UndercoverVariables): UndercoverVariables["stats"] {
  const stats: UndercoverVariables["stats"] = { ...variables.stats };
  for (const target of Object.values(variables.votes)) {
    const current = stats[target] ?? { spoke: 0, votesAgainst: 0, survivedRounds: 0 };
    stats[target] = { ...current, votesAgainst: current.votesAgainst + 1 };
  }
  for (const seat of variables.alive) {
    const current = stats[seat] ?? { spoke: 0, votesAgainst: 0, survivedRounds: 0 };
    stats[seat] = { ...current, survivedRounds: current.survivedRounds + 1 };
  }
  return stats;
}

/** The report a finished match publishes: what each seat did, and whether it was on the winning side. */
function buildScores(
  state: GameState,
  stats: UndercoverVariables["stats"],
  winner: string,
): NonNullable<UndercoverVariables["scores"]> {
  return state.participants.map((seat) => {
    const own = stats[seat.participantId] ?? { spoke: 0, votesAgainst: 0, survivedRounds: 0 };
    const undercover = seat.roleId === "undercover";
    // Field order is the column order: the reader scans seat by seat, verdict last.
    return {
      seat: seat.participantId,
      role: seat.roleId ?? "civilian",
      spoke: own.spoke,
      votesAgainst: own.votesAgainst,
      survivedRounds: own.survivedRounds,
      won: winner === "undercover" ? undercover : !undercover,
    };
  });
}

/**
 * One discussion round ends when every seat still in the round has been handled — speaking and
 * skipping count the same, and seats already out of the round are not waited for at all. The last
 * round hands the table to the vote: the rules, not the players, decide when talking stops.
 */
function advanceDiscussion(state: GameState, discussed: string[]): TransitionResult {
  const variables = variablesOf(state);
  const pending = variables.alive.filter((seat) => !discussed.includes(seat));
  if (pending.length > 0) {
    return {
      state: {
        ...state,
        variables: { ...state.variables, discussed },
        waiting: waitingFor("discuss", pending),
      },
      events: [],
    };
  }

  if (variables.discussRound < DISCUSSION_ROUNDS) {
    return {
      state: {
        ...state,
        waiting: waitingFor("discuss", variables.alive),
        variables: {
          ...state.variables,
          discussed: [],
          discussRound: variables.discussRound + 1,
        },
      },
      events: [derived(state, "discussRoundEnded", { round: variables.discussRound })],
    };
  }

  return {
    state: {
      ...state,
      stepId: "vote",
      waiting: waitingFor("vote", variables.alive),
      variables: { ...state.variables, phase: "vote", discussed, votes: {} },
    },
    events: [derived(state, "discussionEnded", { rounds: DISCUSSION_ROUNDS })],
  };
}
