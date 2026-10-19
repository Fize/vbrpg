-- A persona stopped being the table's shared flavour: only AI seats hold one, each reads only its
-- own, and everyone else sees a gender tag. Nothing is left for a match to publish.
alter table rooms drop column if exists persona_public;
alter table game_instances drop column if exists persona_public;
