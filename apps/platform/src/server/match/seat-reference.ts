import type { GameModule } from "../game/index.js";

/**
 * A seat can be referred to by its name (`s2`) or by its id. Humans type names because that is what
 * they see; a model does too, and asking it to reproduce 36-character ids is a tax on every turn —
 * one the earlier version of this platform paid in failed votes and retries.
 *
 * So the platform resolves the references: every action argument the game declared as `kind: "seat"`
 * is mapped from a seat name to the participant id before the rules see it. Values that are already
 * ids, or that match no seat at all, are passed through untouched — refusing them is the game's job.
 */
export function resolveSeatReferences(input: {
  game: GameModule;
  actionType: string;
  payload: Record<string, unknown>;
  /** Seat name to participant id, for this match. */
  seats: Record<string, string>;
}): Record<string, unknown> {
  const action = (input.game.actions ?? []).find(
    (candidate) => candidate.name === input.actionType,
  );
  const seatArgs = Object.entries(action?.args ?? {})
    .filter(([, arg]) => arg.kind === "seat")
    .map(([name]) => name);
  if (seatArgs.length === 0) return input.payload;

  const resolved = { ...input.payload };
  for (const name of seatArgs) {
    const value = resolved[name];
    if (typeof value !== "string") continue;
    const seatId = input.seats[value];
    if (seatId !== undefined) resolved[name] = seatId;
  }
  return resolved;
}
