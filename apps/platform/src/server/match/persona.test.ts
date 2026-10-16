import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { PERSONA_BANK, dealPersonas, readPersona, visiblePersona } from "./persona.js";

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

  it("wraps instead of failing when a match has more seats than the bank", () => {
    const dealt = dealPersonas("seed-a", PERSONA_BANK.length + 3);
    assert.equal(dealt.length, PERSONA_BANK.length + 3);
    assert.deepEqual(dealt.slice(PERSONA_BANK.length), dealPersonas("seed-a", 3));
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

  it("shows a seat its own persona and hides MBTI from everyone else", () => {
    const [persona] = dealPersonas("seed-a", 1);
    assert.ok(persona);
    const own = visiblePersona(persona, { own: true, published: false });
    assert.deepEqual(own, { ...persona });

    const otherPublished = visiblePersona(persona, { own: false, published: true });
    assert.equal(otherPublished?.gender, persona.gender);
    assert.equal(otherPublished?.profession, persona.profession);
    assert.equal(otherPublished?.mbti, undefined);

    const otherHidden = visiblePersona(persona, { own: false, published: false });
    assert.deepEqual(otherHidden, { gender: persona.gender });
    assert.equal(visiblePersona(null, { own: true, published: true }), null);
  });

  it("degrades to no persona when the stored one is broken", () => {
    assert.equal(readPersona(null), null);
    assert.equal(readPersona({ gender: "女" }), null);
    assert.equal(readPersona({ ...dealPersonas("seed-a", 1)[0], mbti: "" }), null);
    const [persona] = dealPersonas("seed-a", 1);
    assert.deepEqual(readPersona(persona), persona);
  });
});
