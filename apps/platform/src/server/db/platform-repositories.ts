import { randomUUID } from "node:crypto";
import { sql, type Kysely, type Selectable } from "kysely";
import type {
  AuthSessionsTable,
  Database,
  PlatformRole,
  ProviderModelsTable,
  ProvidersTable,
  UsersTable,
} from "./types.js";
import type { DbExecutor } from "./repositories.js";

export interface PlatformUserRecord {
  id: string;
  username: string;
  passwordHash: string | null;
  role: PlatformRole;
  active: boolean;
  createdAt: Date;
}

type UserRow = Selectable<UsersTable>;

function toPlatformUser(row: UserRow): PlatformUserRecord {
  return {
    id: row.id,
    username: row.username,
    passwordHash: row.password_hash,
    role: row.platform_role,
    active: row.is_active,
    createdAt: row.created_at,
  };
}

export async function findPlatformUserByUsername(
  db: DbExecutor,
  username: string,
): Promise<PlatformUserRecord | undefined> {
  const row = await db
    .selectFrom("users")
    .selectAll()
    .where("username", "=", username)
    .executeTakeFirst();
  return row ? toPlatformUser(row) : undefined;
}

export async function getPlatformUser(
  db: DbExecutor,
  userId: string,
): Promise<PlatformUserRecord | undefined> {
  const row = await db.selectFrom("users").selectAll().where("id", "=", userId).executeTakeFirst();
  return row ? toPlatformUser(row) : undefined;
}

export async function listPlatformUsers(db: DbExecutor): Promise<PlatformUserRecord[]> {
  const rows = await db.selectFrom("users").selectAll().orderBy("created_at", "asc").execute();
  return rows.map(toPlatformUser);
}

export async function createPlatformUser(
  db: DbExecutor,
  input: {
    id: string;
    username: string;
    passwordHash: string;
    role: PlatformRole;
  },
): Promise<PlatformUserRecord> {
  const row = await db
    .insertInto("users")
    .values({
      id: input.id,
      username: input.username,
      password_hash: input.passwordHash,
      platform_role: input.role,
      is_active: true,
    })
    .returningAll()
    .executeTakeFirstOrThrow();
  return toPlatformUser(row);
}

export async function updatePlatformUser(
  db: DbExecutor,
  userId: string,
  patch: {
    role?: PlatformRole;
    active?: boolean;
    passwordHash?: string;
  },
): Promise<PlatformUserRecord | undefined> {
  const row = await db
    .updateTable("users")
    .set({
      ...(patch.role === undefined ? {} : { platform_role: patch.role }),
      ...(patch.active === undefined ? {} : { is_active: patch.active }),
      ...(patch.passwordHash === undefined ? {} : { password_hash: patch.passwordHash }),
      updated_at: new Date(),
    })
    .where("id", "=", userId)
    .returningAll()
    .executeTakeFirst();
  return row ? toPlatformUser(row) : undefined;
}

export async function countActiveAdmins(db: DbExecutor): Promise<number> {
  const row = await db
    .selectFrom("users")
    .select(sql<number>`count(*)::int`.as("total"))
    .where("platform_role", "=", "admin")
    .where("is_active", "=", true)
    .executeTakeFirst();
  return row?.total ?? 0;
}

/**
 * One-time creation of the first administrator. The advisory lock plus the
 * active-admin check make concurrent bootstrap attempts safe; the caller
 * supplies an already-hashed password and never receives it back.
 */
export async function bootstrapPlatformAdmin(
  db: Kysely<Database>,
  input: { username: string; passwordHash: string },
): Promise<{ created: boolean }> {
  return db.transaction().execute(async (transaction) => {
    await sql`select pg_advisory_xact_lock(hashtext('vbrpg_admin_bootstrap'))`.execute(transaction);

    const activeAdmins = await transaction
      .selectFrom("users")
      .select(sql<number>`count(*)::int`.as("total"))
      .where("platform_role", "=", "admin")
      .where("is_active", "=", true)
      .executeTakeFirst();
    if ((activeAdmins?.total ?? 0) > 0) return { created: false };

    const userId = randomUUID();
    await transaction
      .insertInto("users")
      .values({
        id: userId,
        username: input.username,
        password_hash: input.passwordHash,
        platform_role: "admin",
        is_active: true,
      })
      .execute();
    await transaction
      .insertInto("audit_logs")
      .values({
        id: randomUUID(),
        actor_user_id: userId,
        action: "admin.bootstrap",
        resource_type: "user",
        resource_id: userId,
        metadata: { succeeded: true },
      })
      .execute();
    return { created: true };
  });
}

