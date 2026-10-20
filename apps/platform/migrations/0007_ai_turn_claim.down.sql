alter table game_instances
  drop column if exists ai_claim_until,
  drop column if exists ai_claim_worker;
