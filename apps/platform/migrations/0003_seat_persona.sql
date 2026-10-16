-- A seat's persona is platform flavour, not game state: it shapes how an AI seat speaks and gives
-- human seats a character to play. It never changes inside a match, so it lives with the seat.
alter table game_participants add column persona jsonb;

-- Whether the rest of the table may see the other seats' personas. MBTI stays private and gender
-- stays public whatever this says; the projection enforces that, not the column.
alter table game_instances add column persona_public boolean not null default false;
