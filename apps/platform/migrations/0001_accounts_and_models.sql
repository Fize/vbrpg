-- Platform accounts, opaque browser sessions, the shared provider/model catalog
-- and the administrator audit trail.
-- Design: docs/design/phase1-auth-provider-secure-design.md

create table users (
  id text primary key,
  username text not null,
  password_hash text,
  platform_role text not null default 'user',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint users_username_unique unique (username),
  constraint users_platform_role_check check (platform_role in ('admin', 'user'))
);

create table auth_sessions (
  id text primary key,
  -- Sessions are derived from the account: deleting a user ends its sessions.
  user_id text not null references users (id) on delete cascade,
  -- The cookie carries the opaque token; the database only stores its digest.
  token_hash bytea,
  csrf_token_hash bytea,
  created_at timestamptz not null default now(),
  -- `expires_at` is the idle deadline; `absolute_expires_at` caps total session life.
  expires_at timestamptz not null,
  absolute_expires_at timestamptz not null,
  last_seen_at timestamptz not null default now(),
  revoked_at timestamptz
);

create unique index auth_sessions_token_hash_idx
  on auth_sessions (token_hash)
  where token_hash is not null;

create index auth_sessions_active_idx
  on auth_sessions (user_id, expires_at)
  where revoked_at is null;

create table providers (
  id text primary key,
  name text not null,
  provider_type text not null default 'openai_compatible',
  base_url text not null,
  enabled boolean not null default true,
  credential_ciphertext bytea not null,
  credential_nonce bytea not null,
  credential_tag bytea not null,
  credential_key_version integer not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint providers_type_check check (provider_type = 'openai_compatible'),
  constraint providers_name_unique unique (name),
  constraint providers_credential_key_version_check check (credential_key_version > 0)
);

create table provider_models (
  id text primary key,
  provider_id text not null,
  model_id text not null,
  display_name text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint provider_models_provider_fk foreign key (provider_id)
    references providers (id) on delete restrict,
  constraint provider_models_provider_model_unique unique (provider_id, model_id)
);

create index providers_enabled_idx on providers (enabled);
create index provider_models_enabled_idx on provider_models (enabled);

create table audit_logs (
  id text primary key,
  -- Audit rows outlive the account they name: deleting an account nulls the link instead of
  -- blocking the delete. Match history (game_participants, game_events) still blocks it.
  actor_user_id text references users (id) on delete set null,
  action text not null,
  resource_type text not null,
  resource_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index audit_logs_created_idx on audit_logs (created_at);
