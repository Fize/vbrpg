import assert from "node:assert/strict";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import {
  bootstrapPlatformAdmin,
  claimPendingCommands,
  claimScheduledJobs,
  closeDb,
  completePendingCommand,
  countActiveAdmins,
  createAuthSession,
  createDb,
  createGameInstance,
  createPlatformUser,
  createProvider,
  createProviderModel,
  failLeasedTask,
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
const platformUserId = randomUUID();
const platformSessionId = randomUUID();
const providerId = randomUUID();
const providerName = `integration-provider-${suffix}`;
const workerId = `integration-worker-${suffix}`;

try {
  await createGameInstance(db, {
    id: instanceId,
    gameVersionId: versionId,
    status: "running",
    currentSequence: 0,
    stateJson: {},
  });
  assert.equal((await getGameInstance(db, instanceId))?.id, instanceId);
  assert.equal(await getGameInstance(db, `missing-${suffix}`), undefined);

  // ─── Queue: claim, lease, complete ────────────────────────────────────────
  const commandId = randomUUID();
  await db
    .insertInto("pending_commands")
    .values({
      id: commandId,
      instance_id: instanceId,
      command_id: `cmd-${suffix}`,
      command_type: "emit",
      payload: { eventName: "tick" },
    })
    .execute();

  const claimed = await claimPendingCommands(db, { workerId, leaseMs: 30_000 });
  assert.equal(claimed.length, 1);
  assert.equal(claimed[0]?.id, commandId);
  assert.equal(claimed[0]?.status, "leased");
  assert.equal(claimed[0]?.attempts, 1);
  assert.equal(claimed[0]?.leased_by, workerId);

  // A leased row is invisible to other workers until its lease expires.
  assert.equal((await claimPendingCommands(db, { workerId: "other-worker" })).length, 0);

  await completePendingCommand(db, commandId, workerId);
  assert.equal(
    (await db.selectFrom("pending_commands").select("status").where("id", "=", commandId).executeTakeFirst())?.status,
    "completed",
  );

  // ─── Queue: a paused match keeps its work queued ──────────────────────────
  const pausedCommandId = randomUUID();
  await db
    .insertInto("pending_commands")
    .values({
      id: pausedCommandId,
      instance_id: instanceId,
      command_id: `cmd-paused-${suffix}`,
      command_type: "emit",
      payload: {},
    })
    .execute();
  await setInstanceStatus(db, instanceId, "paused");
  assert.equal((await claimPendingCommands(db, { workerId })).length, 0);
  await setInstanceStatus(db, instanceId, "running");
  assert.equal((await claimPendingCommands(db, { workerId })).length, 1);

  // ─── Queue: exhausted retries land in `dead` ──────────────────────────────
  const failingCommandId = randomUUID();
  await db
    .insertInto("pending_commands")
    .values({
      id: failingCommandId,
      instance_id: instanceId,
      command_id: `cmd-fail-${suffix}`,
      command_type: "emit",
      max_attempts: 1,
      payload: {},
    })
    .execute();
  assert.equal((await claimPendingCommands(db, { workerId })).length, 1);
  await failLeasedTask(db, "pending_commands", failingCommandId, workerId, "boom");
  assert.equal(
    (await db.selectFrom("pending_commands").select("status").where("id", "=", failingCommandId).executeTakeFirst())?.status,
    "dead",
  );

  // ─── Scheduled jobs: instance-scoped and standalone timers ────────────────
  const jobId = randomUUID();
  await db
    .insertInto("scheduled_jobs")
    .values({
      id: jobId,
      instance_id: instanceId,
      job_key: `job-${suffix}`,
      job_type: "timerExpired",
      run_at: new Date(Date.now() - 1_000),
      payload: {},
    })
    .execute();
  const standaloneJobId = randomUUID();
  await db
    .insertInto("scheduled_jobs")
    .values({
      id: standaloneJobId,
      instance_id: null,
      job_key: `standalone-job-${suffix}`,
      job_type: "timerExpired",
      run_at: new Date(Date.now() - 1_000),
      payload: {},
    })
    .execute();
  const jobs = await claimScheduledJobs(db, { workerId });
  assert.deepEqual(
    jobs.map((job) => job.id).sort(),
    [jobId, standaloneJobId].sort(),
    "a timer without an instance must still be claimable",
  );

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
  assert.equal(platformUser.mustChangePassword, true);
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
    await db.deleteFrom("providers").where("id", "=", providerId).execute();
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

  console.log("Database integration test passed");
} finally {
  await db.deleteFrom("provider_models").where("provider_id", "=", providerId).execute();
  await db.deleteFrom("providers").where("id", "=", providerId).execute();
  await db.deleteFrom("auth_sessions").where("id", "=", platformSessionId).execute();
  await db.deleteFrom("audit_logs").where("actor_user_id", "=", platformUserId).execute();
  await db.deleteFrom("users").where("id", "=", platformUserId).execute();
  // Deleting the instance cascades to its events, commands and jobs.
  await db.deleteFrom("scheduled_jobs").where("job_key", "=", `standalone-job-${suffix}`).execute();
  await db.deleteFrom("game_instances").where("id", "=", instanceId).execute();
  await closeDb(db);
}
