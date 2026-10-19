import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { dealPersonas, publicPersona, readPersona } from "./persona.js";

/** The same hash the games use to deal roles, so the correlation test matches reality. */
function hash(input: string): number {
  let value = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    value ^= input.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return Math.abs(value);
}

describe("seat personas", () => {
  it("deals deterministically from the match seed", () => {
    const first = dealPersonas("seed-a", 4);
    assert.deepEqual(dealPersonas("seed-a", 4), first);
    assert.notDeepEqual(dealPersonas("seed-b", 4), first);
    assert.equal(first.length, 4);
  });

  it("combines the five dimensions instead of drawing ready-made characters", () => {
    // 24 fixed personas could never fill 200 seats with distinct people; five independent pools can.
    const dealt = dealPersonas("wide", 200);
    assert.equal(dealt.length, 200);
    const distinct = new Set(
      dealt.map((persona) =>
        [persona.mbti, persona.gender, persona.profession, persona.personality, persona.style].join(
          "|",
        ),
      ),
    );
    assert.ok(distinct.size > 150, `expected a wide spread, saw ${distinct.size} distinct people`);

    // The dimensions must not travel together: one MBTI has to arrive with several professions.
    const byMbti = new Map<string, Set<string>>();
    for (const persona of dealt) {
      const professions = byMbti.get(persona.mbti) ?? new Set<string>();
      professions.add(persona.profession);
      byMbti.set(persona.mbti, professions);
    }
    for (const [mbti, professions] of byMbti) {
      assert.ok(professions.size > 1, `${mbti} only ever came with ${[...professions].join(",")}`);
    }
  });

  it("does not correlate with the seat the game makes the undercover", () => {
    // The point of publishing personas is flavour; if dealing looked at roles it would become a
    // shortcut to guessing them. Over 120 seeds the undercover seat must draw many different people.
    const seen = new Set<string>();
    const seats = 4;
    for (let index = 0; index < 120; index += 1) {
      const seed = `correlation-${index}`;
      const undercover = hash(`${seed}#u`) % seats;
      const persona = dealPersonas(seed, seats)[undercover];
      if (persona) seen.add(persona.mbti + persona.profession);
    }
    assert.ok(seen.size > 12, `expected a spread of personas, saw ${seen.size}`);
  });

  it("publishes the gender tag and nothing else", () => {
    const [persona] = dealPersonas("seed-a", 1);
    assert.ok(persona);
    // A persona is how its seat talks; the table gets one word, so nothing can leak from it.
    assert.deepEqual(publicPersona(persona), { gender: persona.gender });
    assert.equal(publicPersona(null), null);
  });

  it("degrades to no persona when the stored one is broken", () => {
    assert.equal(readPersona(null), null);
    assert.equal(readPersona({ gender: "女" }), null);
    assert.equal(readPersona({ ...dealPersonas("seed-a", 1)[0], mbti: "" }), null);
    const [persona] = dealPersonas("seed-a", 1);
    assert.deepEqual(readPersona(persona), persona);
  });
});
