import type { Generated } from "kysely";

export type JsonObject = Record<string, unknown>;
export type PlatformRole = "admin" | "user";
export type ProviderType = "openai_compatible";

export interface UsersTable {
  id: string;
  username: string;
  password_hash: string | null;
  platform_role: Generated<PlatformRole>;
  is_active: Generated<boolean>;
  must_change_password: Generated<boolean>;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
}

export interface AuthSessionsTable {
  id: string;
  user_id: string;
  token_hash: Buffer | null;
  csrf_token_hash: Buffer | null;
  created_at: Generated<Date>;
  expires_at: Date;
  absolute_expires_at: Date;
  last_seen_at: Generated<Date>;
  revoked_at: Date | null;
}

export interface ProvidersTable {
  id: string;
  name: string;
  provider_type: Generated<ProviderType>;
  base_url: string;
  enabled: Generated<boolean>;
  credential_ciphertext: Buffer;
  credential_nonce: Buffer;
  credential_tag: Buffer;
  credential_key_version: number;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
}

export interface ProviderModelsTable {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  enabled: Generated<boolean>;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
}

export interface GameInstancesTable {
  id: string;
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
  instance_id: string;
  sequence: number;
  type: string;
  participant_id: string | null;
  actor_user_id: string | null;
  step_id: string | null;
  idempotency_key: string;
  occurred_at: Generated<Date>;
  payload: JsonObject;
  provider_id: string | null;
  model_id: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface AuditLogsTable {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  metadata: JsonObject;
  created_at: Generated<Date>;
}

export interface Database {
  users: UsersTable;
  auth_sessions: AuthSessionsTable;
  providers: ProvidersTable;
  provider_models: ProviderModelsTable;
  game_instances: GameInstancesTable;
  game_participants: GameParticipantsTable;
  game_events: GameEventsTable;
  audit_logs: AuditLogsTable;
}
