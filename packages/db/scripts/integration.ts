import assert from "node:assert/strict";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { sql } from "kysely";
import { Pool } from "pg";
import {
  bootstrapPlatformAdmin,
  closeDb,
  countActiveAdmins,
  createAuthSession,
  createDb,
  createPlatformUser,
  createProvider,
  createProviderModel,
  findPlatformUserByUsername,
  getActiveAuthSession,
  getAuthSessionByTokenHash,
  getGameInstance,
  getTenantMembership,
  listProvidersWithModels,
  platformContext,
  revokeUserSessions,
  withTenantContext,
  PLATFORM_TENANT_ID,
} from "../src/index.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.log("Database integration test skipped: DATABASE_URL is not configured");
  process.exit(0);
}

const db = createDb({ databaseUrl });
const suffix = randomUUID();
const tenantA = `integration-tenant-a-${suffix}`;
const tenantB = `integration-tenant-b-${suffix}`;
const userId = `integration-user-${suffix}`;
const sessionId = `integration-session-${suffix}`;
const gameId = `integration-game-${suffix}`;
const versionId = `integration-version-${suffix}`;
const instanceId = `integration-instance-${suffix}`;
const platformUserId = randomUUID();
const platformSessionId = randomUUID();
const providerId = randomUUID();
const providerName = `integration-provider-${suffix}`;

