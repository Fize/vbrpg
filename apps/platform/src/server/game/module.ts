import type { ActionArg, GameEvent, GameState, Participant } from "../../shared/index.js";
import type { TransitionResult } from "./errors.js";
import type { Visibility } from "./projector.js";

export interface CreateInstanceInput {
  instanceId: string;
  gameVersionId: string;
  engineVersion: string;
  randomSeed: string;
  participants: Participant[];
  variables?: Record<string, unknown>;
}

/**
 * The platform owns this envelope; a game only fills the variables it needs. Everything the
 * platform guarantees — ordering, storage, projection and history — reads it.
 */
export function createBaseState(
  input: CreateInstanceInput,
  variables: Record<string, unknown>,
): GameState {
  return {
    instanceId: input.instanceId,
    gameVersionId: input.gameVersionId,
    engineVersion: input.engineVersion,
    sequence: 0,
    status: "created",
    stepId: "start",
    variables: structuredClone(variables),
    participants: structuredClone(input.participants),
    waiting: null,
    randomSeed: input.randomSeed,
  };
}

/**
 * A game is this interface and nothing else: no definitions, no nodes, no interpreter. The module
 * owns the rules — including who plays what at creation — while the platform owns identity,
 * ordering, storage, projection and delivery of side effects.
 *
 * `transition` must stay pure: no database, no network, no clock, no randomness. Time, randomness
 * and model replies arrive as events; anything the outside world must do leaves as a command.
 */
/**
 * Visibility may depend on the state: a per-seat secret is only addressable once the seats exist,
 * so a game that deals private information computes its rules from `state.participants`.
 */
export type VisibilitySource = Visibility | ((state: GameState) => Visibility);

export function resolveVisibility(
  source: VisibilitySource | undefined,
  state: GameState,
): Visibility {
  if (source === undefined) return {};
  return typeof source === "function" ? source(state) : source;
}

/**
 * One thing a seat can do. The name is the event type it produces and `args` names the payload
 * fields, so a tool call and a human submission are the same thing on the wire.
 */
export interface ActionDefinition {
  readonly name: string;
  /** What the table calls it. */
  readonly label: string;
  readonly description: string;
  /** Argument name to its shape. `kind: "seat"` is the only hint a UI needs; text is the default. */
  readonly args?: Readonly<Record<string, ActionArg>>;
  /**
   * `room` content is part of the shared transcript every seat may read; `seat` content stays
   * with its owner (a secret ballot, a private note).
   */
  readonly audience?: "room" | "seat";
}

/** A creation parameter the game asks for; the platform renders it and passes the value back. */
export interface SetupField {
  readonly name: string;
  readonly label: string;
  readonly description: string;
  readonly kind?: "text" | "category" | "word";
  readonly from?: "pair.civilian" | "pair.undercover";
}

export interface GameModule {
  readonly id: string;
  /** What players call this game. */
  readonly title: string;
  readonly version: string;
  readonly engineVersion: string;
  /** Step id to the name the table reads. Anything absent is shown as the game wrote it. */
  readonly steps?: Readonly<Record<string, string>>;
  /** Every other word the game uses — variables, roles, outcomes, its own event types. */
  readonly words?: Readonly<Record<string, string>>;
  /** What the game needs before it can deal, e.g. the words a round is played with. */
  readonly setup?: readonly SetupField[];
  /** Which variables each viewer may see. Absent means nobody sees them (fail-closed). */
  readonly visibility?: VisibilitySource;
  /** Roles, dealt cards and per-game variables are the game's business, so creation is its hook. */
  /** Everything a seat may ever do. Fixed for the match so the prompt prefix never moves. */
  readonly actions?: readonly ActionDefinition[];
  /** The rules, in the game's own words. Stable for the match; the seat's private state is added by the platform. */
  briefing?(state: GameState, participantId: string): string;
  initialState(input: CreateInstanceInput): GameState;
  transition(state: GameState, event: GameEvent): TransitionResult;
}

/** The catalogue entries the current waiting point allows, in catalogue order. */
export function allowedActions(game: GameModule, state: GameState): ActionDefinition[] {
  const catalogue = game.actions ?? [];
  const allowed = state.waiting?.actions ?? [];
  return catalogue.filter((action) => allowed.includes(action.name));
}

/** Action names whose content belongs to the shared transcript. */
export function roomAudienceActions(game: GameModule): string[] {
  return (game.actions ?? [])
    .filter((action) => (action.audience ?? "room") === "room")
    .map((action) => action.name);
}

/** Games are registered at startup; the registry is the only place that knows their ids. */
export class GameRegistry {
  readonly #modules = new Map<string, GameModule>();

  constructor(modules: readonly GameModule[]) {
    for (const module of modules) {
      if (this.#modules.has(module.id)) {
        throw new Error(`Duplicate game id: ${module.id}`);
      }
      this.#modules.set(module.id, module);
    }
  }

  get(gameId: string): GameModule | undefined {
    return this.#modules.get(gameId);
  }

  require(gameId: string): GameModule {
    const module = this.get(gameId);
    if (!module) {
      throw new Error(`Unknown game: ${gameId}`);
    }
    return module;
  }

  list(): GameModule[] {
    return [...this.#modules.values()];
  }
}

export function createGameRegistry(modules: readonly GameModule[]): GameRegistry {
  return new GameRegistry(modules);
}
