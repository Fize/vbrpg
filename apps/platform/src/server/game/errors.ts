import type { GameEvent, GameState } from "../../shared/index.js";

export interface TransitionResult {
  state: GameState;
  /**
   * Further events this step produced. The inbound event is appended by the platform and must not
   * be echoed here; anything listed is appended after it, with the next sequence numbers.
   */
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