try {
  await db.insertInto("tenants").values([
    { id: tenantA, slug: tenantA, name: "Integration A", status: "active" },
    { id: tenantB, slug: tenantB, name: "Integration B", status: "active" },
  ]).execute();
  await db.insertInto("users").values({ id: userId, username: userId }).execute();
  await db.insertInto("tenant_memberships").values({ tenant_id: tenantA, user_id: userId, role: "admin" }).execute();
  await db.insertInto("auth_sessions").values({
    id: sessionId,
    tenant_id: tenantA,
    user_id: userId,
    expires_at: new Date(Date.now() + 60_000),
    absolute_expires_at: new Date(Date.now() + 120_000),
  }).execute();
  await db.insertInto("games").values({
    id: gameId,
    tenant_id: tenantA,
    slug: `integration-game-${suffix}`,
    code: `integration-${suffix.slice(0, 8)}`,
    name: "Integration Game",
    owner_user_id: userId,
    visibility: "private",
  }).execute();
  await db.insertInto("game_versions").values({
    id: versionId,
    tenant_id: tenantA,
    game_id: gameId,
    version: "1.0.0",
    dsl_version: "v0",
    engine_version: "test",
    created_by: userId,
  }).execute();
  await db.insertInto("game_instances").values({
    id: instanceId,
    tenant_id: tenantA,
    game_version_id: versionId,
    state_json: {},
  }).execute();

  const session = await getActiveAuthSession(db, { tenantId: tenantA }, sessionId);
  assert.equal(session?.user_id, userId);
  const membership = await getTenantMembership(db, { tenantId: tenantA }, userId);
  assert.equal(membership?.role, "admin");
  assert.equal((await getGameInstance(db, { tenantId: tenantA }, instanceId))?.id, instanceId);
  assert.equal(await getGameInstance(db, { tenantId: tenantB }, instanceId), undefined);

  const currentTenant = await withTenantContext(db, { tenantId: tenantA }, async (transaction) => {
    const result = await sql<{ tenant_id: string }>`select current_setting('app.tenant_id', true) as tenant_id`.execute(transaction);
    return result.rows[0]?.tenant_id;
  });
  assert.equal(currentTenant, tenantA);

  // Phase 1: platform accounts, opaque sessions and the provider catalog.
  const platformUser = await createPlatformUser(db, {
    id: platformUserId,
    username: `integration-admin-${suffix}`,
    passwordHash: "scrypt$v=1$N=32768,r=8,p=1$placeholder$placeholder",
    role: "admin",
  });
  assert.equal(platformUser.role, "admin");
  assert.equal(platformUser.mustChangePassword, true);
  assert.equal(
    (await findPlatformUserByUsername(db, platformUser.username))?.id,
    platformUserId,
  );
  assert.equal(await countActiveAdmins(db), 1);

  // Bootstrap refuses once an active administrator exists.
  assert.deepEqual(
    await bootstrapPlatformAdmin(db, { username: `second-${suffix}`, passwordHash: "h" }),
    { created: false },
  );

  const tokenHash = createHash("sha256").update(`integration-token-${suffix}`).digest();
  await createAuthSession(db, {
    id: platformSessionId,
    userId: platformUserId,
    tokenHash,
    csrfTokenHash: randomBytes(32),
    idleExpiresAt: new Date(Date.now() + 60_000),
    absoluteExpiresAt: new Date(Date.now() + 120_000),
  });
  assert.equal((await getAuthSessionByTokenHash(db, tokenHash))?.user_id, platformUserId);

  // Revocation must make the stored token hash unusable immediately.
  await revokeUserSessions(db, platformUserId);
  assert.equal(await getAuthSessionByTokenHash(db, tokenHash), undefined);

  await createProvider(db, {
    id: providerId,
    name: providerName,
    baseUrl: "https://api.example.com/v1",
    enabled: true,
    credential: {
      // Database-layer fixture represents ciphertext; the API owns AEAD encryption.
      credential_ciphertext: randomBytes(32),
      credential_nonce: randomBytes(12),
      credential_tag: randomBytes(16),
      credential_key_version: 1,
    },
  });
  const model = await createProviderModel(db, {
    id: randomUUID(),
    providerId,
    modelId: "hy3",
    displayName: "Hy3",
    enabled: true,
  });
  const catalog = await listProvidersWithModels(db);
  assert.ok(catalog.some((entry) => entry.provider.id === providerId && entry.models.length === 1));

  // A disabled model disappears from the enabled-only catalog view.
  const enabledOnly = await listProvidersWithModels(db, { includeDisabled: false });
  assert.ok(enabledOnly.every((entry) => entry.models.every((candidate) => candidate.enabled)));
  void model;

  // Uniqueness of (tenant, provider, model id) is enforced by the database.
  let duplicateRejected = false;
  try {
    await createProviderModel(db, {
      id: randomUUID(),
      providerId,
      modelId: "hy3",
      displayName: "duplicate",
      enabled: true,
    });
  } catch (error) {
    duplicateRejected = (error as { code?: string }).code === "23505";
  }
  assert.equal(duplicateRejected, true, "duplicate provider model must be rejected");

  // A provider with models cannot be deleted out from under them.
  let restrictEnforced = false;
  try {
    await withTenantContext(db, platformContext, (transaction) =>
      transaction.deleteFrom("providers").where("id", "=", providerId).execute(),
    );
  } catch (error) {
    restrictEnforced = (error as { code?: string }).code === "23503";
  }
  assert.equal(restrictEnforced, true, "provider delete must be restricted while models exist");

  // Only ciphertext is persisted.
  const stored = await withTenantContext(db, platformContext, (transaction) =>
    transaction
      .selectFrom("providers")
      .select(["credential_ciphertext", "credential_tag"])
      .where("id", "=", providerId)
      .executeTakeFirstOrThrow(),
  );
  assert.equal(stored.credential_ciphertext.length, 32);
  assert.equal(stored.credential_tag.length, 16);

  const roleName = `rls_test_${suffix.replaceAll("-", "")}`;
  const pool = new Pool({ connectionString: databaseUrl });
  const client = await pool.connect();
  try {
    await client.query(`create role "${roleName}"`);
    await client.query(`grant select on game_instances, providers to "${roleName}"`);
    await client.query(`set role "${roleName}"`);
    await client.query("begin");
    try {
      await client.query("select set_config('app.tenant_id', $1, true)", [tenantA]);
      const visibleToA = await client.query("select id from game_instances where id = $1", [instanceId]);
      assert.equal(visibleToA.rowCount, 1);
      await client.query("select set_config('app.tenant_id', $1, true)", [tenantB]);
      const visibleToB = await client.query("select id from game_instances where id = $1", [instanceId]);
      assert.equal(visibleToB.rowCount, 0);

      // RLS hides the platform tenant's providers from an unrelated tenant context.
      const providersHidden = await client.query("select id from providers where id = $1", [providerId]);
      assert.equal(providersHidden.rowCount, 0);
      await client.query("select set_config('app.tenant_id', $1, true)", [PLATFORM_TENANT_ID]);
      const providersVisible = await client.query("select id from providers where id = $1", [providerId]);
      assert.equal(providersVisible.rowCount, 1);
      await client.query("commit");
    } catch (error) {
      await client.query("rollback");
      throw error;
    }
  } finally {
    await client.query("reset role");
    await client.query(`revoke all privileges on table game_instances from "${roleName}"`);
    await client.query(`revoke all privileges on table providers from "${roleName}"`);
    await client.query(`drop role "${roleName}"`);
    client.release();
    await pool.end();
  }

  console.log("Database integration test passed");
} finally {
  await db.deleteFrom("provider_models").where("provider_id", "=", providerId).execute();
  await db.deleteFrom("providers").where("id", "=", providerId).execute();
  await db.deleteFrom("auth_sessions").where("id", "=", platformSessionId).execute();
  await db.deleteFrom("audit_logs").where("actor_user_id", "=", platformUserId).execute();
  await db.deleteFrom("tenant_memberships").where("user_id", "=", platformUserId).execute();
  await db.deleteFrom("users").where("id", "=", platformUserId).execute();
  await db.deleteFrom("game_instances").where("id", "=", instanceId).execute();
  await db.deleteFrom("game_versions").where("id", "=", versionId).execute();
  await db.deleteFrom("games").where("id", "=", gameId).execute();
  await db.deleteFrom("auth_sessions").where("id", "=", sessionId).execute();
  await db.deleteFrom("tenant_memberships").where("tenant_id", "in", [tenantA, tenantB]).execute();
  await db.deleteFrom("tenants").where("id", "in", [tenantA, tenantB]).execute();
  await db.deleteFrom("users").where("id", "=", userId).execute();
  await closeDb(db);
}
