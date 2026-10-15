import type { GameEvent, GameState } from "../../shared/index.js";
import type { TransitionResult } from "./errors.js";

/** A game supplies this: a pure function that never touches the network, the clock or the database. */
export type TransitionFn = (state: GameState, event: GameEvent) => TransitionResult;

export interface ReplayResult {
  state: GameState;
}

export function replayEvents(
  transition: TransitionFn,
  initialState: GameState,
  events: readonly GameEvent[],
): ReplayResult {
  let state = initialState;
  for (const event of events) {
    state = transition(state, event).state;
  }
  return { state };
}
