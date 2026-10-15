-- Rollback for 0005. Refuses to run while provider data exists, so an operator
-- must export and delete provider rows first (see docs/operations for the backup step).

do $$
begin
  if exists (select 1 from provider_models) or exists (select 1 from providers) then
    raise exception 'refusing to roll back 0005: provider rows still exist; back up and delete them first';
  end if;
end $$;

drop policy if exists tenant_isolation on provider_models;
alter table provider_models disable row level security;
drop table if exists provider_models;

drop policy if exists tenant_isolation on providers;
alter table providers disable row level security;
drop table if exists providers;

alter table auth_sessions drop column if exists absolute_expires_at;
alter table auth_sessions drop column if exists csrf_token_hash;
alter table auth_sessions drop column if exists token_hash;

alter table users drop constraint if exists users_platform_role_check;
alter table users drop column if exists must_change_password;
alter table users drop column if exists is_active;
alter table users drop column if exists platform_role;
alter table users drop column if exists password_hash;
