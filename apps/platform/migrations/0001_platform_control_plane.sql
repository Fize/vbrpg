-- VBRPG platform baseline: tenant-scoped control-plane tables.
-- This migration is PostgreSQL-only and intentionally does not alter legacy tables.

create table if not exists tenants (
    id text primary key,
    slug text not null,
    name text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint tenants_status_check check (status in ('active', 'suspended', 'archived')),
    constraint tenants_slug_unique unique (slug)
);

create table if not exists users (
    id text primary key,
    username text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint users_username_unique unique (username)
);

create table if not exists tenant_memberships (
    tenant_id text not null references tenants (id) on delete cascade,
    user_id text not null references users (id) on delete cascade,
    role text not null,
    created_at timestamptz not null default now(),
    primary key (tenant_id, user_id),
    constraint tenant_memberships_role_check check (
        role in ('owner', 'admin', 'developer', 'player')
    )
);

create index if not exists tenant_memberships_user_id_idx
    on tenant_memberships (user_id);
