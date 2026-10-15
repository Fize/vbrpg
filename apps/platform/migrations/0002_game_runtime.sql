create table game_instances (
  id text primary key,
  -- The game version is a constant inside the game's own code, not a table row.
  game_version_id text not null,
  status text not null default 'created' check (status in ('created', 'running', 'waiting', 'paused', 'completed', 'cancelled')),
  current_sequence integer not null default 0 check (current_sequence >= 0),
  state_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

create table game_participants (
  id text primary key,
  instance_id text not null,
  -- Humans carry an account; AI seats are unowned.
  actor_user_id text references users (id),
  participant_key text not null,
  role_id text,
  control text not null check (control in ('human', 'ai')),
  status text not null check (status in ('active', 'eliminated', 'disconnected', 'finished')),
  seat integer,
  created_at timestamptz not null default now(),
  unique (instance_id, participant_key),
  unique (instance_id, seat),
  foreign key (instance_id) references game_instances (id) on delete cascade
);

create table game_events (
  id text primary key,
  instance_id text not null,
  -- Ordering is by sequence only: wall-clock time is display and timeout input, never a sort key.
  sequence integer not null check (sequence > 0),
  type text not null,
  actor_user_id text references users (id),
  idempotency_key text not null,
  occurred_at timestamptz not null default now(),
  payload jsonb not null,
  unique (instance_id, sequence),
  unique (instance_id, idempotency_key),
  foreign key (instance_id) references game_instances (id) on delete cascade
);

create index game_instances_status_updated_idx on game_instances (status, updated_at);
create index game_events_instance_sequence_idx on game_events (instance_id, sequence);
