import type { ColumnType, Generated } from "kysely";
import type { RoomSeatPlanEntry } from "../../shared/index.js";

export type JsonObject = Record<string, unknown>;
export type PlatformRole = "admin" | "user";
export type ProviderType = "openai_compatible";

export interface UsersTable {
  id: string;
  username: string;
  password_hash: string | null;
  platform_role: Generated<PlatformRole>;
  is_active: Generated<boolean>;
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

export interface RoomsTable {
  id: string;
  game_id: string;
  game_version: string;
  owner_user_id: string;
  /** Six characters, unique, meant to be read aloud. */
  code: string;
  status: "open" | "closed" | "cancelled";
  /**
   * `[{key, control}]`: humans take their seats, AI seats are placeholders until a match starts.
   * Written as a JSON string because the driver turns a bare array into a Postgres array literal,
   * which a jsonb column refuses.
   */
  seat_plan: ColumnType<RoomSeatPlanEntry[], string, string>;
  persona_public: Generated<boolean>;
  variables: JsonObject;
  current_instance_id: string | null;
  created_at: Generated<Date>;
  updated_at: Generated<Date>;
  closed_at: Date | null;
}

export interface RoomMembersTable {
  id: string;
  room_id: string;
  user_id: string;
  seat_key: string;
  seat: number;
  ready: Generated<boolean>;
  created_at: Generated<Date>;
}

export interface GameInstancesTable {
  id: string;
  game_id: string;
  game_version: string;
  status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled";
  current_sequence: number;
  state_json: JsonObject;
  /** The table this match was played at; null for matches created outside a room. */
  room_id: string | null;
  /** Whether the table may see each other's personas. Gender and MBTI ignore it. */
  persona_public: Generated<boolean>;
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
  /** Platform flavour dealt at creation; never changes inside a match. */
  persona: JsonObject | null;
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
  rooms: RoomsTable;
  room_members: RoomMembersTable;
  game_instances: GameInstancesTable;
  game_participants: GameParticipantsTable;
  game_events: GameEventsTable;
  audit_logs: AuditLogsTable;
}
