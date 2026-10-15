import type { GameEvent, GameState } from "../../shared/index.js";

export interface TransitionResult {
  state: GameState;
  /** Further events this step produced, appended in order by the platform. */
  events: GameEvent[];
}

export class EngineError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "EngineError";
    this.code = code;
  }
}
