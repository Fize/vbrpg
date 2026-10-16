-- A room is the table, not the round: it exists before any match, decides which game is played, and
-- can host several matches over time. Whether one is running right now is derived from the current
-- instance's status, so the room row never carries a second copy of that truth.
create table rooms (
  id text primary key,
  game_id text not null,
  game_version text not null,
  owner_user_id text not null references users (id),
  status text not null default 'open' check (status in ('open', 'closed', 'cancelled')),
  -- [{key, control}]: which seats exist and which of them are AI placeholders. Editable while no
  -- match is running; the seat count is bounded by the game's own minSeats/maxSeats.
  seat_plan jsonb not null,
  persona_public boolean not null default false,
  variables jsonb not null default '{}'::jsonb,
  current_instance_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  closed_at timestamptz
);

-- Humans take seats here. AI placeholders have no row: they come into existence only when a match
-- starts, so a waiting room costs nothing and deals nobody.
create table room_members (
  id text primary key,
  room_id text not null,
  user_id text not null references users (id),
  seat_key text not null,
  seat integer not null,
  ready boolean not null default false,
  created_at timestamptz not null default now(),
  unique (room_id, user_id),
  unique (room_id, seat_key),
  foreign key (room_id) references rooms (id) on delete cascade
);

-- Every match remembers its table, so a room's history is one query and nothing has to be stored twice.
alter table game_instances add column room_id text references rooms (id);
create index game_instances_room_idx on game_instances (room_id, created_at desc);

alter table rooms
  add constraint rooms_current_instance_fk
  foreign key (current_instance_id) references game_instances (id);

create index rooms_status_updated_idx on rooms (status, updated_at);
