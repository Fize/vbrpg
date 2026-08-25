import type { GameDefinition, GameEvent, GameState, ExternalCommand } from "@vbrpg/contracts";
import { transition } from "./native-runtime.js";

export interface ReplayResult {
  state: GameState;
  commands: ExternalCommand[];
}

export function replayEvents(
  definition: GameDefinition,
  initialState: GameState,
  events: readonly GameEvent[],
): ReplayResult {
  let state = initialState;
  const commands: ExternalCommand[] = [];
  for (const event of events) {
    const result = transition(definition, state, event);
    state = result.state;
    commands.push(...result.commands);
  }
  return { state, commands };
}
