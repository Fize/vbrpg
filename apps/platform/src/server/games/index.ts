import { createGameRegistry, type GameModule } from "../game/index.js";
import { undercover } from "./undercover.js";

/** Every game the platform ships. The registry refuses duplicate ids at startup. */
export const builtInGames: readonly GameModule[] = [undercover];

export function createBuiltInRegistry() {
  return createGameRegistry(builtInGames);
}

export { undercover };
