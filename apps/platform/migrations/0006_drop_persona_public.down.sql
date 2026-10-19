alter table game_instances add column if not exists persona_public boolean not null default false;
alter table rooms add column if not exists persona_public boolean not null default false;
