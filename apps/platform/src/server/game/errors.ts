import type { ExternalCommand, GameEvent, GameState } from "../../shared/index.js";

export interface TransitionResult {
  state: GameState;
  events: GameEvent[];
  commands: ExternalCommand[];
}

export class EngineError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "EngineError";
    this.code = code;
  }
}
