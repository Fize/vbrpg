import type { ExternalCommand, GameEvent, GameState } from "@vbrpg/contracts";
import type { TransitionResult } from "./errors.js";

/** A game supplies this: a pure function that never touches the network, the clock or the database. */
export type TransitionFn = (state: GameState, event: GameEvent) => TransitionResult;

export interface ReplayResult {
  state: GameState;
  commands: ExternalCommand[];
}

export function replayEvents(
  transition: TransitionFn,
  initialState: GameState,
  events: readonly GameEvent[],
): ReplayResult {
  let state = initialState;
  const commands: ExternalCommand[] = [];
  for (const event of events) {
    const result = transition(state, event);
    state = result.state;
    commands.push(...result.commands);
  }
  return { state, commands };
}
