-- One worker owns a match's current AI turn. Without a claim, two workers both read the same
-- waiting seat and both pay for a model call; the loser's write is rejected, but the tokens are gone.
alter table game_instances
  add column ai_claim_until timestamptz,
  add column ai_claim_worker text;
