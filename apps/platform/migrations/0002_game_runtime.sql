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
  unique (instance_id, id),
  unique (instance_id, participant_key),
  unique (instance_id, seat),
  foreign key (instance_id) references game_instances (id) on delete cascade
);

-- The match record: what happened, in one total order per match. Rows are what a viewer reads;
-- they are not the input to rebuilding state (`game_instances.state_json` is the current state).
create table game_events (
  id text primary key,
  instance_id text not null,
  -- Ordering is by sequence only; wall-clock time is display and timeout input, never a sort key.
  sequence integer not null check (sequence > 0),
  type text not null,
  -- The seat this row belongs to, and the human behind it when there is one.
  participant_id text,
  actor_user_id text references users (id),
  -- The game's own step label at append time, copied from state by the platform.
  step_id text,
  idempotency_key text not null,
  occurred_at timestamptz not null default now(),
  payload jsonb not null,
  -- Model calls carry usage; every other row leaves all five empty.
  provider_id text,
  model_id text,
  prompt_tokens integer check (prompt_tokens is null or prompt_tokens >= 0),
  completion_tokens integer check (completion_tokens is null or completion_tokens >= 0),
  total_tokens integer check (total_tokens is null or total_tokens >= 0),
  constraint game_events_usage_all_or_nothing check (
    num_nonnulls(provider_id, model_id, prompt_tokens, completion_tokens, total_tokens) in (0, 5)
  ),
  unique (instance_id, sequence),
  unique (instance_id, idempotency_key),
  foreign key (instance_id) references game_instances (id) on delete cascade,
  foreign key (instance_id, participant_id) references game_participants (instance_id, id)
);

create index game_instances_status_updated_idx on game_instances (status, updated_at);
-- Ordering by (instance_id, sequence) is already served by the unique constraint; no second index.
-- One seat's own history, in order: what an AI seat's next prompt is built from.
create index game_events_instance_participant_idx on game_events (instance_id, participant_id, sequence);
