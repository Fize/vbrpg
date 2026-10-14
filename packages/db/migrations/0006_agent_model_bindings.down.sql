-- Rollback for 0006. Bindings carry no credentials, so they can be dropped
-- directly; a running instance that still waits on an AI node needs its agents
-- bound again after re-applying 0006.
drop policy if exists tenant_isolation on agent_model_bindings;
alter table agent_model_bindings disable row level security;
drop table if exists agent_model_bindings;