export async function createAuthSession(
  db: DbExecutor,
  input: {
    id: string;
    userId: string;
    tokenHash: Buffer;
    csrfTokenHash: Buffer;
    idleExpiresAt: Date;
    absoluteExpiresAt: Date;
  },
): Promise<void> {
  await db
    .insertInto("auth_sessions")
    .values({
      id: input.id,
      user_id: input.userId,
      token_hash: input.tokenHash,
      csrf_token_hash: input.csrfTokenHash,
      expires_at: input.idleExpiresAt,
      absolute_expires_at: input.absoluteExpiresAt,
    })
    .execute();
}

export async function getAuthSessionByTokenHash(
  db: DbExecutor,
  tokenHash: Buffer,
  now = new Date(),
): Promise<Selectable<AuthSessionsTable> | undefined> {
  return db
    .selectFrom("auth_sessions")
    .selectAll()
    .where("token_hash", "=", tokenHash)
    .where("revoked_at", "is", null)
    .where("expires_at", ">", now)
    .where("absolute_expires_at", ">", now)
    .executeTakeFirst();
}

export async function touchAuthSession(
  db: DbExecutor,
  sessionId: string,
  idleExpiresAt: Date,
  now = new Date(),
): Promise<void> {
  await db
    .updateTable("auth_sessions")
    .set({ last_seen_at: now, expires_at: idleExpiresAt })
    .where("id", "=", sessionId)
    .where("revoked_at", "is", null)
    .execute();
}

export async function setAuthSessionCsrfHash(
  db: DbExecutor,
  sessionId: string,
  csrfTokenHash: Buffer,
): Promise<void> {
  await db
    .updateTable("auth_sessions")
    .set({ csrf_token_hash: csrfTokenHash })
    .where("id", "=", sessionId)
    .execute();
}

export async function revokeAuthSession(
  db: DbExecutor,
  sessionId: string,
  now = new Date(),
): Promise<void> {
  await db
    .updateTable("auth_sessions")
    .set({ revoked_at: now })
    .where("id", "=", sessionId)
    .where("revoked_at", "is", null)
    .execute();
}

export async function revokeUserSessions(
  db: DbExecutor,
  userId: string,
  now = new Date(),
): Promise<void> {
  await db
    .updateTable("auth_sessions")
    .set({ revoked_at: now })
    .where("user_id", "=", userId)
    .where("revoked_at", "is", null)
    .execute();
}

export async function deletePlatformUser(db: DbExecutor, userId: string): Promise<boolean> {
  const result = await db.deleteFrom("users").where("id", "=", userId).executeTakeFirst();
  return Number(result.numDeletedRows ?? 0) > 0;
}

export async function deleteProvider(db: DbExecutor, providerId: string): Promise<boolean> {
  const result = await db.deleteFrom("providers").where("id", "=", providerId).executeTakeFirst();
  return Number(result.numDeletedRows ?? 0) > 0;
}

export async function deleteProviderModel(db: DbExecutor, modelRecordId: string): Promise<boolean> {
  const result = await db
    .deleteFrom("provider_models")
    .where("id", "=", modelRecordId)
    .executeTakeFirst();
  return Number(result.numDeletedRows ?? 0) > 0;
}

export interface ProviderWithModels {
  provider: Selectable<ProvidersTable>;
  models: Selectable<ProviderModelsTable>[];
}

