-- One agent inside one game version resolves to exactly one model. The binding
-- lives with the version so a published version keeps the models it shipped with
-- (P4-03), and it is tenant-scoped like every other resource.
create table agent_model_bindings (
  id text primary key,
  tenant_id text not null,
  game_version_id text not null,
  agent_id text not null,
  provider_model_id text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  constraint agent_model_bindings_scope_unique unique (tenant_id, game_version_id, agent_id),
  constraint agent_model_bindings_agent_id_check check (length(agent_id) > 0),
  constraint agent_model_bindings_version_fk foreign key (tenant_id, game_version_id)
    references game_versions (tenant_id, id) on delete cascade,
  -- The provider catalog is platform-owned and shared by every game, so this
  -- reference crosses tenants by design; the binding itself stays tenant-scoped.
  constraint agent_model_bindings_model_fk foreign key (provider_model_id)
    references provider_models (id) on delete restrict
);

create index agent_model_bindings_tenant_version_idx
  on agent_model_bindings (tenant_id, game_version_id);

alter table agent_model_bindings enable row level security;
create policy tenant_isolation on agent_model_bindings
  using (tenant_id = current_setting('app.tenant_id', true))
  with check (tenant_id = current_setting('app.tenant_id', true));
