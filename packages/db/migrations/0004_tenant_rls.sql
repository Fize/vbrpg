-- RLS is a defense-in-depth layer. Application queries must still include tenant_id
-- and establish app.tenant_id with SET LOCAL inside the transaction.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'tenant_memberships', 'auth_sessions', 'games', 'game_versions',
    'workflow_definitions', 'game_instances', 'game_participants',
    'game_events', 'game_snapshots', 'player_actions', 'pending_commands',
    'scheduled_jobs', 'outbox_events', 'tenant_secrets', 'ai_usage_ledger',
    'audit_logs'
  ] loop
    execute format('alter table %I enable row level security', table_name);
    execute format(
      'create policy tenant_isolation on %I using (tenant_id = current_setting(''app.tenant_id'', true)) with check (tenant_id = current_setting(''app.tenant_id'', true))',
      table_name
    );
  end loop;
end $$;
