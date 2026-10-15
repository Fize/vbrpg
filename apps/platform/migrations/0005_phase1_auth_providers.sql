-- Phase 1: administrator-provisioned platform accounts, opaque sessions,
-- and the shared provider/model catalog.
-- Design: docs/design/phase1-auth-provider-secure-design.md

alter table users
  add column password_hash text,
  add column platform_role text not null default 'user',
  add column is_active boolean not null default true,
  add column must_change_password boolean not null default true;

alter table users
  add constraint users_platform_role_check check (platform_role in ('admin', 'user'));

-- Phase 1 is a single platform; the tenant row exists so RLS-scoped tables
-- (sessions, providers, provider_models) have a stable owner.
insert into tenants (id, slug, name, status)
values ('platform', 'platform', 'VBRPG Platform', 'active')
on conflict (id) do nothing;

-- `expires_at` is the idle deadline; `absolute_expires_at` caps total session life.
alter table auth_sessions
  add column token_hash bytea,
  add column csrf_token_hash bytea,
  add column absolute_expires_at timestamptz;

update auth_sessions set absolute_expires_at = expires_at where absolute_expires_at is null;

alter table auth_sessions alter column absolute_expires_at set not null;

create unique index auth_sessions_token_hash_idx
  on auth_sessions (token_hash)
  where token_hash is not null;

create table providers (
  id text primary key,
  tenant_id text not null references tenants (id),
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
  constraint providers_tenant_id_id_unique unique (tenant_id, id),
  constraint providers_tenant_name_unique unique (tenant_id, name),
  constraint providers_credential_key_version_check check (credential_key_version > 0)
);

create table provider_models (
  id text primary key,
  tenant_id text not null,
  provider_id text not null,
  model_id text not null,
  display_name text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint provider_models_provider_fk foreign key (tenant_id, provider_id)
    references providers (tenant_id, id) on delete restrict,
  constraint provider_models_tenant_id_id_unique unique (tenant_id, id),
  constraint provider_models_provider_model_unique unique (tenant_id, provider_id, model_id)
);

create index providers_tenant_enabled_idx on providers (tenant_id, enabled);
create index provider_models_tenant_enabled_idx on provider_models (tenant_id, enabled);

alter table providers enable row level security;
create policy tenant_isolation on providers
  using (tenant_id = current_setting('app.tenant_id', true))
  with check (tenant_id = current_setting('app.tenant_id', true));

alter table provider_models enable row level security;
create policy tenant_isolation on provider_models
  using (tenant_id = current_setting('app.tenant_id', true))
  with check (tenant_id = current_setting('app.tenant_id', true));
