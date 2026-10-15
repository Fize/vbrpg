import type { GameEvent, GameState, Participant } from "../../shared/index.js";
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

export function resolveVisibility(source: VisibilitySource | undefined, state: GameState): Visibility {
  if (source === undefined) return {};
  return typeof source === "function" ? source(state) : source;
}

export interface GameModule {
  readonly id: string;
  readonly version: string;
  readonly engineVersion: string;
  /** Which variables each viewer may see. Absent means nobody sees them (fail-closed). */
  readonly visibility?: VisibilitySource;
  /** Roles, dealt cards and per-game variables are the game's business, so creation is its hook. */
  initialState(input: CreateInstanceInput): GameState;
  transition(state: GameState, event: GameEvent): TransitionResult;
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
