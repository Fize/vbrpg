create table auth_sessions (
  id text primary key,
  tenant_id text not null,
  user_id text not null,
  refresh_token_hash bytea,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  last_seen_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (tenant_id, id),
  foreign key (tenant_id, user_id) references tenant_memberships(tenant_id, user_id) on delete cascade
);

create index auth_sessions_active_idx
  on auth_sessions (tenant_id, user_id, expires_at)
  where revoked_at is null;
