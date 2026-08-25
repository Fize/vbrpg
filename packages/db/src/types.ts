import type { Generated } from "kysely";

export type JsonObject = Record<string, unknown>;
export type TenantRole = "owner" | "admin" | "developer" | "player";
export type TenantStatus = "active" | "suspended" | "archived";

export interface TenantsTable {
  id: string;
  slug: string;
  name: string;
  status: TenantStatus;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
}

export interface UsersTable {
  id: string;
  username: string;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
}

export interface TenantMembershipsTable {
  tenant_id: string;
  user_id: string;
  role: TenantRole;
  created_at: Generated<Date>;
}

export interface AuthSessionsTable {
  id: string;
  tenant_id: string;
  user_id: string;
  refresh_token_hash: Buffer | null;
  created_at: Generated<Date>;
  expires_at: Date;
  last_seen_at: Generated<Date>;
  revoked_at: Date | null;
}

export interface GamesTable {
  id: string;
  tenant_id: string;
  slug: string;
  code: string;
  name: string;
  description: string;
  owner_user_id: string;
  visibility: "private" | "tenant" | "public";
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
  archived_at: Date | null;
}

export interface GameVersionsTable {
  id: string;
  tenant_id: string;
  game_id: string;
  version: string;
  status: "draft" | "testing" | "published" | "withdrawn";
  dsl_version: string;
  engine_version: string;
  content_hash: string | null;
  created_by: string;
  created_at: Generated<Date>;
  published_at: Date | null;
}

export interface WorkflowDefinitionsTable {
  id: string;
  tenant_id: string;
  game_version_id: string;
  schema_version: string;
  definition_json: JsonObject;
  compiled_artifact_hash: string | null;
  created_at: Generated<Date>;
}

export interface GameInstancesTable {
  id: string;
  tenant_id: string;
  game_version_id: string;
  status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled";
  current_sequence: number;
  state_json: JsonObject;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
  completed_at: Date | null;
}

export interface GameParticipantsTable {
  id: string;
  tenant_id: string;
  instance_id: string;
  actor_user_id: string | null;
  participant_key: string;
  role_id: string | null;
  control: "human" | "ai";
  status: "active" | "eliminated" | "disconnected" | "finished";
  seat: number | null;
  created_at: Generated<Date>;
}

export interface GameEventsTable {
  id: string;
  tenant_id: string;
  instance_id: string;
  sequence: number;
  type: string;
  actor_user_id: string | null;
  idempotency_key: string;
  occurred_at: Generated<Date>;
  payload: JsonObject;
}

export interface GameSnapshotsTable {
  id: string;
  tenant_id: string;
  instance_id: string;
  sequence: number;
  state_json: JsonObject;
  created_at: Generated<Date>;
}

export interface PlayerActionsTable {
  id: string;
  tenant_id: string;
  instance_id: string;
  actor_user_id: string;
  idempotency_key: string;
  status: "received" | "accepted" | "rejected" | "failed";
  payload: JsonObject;
  result_json: JsonObject | null;
  error_code: string | null;
  created_at: Generated<Date>;
  processed_at: Date | null;
}

export interface PendingCommandsTable {
  id: string;
  tenant_id: string;
  instance_id: string;
  command_id: string;
  command_type: string;
  status: Generated<"pending" | "leased" | "completed" | "failed" | "dead">;
  payload: JsonObject;
  attempts: Generated<number>;
  max_attempts: Generated<number>;
  available_at: Generated<Date>;
  lease_until: Date | null;
  leased_by: string | null;
  last_error: string | null;
  created_at: Generated<Date>;
  completed_at: Date | null;
}

export interface ScheduledJobsTable {
  id: string;
  tenant_id: string;
  instance_id: string | null;
  job_key: string;
  job_type: string;
  status: Generated<"scheduled" | "leased" | "completed" | "cancelled" | "dead">;
  payload: JsonObject;
  run_at: Date;
  attempts: Generated<number>;
  max_attempts: Generated<number>;
  lease_until: Date | null;
  leased_by: string | null;
  last_error: string | null;
  created_at: Generated<Date>;
  completed_at: Date | null;
}

export interface OutboxEventsTable {
  id: string;
  tenant_id: string;
  aggregate_type: string;
  aggregate_id: string;
  event_type: string;
  status: Generated<"pending" | "leased" | "published" | "failed" | "dead">;
  payload: JsonObject;
  available_at: Generated<Date>;
  published_at: Date | null;
  attempts: Generated<number>;
  max_attempts: Generated<number>;
  lease_until: Date | null;
  leased_by: string | null;
  last_error: string | null;
  created_at: Generated<Date>;
}

export interface TenantSecretsTable {
  id: string;
  tenant_id: string;
  key_name: string;
  encrypted_value: Buffer;
  key_version: number;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
}

export interface AiUsageLedgerTable {
  id: string;
  tenant_id: string;
  instance_id: string | null;
  actor_user_id: string | null;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_minor_units: string;
  metadata: JsonObject;
  created_at: Generated<Date>;
}

export interface AuditLogsTable {
  id: string;
  tenant_id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  metadata: JsonObject;
  created_at: Generated<Date>;
}

export interface Database {
  tenants: TenantsTable;
  users: UsersTable;
  tenant_memberships: TenantMembershipsTable;
  auth_sessions: AuthSessionsTable;
  games: GamesTable;
  game_versions: GameVersionsTable;
  workflow_definitions: WorkflowDefinitionsTable;
  game_instances: GameInstancesTable;
  game_participants: GameParticipantsTable;
  game_events: GameEventsTable;
  game_snapshots: GameSnapshotsTable;
  player_actions: PlayerActionsTable;
  pending_commands: PendingCommandsTable;
  scheduled_jobs: ScheduledJobsTable;
  outbox_events: OutboxEventsTable;
  tenant_secrets: TenantSecretsTable;
  ai_usage_ledger: AiUsageLedgerTable;
  audit_logs: AuditLogsTable;
}