export async function listProvidersWithModels(
  db: DbExecutor,
  options: { includeDisabled?: boolean } = {},
): Promise<ProviderWithModels[]> {
  let query = db.selectFrom("providers").selectAll().orderBy("created_at", "asc");
  if (!options.includeDisabled) {
    query = query.where("enabled", "=", true);
  }
  const providers = await query.execute();
  if (providers.length === 0) return [];

  let modelQuery = db
    .selectFrom("provider_models")
    .selectAll()
    .where(
      "provider_id",
      "in",
      providers.map((provider) => provider.id),
    )
    .orderBy("created_at", "asc");
  if (!options.includeDisabled) {
    modelQuery = modelQuery.where("enabled", "=", true);
  }
  const models = await modelQuery.execute();

  return providers.map((provider) => ({
    provider,
    models: models.filter((model) => model.provider_id === provider.id),
  }));
}

export async function getProvider(
  db: DbExecutor,
  providerId: string,
): Promise<Selectable<ProvidersTable> | undefined> {
  return db.selectFrom("providers").selectAll().where("id", "=", providerId).executeTakeFirst();
}

export interface ProviderCredentialColumns {
  credential_ciphertext: Buffer;
  credential_nonce: Buffer;
  credential_tag: Buffer;
  credential_key_version: number;
}

export async function createProvider(
  db: DbExecutor,
  input: {
    id: string;
    name: string;
    baseUrl: string;
    enabled: boolean;
    credential: ProviderCredentialColumns;
  },
): Promise<Selectable<ProvidersTable>> {
  return db
    .insertInto("providers")
    .values({
      id: input.id,
      name: input.name,
      provider_type: "openai_compatible",
      base_url: input.baseUrl,
      enabled: input.enabled,
      ...input.credential,
    })
    .returningAll()
    .executeTakeFirstOrThrow();
}

export async function updateProvider(
  db: DbExecutor,
  providerId: string,
  patch: {
    name?: string;
    baseUrl?: string;
    enabled?: boolean;
    credential?: ProviderCredentialColumns;
  },
): Promise<Selectable<ProvidersTable> | undefined> {
  return db
    .updateTable("providers")
    .set({
      ...(patch.name === undefined ? {} : { name: patch.name }),
      ...(patch.baseUrl === undefined ? {} : { base_url: patch.baseUrl }),
      ...(patch.enabled === undefined ? {} : { enabled: patch.enabled }),
      ...(patch.credential ?? {}),
      updated_at: new Date(),
    })
    .where("id", "=", providerId)
    .returningAll()
    .executeTakeFirst();
}

export async function createProviderModel(
  db: DbExecutor,
  input: {
    id: string;
    providerId: string;
    modelId: string;
    displayName: string;
    enabled: boolean;
  },
): Promise<Selectable<ProviderModelsTable>> {
  return db
    .insertInto("provider_models")
    .values({
      id: input.id,
      provider_id: input.providerId,
      model_id: input.modelId,
      display_name: input.displayName,
      enabled: input.enabled,
    })
    .returningAll()
    .executeTakeFirstOrThrow();
}

export async function updateProviderModel(
  db: DbExecutor,
  modelRecordId: string,
  patch: { modelId?: string; displayName?: string; enabled?: boolean },
): Promise<Selectable<ProviderModelsTable> | undefined> {
  return db
    .updateTable("provider_models")
    .set({
      ...(patch.modelId === undefined ? {} : { model_id: patch.modelId }),
      ...(patch.displayName === undefined ? {} : { display_name: patch.displayName }),
      ...(patch.enabled === undefined ? {} : { enabled: patch.enabled }),
      updated_at: new Date(),
    })
    .where("id", "=", modelRecordId)
    .returningAll()
    .executeTakeFirst();
}

/** Audit rows carry identifiers and outcome only: never requests, secrets or cookies. */
export async function recordAuditLog(
  db: DbExecutor,
  input: {
    id: string;
    actorUserId: string | null;
    action: string;
    resourceType: string;
    resourceId?: string | null;
    metadata?: Record<string, unknown>;
    succeeded: boolean;
  },
): Promise<void> {
  await db
    .insertInto("audit_logs")
    .values({
      id: input.id,
      actor_user_id: input.actorUserId,
      action: input.action,
      resource_type: input.resourceType,
      resource_id: input.resourceId ?? null,
      metadata: { ...(input.metadata ?? {}), succeeded: input.succeeded },
    })
    .execute();
}
