/**
 * Deterministic picks from a match seed. Three callers need this: the platform deals personas and
 * resolves a coin flip for a supplied word pair, and the games deal their own roles and cards. The
 * salt is what keeps those draws independent — the same seed must never link a persona to a role.
 */
export function hashSeed(input: string): number {
  let value = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    value ^= input.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return Math.abs(value);
}

/** A number in `[0, size)`, stable for the same seed and salt. */
export function seededIndex(seed: string, salt: string, size: number): number {
  return hashSeed(`${seed}#${salt}`) % Math.max(size, 1);
}
