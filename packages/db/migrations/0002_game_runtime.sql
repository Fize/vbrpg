create table games (
  id text primary key,
  tenant_id text not null references tenants(id) on delete cascade,
  slug text not null,
  code text not null,
  name text not null,
  description text not null default '',
  owner_user_id text not null,
  visibility text not null default 'private' check (visibility in ('private', 'tenant', 'public')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  unique (tenant_id, id),
  unique (tenant_id, slug),
  unique (tenant_id, code),
  foreign key (tenant_id, owner_user_id) references tenant_memberships(tenant_id, user_id)
);

create table game_versions (
  id text primary key,
  tenant_id text not null,
  game_id text not null,
  version text not null,
  status text not null default 'draft' check (status in ('draft', 'testing', 'published', 'withdrawn')),
  dsl_version text not null,
  engine_version text not null,
  content_hash text,
  created_by text not null,
  created_at timestamptz not null default now(),
  published_at timestamptz,
  unique (tenant_id, id),
  unique (tenant_id, game_id, version),
  foreign key (tenant_id, game_id) references games(tenant_id, id),
  foreign key (tenant_id, created_by) references tenant_memberships(tenant_id, user_id)
);

create table workflow_definitions (
  id text primary key,
  tenant_id text not null,
  game_version_id text not null,
  schema_version text not null,
  definition_json jsonb not null,
  compiled_artifact_hash text,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, game_version_id),
  foreign key (tenant_id, game_version_id) references game_versions(tenant_id, id) on delete cascade
);

create table game_instances (
  id text primary key,
  tenant_id text not null,
  game_version_id text not null,
  status text not null default 'created' check (status in ('created', 'running', 'waiting', 'paused', 'completed', 'cancelled')),
  current_sequence integer not null default 0 check (current_sequence >= 0),
  state_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (tenant_id, id),
  foreign key (tenant_id, game_version_id) references game_versions(tenant_id, id)
);

create table game_participants (
  id text primary key,
  tenant_id text not null,
  instance_id text not null,
  actor_user_id text,
  participant_key text not null,
  role_id text,
  control text not null check (control in ('human', 'ai')),
  status text not null check (status in ('active', 'eliminated', 'disconnected', 'finished')),
  seat integer,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, instance_id, participant_key),
  unique (tenant_id, instance_id, seat),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete cascade,
  foreign key (tenant_id, actor_user_id) references tenant_memberships(tenant_id, user_id)
);

create table game_events (
  id text primary key,
  tenant_id text not null,
  instance_id text not null,
  sequence integer not null check (sequence > 0),
  type text not null,
  actor_user_id text,
  idempotency_key text not null,
  occurred_at timestamptz not null default now(),
  payload jsonb not null,
  unique (tenant_id, id),
  unique (tenant_id, instance_id, sequence),
  unique (tenant_id, instance_id, idempotency_key),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete cascade,
  foreign key (tenant_id, actor_user_id) references tenant_memberships(tenant_id, user_id)
);

create table game_snapshots (
  id text primary key,
  tenant_id text not null,
  instance_id text not null,
  sequence integer not null check (sequence >= 0),
  state_json jsonb not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, instance_id, sequence),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete cascade
);

create table player_actions (
  id text primary key,
  tenant_id text not null,
  instance_id text not null,
  actor_user_id text not null,
  idempotency_key text not null,
  status text not null default 'received' check (status in ('received', 'accepted', 'rejected', 'failed')),
  payload jsonb not null,
  result_json jsonb,
  error_code text,
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  unique (tenant_id, id),
  unique (tenant_id, instance_id, idempotency_key),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete cascade,
  foreign key (tenant_id, actor_user_id) references tenant_memberships(tenant_id, user_id)
);

create table pending_commands (
  id text primary key,
  tenant_id text not null,
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
  unique (tenant_id, id),
  unique (tenant_id, instance_id, command_id),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete cascade
);

create table scheduled_jobs (
  id text primary key,
  tenant_id text not null,
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
  unique (tenant_id, id),
  unique (tenant_id, job_key),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete cascade
);

create table outbox_events (
  id text primary key,
  tenant_id text not null,
  aggregate_type text not null,
  aggregate_id text not null,
  event_type text not null,
  status text not null default 'pending' check (status in ('pending', 'leased', 'published', 'failed', 'dead')),
  payload jsonb not null,
  available_at timestamptz not null default now(),
  published_at timestamptz,
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 10 check (max_attempts > 0),
  lease_until timestamptz,
  leased_by text,
  last_error text,
  created_at timestamptz not null default now(),
  unique (tenant_id, id)
);

create table tenant_secrets (
  id text primary key,
  tenant_id text not null references tenants(id) on delete cascade,
  key_name text not null,
  encrypted_value bytea not null,
  key_version integer not null default 1 check (key_version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, key_name)
);

create table ai_usage_ledger (
  id text primary key,
  tenant_id text not null,
  instance_id text,
  actor_user_id text,
  provider text not null,
  model text not null,
  input_tokens integer not null default 0 check (input_tokens >= 0),
  output_tokens integer not null default 0 check (output_tokens >= 0),
  cost_minor_units bigint not null default 0 check (cost_minor_units >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, instance_id) references game_instances(tenant_id, id) on delete set null,
  foreign key (tenant_id, actor_user_id) references tenant_memberships(tenant_id, user_id)
);

create table audit_logs (
  id text primary key,
  tenant_id text not null references tenants(id) on delete cascade,
  actor_user_id text,
  action text not null,
  resource_type text not null,
  resource_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, actor_user_id) references tenant_memberships(tenant_id, user_id)
);

create index games_tenant_status_idx on games (tenant_id, archived_at);
create index game_versions_tenant_status_idx on game_versions (tenant_id, status);
create index game_instances_tenant_status_idx on game_instances (tenant_id, status, updated_at);
create index game_events_instance_sequence_idx on game_events (tenant_id, instance_id, sequence);
create index pending_commands_claim_idx on pending_commands (status, available_at, lease_until);
create index scheduled_jobs_claim_idx on scheduled_jobs (status, run_at, lease_until);
create index outbox_events_claim_idx on outbox_events (published_at, available_at, lease_until);
create index audit_logs_tenant_created_idx on audit_logs (tenant_id, created_at);
