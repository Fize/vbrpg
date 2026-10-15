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

create table game_snapshots (
  id text primary key,
  instance_id text not null,
  sequence integer not null check (sequence >= 0),
  state_json jsonb not null,
  created_at timestamptz not null default now(),
  unique (instance_id, sequence),
  foreign key (instance_id) references game_instances (id) on delete cascade
);

create table pending_commands (
  id text primary key,
  instance_id text not null,
  command_id text not null,
  command_type text not null,
  status text not null default 'pending' check (status in ('pending', 'leased', 'completed', 'failed', 'dead')),
  payload jsonb not null,
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  available_at timestamptz not null default now(),
  lease_until timestamptz,
  leased_by text,
  last_error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (instance_id, command_id),
  foreign key (instance_id) references game_instances (id) on delete cascade
);

create table scheduled_jobs (
  id text primary key,
  -- Nullable: a timer does not have to belong to a match.
  instance_id text,
  job_key text not null,
  job_type text not null,
  status text not null default 'scheduled' check (status in ('scheduled', 'leased', 'completed', 'cancelled', 'dead')),
  payload jsonb not null,
  run_at timestamptz not null,
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  lease_until timestamptz,
  leased_by text,
  last_error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (job_key),
  foreign key (instance_id) references game_instances (id) on delete cascade
);

create index game_instances_status_updated_idx on game_instances (status, updated_at);
create index game_events_instance_sequence_idx on game_events (instance_id, sequence);
create index pending_commands_claim_idx on pending_commands (status, available_at, lease_until);
create index scheduled_jobs_claim_idx on scheduled_jobs (status, run_at, lease_until);
