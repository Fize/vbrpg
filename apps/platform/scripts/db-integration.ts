import assert from "node:assert/strict";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import {
  bootstrapPlatformAdmin,
  closeDb,
  countActiveAdmins,
  createAuthSession,
  createDb,
  createGameInstance,
  createPlatformUser,
  createProvider,
  createProviderModel,
  deleteProvider,
  deleteProviderModel,
  findPlatformUserByUsername,
  getAuthSessionByTokenHash,
  getGameInstance,
  listProvidersWithModels,
  revokeUserSessions,
  setInstanceStatus,
} from "../src/server/db/index.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.log("Database integration test skipped: DATABASE_URL is not configured");
  process.exit(0);
}

const db = createDb({ databaseUrl });
const suffix = randomUUID();
const versionId = `integration-version-${suffix}`;
const instanceId = `integration-instance-${suffix}`;
const secondInstanceId = `integration-instance-b-${suffix}`;
const platformUserId = randomUUID();
const platformSessionId = randomUUID();
const providerId = randomUUID();
const providerName = `integration-provider-${suffix}`;

try {
  await createGameInstance(db, {
    id: instanceId,
    gameVersionId: versionId,
    status: "running",
    currentSequence: 0,
    stateJson: {},
  });
  await createGameInstance(db, {
    id: secondInstanceId,
    gameVersionId: versionId,
    status: "running",
    currentSequence: 0,
    stateJson: {},
  });
  assert.equal((await getGameInstance(db, instanceId))?.id, instanceId);
  assert.equal(await getGameInstance(db, `missing-${suffix}`), undefined);
  assert.equal(await setInstanceStatus(db, instanceId, "waiting"), true);
  assert.equal((await getGameInstance(db, instanceId))?.status, "waiting");

  // Seats and the event log are the only per-match data left; their uniqueness is the concurrency guard.
  await db
    .insertInto("game_participants")
    .values([
      {
        id: randomUUID(),
        instance_id: instanceId,
        actor_user_id: null,
        participant_key: "p1",
        control: "ai",
        status: "active",
        seat: 1,
      },
      {
        id: randomUUID(),
        instance_id: secondInstanceId,
        actor_user_id: null,
        participant_key: "p1",
        control: "ai",
        status: "active",
        seat: 1,
      },
    ])
    .execute();
  const seat = await db
    .selectFrom("game_participants")
    .select("id")
    .where("instance_id", "=", instanceId)
    .where("participant_key", "=", "p1")
    .executeTakeFirstOrThrow();

  await db
    .insertInto("game_events")
    .values([
      {
        id: randomUUID(),
        instance_id: instanceId,
        sequence: 1,
        type: "instanceCreated",
        participant_id: null,
        actor_user_id: null,
        step_id: "start",
        idempotency_key: "create",
        payload: {},
      },
      {
        id: randomUUID(),
        instance_id: instanceId,
        sequence: 2,
        type: "aiCall",
        participant_id: seat.id,
        actor_user_id: null,
        step_id: "night-1",
        idempotency_key: "turn-1",
        payload: { content: "vote p2", reasoning: "p2 spoke early" },
        provider_id: randomUUID(),
        model_id: "deepseek-chat",
        prompt_tokens: 1200,
        completion_tokens: 42,
        total_tokens: 1242,
      },
    ])
    .execute();

  // A repeat of either key must be rejected by the database, not by application code.
  for (const clash of [
    { sequence: 2, idempotency_key: "other-key", label: "sequence" },
    { sequence: 3, idempotency_key: "turn-1", label: "idempotency key" },
  ]) {
    let rejected = false;
    try {
      await db
        .insertInto("game_events")
        .values({
          id: randomUUID(),
          instance_id: instanceId,
          sequence: clash.sequence,
          type: "playerInputReceived",
          participant_id: null,
          actor_user_id: null,
          step_id: null,
          idempotency_key: clash.idempotency_key,
          payload: {},
        })
        .execute();
    } catch (error) {
      rejected = (error as { code?: string }).code === "23505";
    }
    assert.equal(rejected, true, `duplicate ${clash.label} must be rejected`);
  }

  // Usage is stored as a whole: a row may not carry only part of it.
  let partialUsageRejected = false;
  try {
    await db
      .insertInto("game_events")
      .values({
        id: randomUUID(),
        instance_id: instanceId,
        sequence: 4,
        type: "aiCall",
        participant_id: seat.id,
        actor_user_id: null,
        step_id: null,
        idempotency_key: "partial-usage",
        payload: {},
        total_tokens: 10,
      })
      .execute();
  } catch (error) {
    partialUsageRejected = (error as { code?: string }).code === "23514";
  }
  assert.equal(partialUsageRejected, true, "partial usage must be rejected");

  // A row cannot point at a seat of another match.
  let foreignSeatRejected = false;
  try {
    await db
      .insertInto("game_events")
      .values({
        id: randomUUID(),
        instance_id: secondInstanceId,
        sequence: 1,
        type: "playerInputReceived",
        participant_id: seat.id,
        actor_user_id: null,
        step_id: null,
        idempotency_key: "cross-seat",
        payload: {},
      })
      .execute();
  } catch (error) {
    foreignSeatRejected = (error as { code?: string }).code === "23503";
  }
  assert.equal(foreignSeatRejected, true, "a seat from another match must be rejected");

  // ─── Platform accounts, sessions and the provider catalog ─────────────────
  // The count is asserted as a delta: this database may already hold other administrators.
  const adminsBefore = await countActiveAdmins(db);
  const platformUser = await createPlatformUser(db, {
    id: platformUserId,
    username: `integration-admin-${suffix}`,
    passwordHash: "scrypt$v=1$N=32768,r=8,p=1$placeholder$placeholder",
    role: "admin",
  });
  assert.equal(platformUser.role, "admin");
  assert.equal(
    (await findPlatformUserByUsername(db, platformUser.username))?.id,
    platformUserId,
  );
  assert.equal(await countActiveAdmins(db), adminsBefore + 1);

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
  await createProviderModel(db, {
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

  // Uniqueness of (provider, model id) is enforced by the database.
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
    await deleteProvider(db, providerId);
  } catch (error) {
    restrictEnforced = (error as { code?: string }).code === "23503";
  }
  assert.equal(restrictEnforced, true, "provider delete must be restricted while models exist");

  // Only ciphertext is persisted.
  const stored = await db
    .selectFrom("providers")
    .select(["credential_ciphertext", "credential_tag"])
    .where("id", "=", providerId)
    .executeTakeFirstOrThrow();
  assert.equal(stored.credential_ciphertext.length, 32);
  assert.equal(stored.credential_tag.length, 16);

  // Deleting the models first makes the provider deletable.
  const catalogRows = await db
    .selectFrom("provider_models")
    .select("id")
    .where("provider_id", "=", providerId)
    .execute();
  for (const row of catalogRows) {
    assert.equal(await deleteProviderModel(db, row.id), true);
  }
  assert.equal(await deleteProvider(db, providerId), true);
  assert.equal(await deleteProvider(db, providerId), false, "a second delete must report nothing");


  console.log("Database integration test passed");
} finally {
  await db.deleteFrom("provider_models").where("provider_id", "=", providerId).execute();
  await db.deleteFrom("providers").where("id", "=", providerId).execute();
  await db.deleteFrom("auth_sessions").where("id", "=", platformSessionId).execute();
  await db.deleteFrom("audit_logs").where("actor_user_id", "=", platformUserId).execute();
  // Deleting an instance cascades to its participants and events, and it must go before the user
  // rows it references.
  await db.deleteFrom("game_instances").where("id", "in", [instanceId, secondInstanceId]).execute();
  await db.deleteFrom("users").where("id", "=", platformUserId).execute();
  await closeDb(db);
}
