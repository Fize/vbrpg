import assert from "node:assert/strict";
import { randomBytes, randomUUID } from "node:crypto";
import { closeDb, createDb, PLATFORM_TENANT_ID, upsertAgentModelBinding } from "@vbrpg/db";
import { compileGameDefinition, createInitialState } from "@vbrpg/workflow-engine";
import type { GameEvent } from "@vbrpg/contracts";
import {
  createAiCommandHandler,
  createScheduledJobHandler,
  dispatchGameEvent,
  parseCredentialKey,
  sealCredential,
  type AiClient,
} from "@vbrpg/runtime";
import { createWorker } from "../src/worker.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.log("AI command integration test skipped: DATABASE_URL is not configured");
  process.exit(0);
}

const db = createDb({ databaseUrl });
const suffix = randomUUID();
const tenantId = `ai-tenant-${suffix}`;
const userId = `ai-user-${suffix}`;
const gameId = `ai-game-${suffix}`;
const boundVersionId = `ai-bound-version-${suffix}`;
const unboundVersionId = `ai-unbound-version-${suffix}`;
const successInstanceId = `ai-instance-ok-${suffix}`;
const unboundInstanceId = `ai-instance-unbound-${suffix}`;
const brokenInstanceId = `ai-instance-broken-${suffix}`;
const providerId = `ai-provider-${suffix}`;
const modelId = `ai-model-${suffix}`;
const credential = "sk-integration-secret";
const credentialKeyEncoded = randomBytes(32).toString("base64");
const credentialKey = parseCredentialKey(credentialKeyEncoded, 1);

function definition() {
  return {
    manifest: {
      gameId,
      slug: `ai-game-${suffix}`,
      version: "1.0.0",
      dslVersion: "v1",
      engineVersion: "native-test",
      authorId: userId,
      license: "MIT",
    },
    workflow: {
      entryNodeId: "start",
      nodes: [
        { id: "start", type: "start", config: {}, next: ["ai"] },
        {
          id: "ai",
          type: "aiGenerate",
          config: {
            agentId: "seer",
            input: { action: "choose" },
            timeoutMs: 5_000,
            maxAttempts: 2,
            fallbackNodeId: "degraded",
            resultKey: "choice",
          },
          next: ["end"],
        },
        { id: "degraded", type: "setVariable", config: { key: "degraded", value: true }, next: ["end"] },
        { id: "end", type: "end", config: {}, next: [] },
      ],
    },
    roles: [],
    variables: {},
    visibility: {},
    presentation: {},
  };
}

const compiled = compileGameDefinition(definition());

async function createWaitingInstance(
  gameVersionId: string,
  instanceId: string,
  game = compiled,
): Promise<void> {
  const initialState = createInitialState(game, {
    instanceId,
    gameVersionId,
    randomSeed: `seed-${instanceId}`,
    participants: [],
  });
  await db
    .insertInto("game_instances")
    .values({ id: instanceId, tenant_id: tenantId, game_version_id: gameVersionId, state_json: initialState })
    .execute();
  const event: GameEvent = {
    eventId: `${instanceId}-event-1`,
    instanceId,
    sequence: 1,
    type: "instanceCreated",
    actor: null,
    occurredAtMs: Date.now(),
    idempotencyKey: `${instanceId}-created`,
    payload: {},
  };
  const result = await dispatchGameEvent(db, { tenantId }, game, event);
  assert.notEqual(result.state.waiting, null);
  assert.notEqual(result.commands.length, 0);
}

async function instance(instanceId: string) {
  return db.selectFrom("game_instances").selectAll().where("id", "=", instanceId).executeTakeFirstOrThrow();
}

async function commandRow(instanceId: string) {
  return db
    .selectFrom("pending_commands")
    .selectAll()
    .where("tenant_id", "=", tenantId)
    .where("instance_id", "=", instanceId)
    .executeTakeFirstOrThrow();
}

async function eventTypes(instanceId: string): Promise<string[]> {
  const rows = await db
    .selectFrom("game_events")
    .select(["type"])
    .where("tenant_id", "=", tenantId)
    .where("instance_id", "=", instanceId)
    .orderBy("sequence", "asc")
    .execute();
  return rows.map((row) => row.type);
}

function variables(row: { state_json: unknown }): Record<string, unknown> {
  return (row.state_json as { variables: Record<string, unknown> }).variables;
}

const seededCredentials: string[] = [];
const timerCompiled = compileGameDefinition(timerDefinition());
const timerVersionId = `ai-timer-version-${suffix}`;
const timerInstanceId = `ai-timer-instance-${suffix}`;

function timerDefinition() {
  return {
    manifest: {
      gameId,
      slug: `timer-game-${suffix}`,
      version: "1.0.0",
      dslVersion: "v1",
      engineVersion: "native-test",
      authorId: userId,
      license: "MIT",
    },
    workflow: {
      entryNodeId: "start",
      nodes: [
        { id: "start", type: "start", config: {}, next: ["wait"] },
        { id: "wait", type: "timer", config: { durationMs: 1 }, next: ["end"] },
        { id: "end", type: "end", config: {}, next: [] },
      ],
    },
    roles: [],
    variables: {},
    visibility: {},
    presentation: {},
  };
}

let scheduledJobHandler: ((job: { tenant_id: string }) => Promise<unknown>) | undefined;

function setTimerHandler(handler: (job: { tenant_id: string }) => Promise<unknown>): void {
  scheduledJobHandler = handler;
}

function workerWith(handler: (command: { tenant_id: string }) => Promise<unknown>, workerId: string) {
  return createWorker(
    { workerId, pollIntervalMs: 10, leaseMs: 5_000 },
    { info: () => {} },
    {
      db,
      listTenantIds: async () => [tenantId],
      handlers: {
        handleCommand: handler as never,
        ...(scheduledJobHandler === undefined
          ? {}
          : { handleScheduledJob: scheduledJobHandler as never }),
      },
    },
  );
}

try {
  await db
    .insertInto("tenants")
    .values({ id: tenantId, slug: tenantId, name: "AI Integration", status: "active" })
    .execute();
  await db.insertInto("users").values({ id: userId, username: userId }).execute();
  await db
    .insertInto("tenant_memberships")
    .values({ tenant_id: tenantId, user_id: userId, role: "developer" })
    .execute();
  await db
    .insertInto("games")
    .values({
      id: gameId,
      tenant_id: tenantId,
      slug: `ai-game-${suffix}`,
      code: `ai-${suffix.slice(0, 8)}`,
      name: "AI Integration",
      owner_user_id: userId,
      visibility: "private",
    })
    .execute();

  for (const [versionId, version, definitionJson] of [
    [boundVersionId, "1.0.0", definition()],
    [unboundVersionId, "1.0.1", definition()],
    [timerVersionId, "1.0.2", timerDefinition()],
  ] as const) {
    await db
      .insertInto("game_versions")
      .values({
        id: versionId,
        tenant_id: tenantId,
        game_id: gameId,
        version,
        dsl_version: "v1",
        engine_version: "native-test",
        created_by: userId,
      })
      .execute();
    await db
      .insertInto("workflow_definitions")
      .values({
        id: `definition-${versionId}`,
        tenant_id: tenantId,
        game_version_id: versionId,
        schema_version: "v1",
        definition_json: definitionJson,
      })
      .execute();
  }

  const sealed = sealCredential(credential, providerId, credentialKey);
  await db
    .insertInto("providers")
    .values({
      id: providerId,
      tenant_id: PLATFORM_TENANT_ID,
      name: `provider-${suffix}`,
      base_url: "https://api.example.com/v1",
      enabled: true,
      ...sealed,
    })
    .execute();
  await db
    .insertInto("provider_models")
    .values({
      id: modelId,
      tenant_id: PLATFORM_TENANT_ID,
      provider_id: providerId,
      model_id: "test-model",
      display_name: "Test Model",
      enabled: true,
    })
    .execute();

  await upsertAgentModelBinding(db, { tenantId }, {
    gameVersionId: boundVersionId,
    agentId: "seer",
    providerModelId: modelId,
  });

  await createWaitingInstance(boundVersionId, successInstanceId);
  await createWaitingInstance(unboundVersionId, unboundInstanceId);

  const handler = createAiCommandHandler(db, {
    credentialKeyEncoded,
    createClient: (config): AiClient => {
      seededCredentials.push(config.apiKey ?? "");
      return {
        async generate() {
          return { choice: "A" };
        },
      };
    },
  });

  // Success path: claim -> resolve binding -> decrypt credential -> call -> aiResultReceived.
  const worker = workerWith(async (command) => handler(command as never), `ai-worker-${suffix}`);
  const firstRun = await worker.runOnce();
  assert.equal(firstRun.claimed, 2);
  assert.equal(firstRun.processed, 2);

  const success = await instance(successInstanceId);
  assert.equal(success.status, "completed");
  assert.deepEqual(variables(success).choice, { choice: "A" });
  assert.deepEqual(await eventTypes(successInstanceId), ["instanceCreated", "aiResultReceived"]);
  const successLedger = await db
    .selectFrom("ai_usage_ledger")
    .selectAll()
    .where("tenant_id", "=", tenantId)
    .where("instance_id", "=", successInstanceId)
    .execute();
  assert.equal(successLedger.length, 1);
  assert.equal((successLedger[0]?.metadata as { outcome?: string }).outcome, "completed");
  assert.deepEqual(seededCredentials, [credential]);

  // Drained queue and a re-delivered command must not advance the instance twice.
  assert.equal((await worker.runOnce()).claimed, 0);
  assert.equal((await handler(await commandRow(successInstanceId))).outcome, "skipped");

  // No binding: the instance leaves the AI node through its fallback branch instead of hanging.
  const unbound = await instance(unboundInstanceId);
  assert.equal(unbound.status, "completed");
  assert.equal(variables(unbound).degraded, true);
  assert.deepEqual(await eventTypes(unboundInstanceId), ["instanceCreated", "aiFailed"]);
  assert.equal(
    (
      await db
        .selectFrom("ai_usage_ledger")
        .select("id")
        .where("instance_id", "=", unboundInstanceId)
        .execute()
    ).length,
    0,
  );

  // Provider failure with attempts left goes back to the queue with backoff.
  await createWaitingInstance(boundVersionId, brokenInstanceId);
  const failingHandler = createAiCommandHandler(db, {
    credentialKeyEncoded,
    createClient: () => ({
      async generate() {
        throw new Error("provider exploded");
      },
    }),
  });
  const failingWorker = workerWith(
    async (command) => failingHandler({ ...(command as never), tenant_id: tenantId } as never),
    `ai-worker-fail-${suffix}`,
  );

  const thirdRun = await failingWorker.runOnce();
  assert.equal(thirdRun.claimed, 1);
  assert.equal(thirdRun.processed, 0);
  const retried = await commandRow(brokenInstanceId);
  assert.equal(retried.status, "pending");
  assert.equal(retried.attempts, 1);
  assert.match(retried.last_error ?? "", /provider exploded/);
  assert.deepEqual(await eventTypes(brokenInstanceId), ["instanceCreated"]);

  // Exhausting maxAttempts degrades rather than leaving the instance waiting forever.
  await db
    .updateTable("pending_commands")
    .set({ attempts: retried.max_attempts, status: "pending", available_at: new Date(), lease_until: null, leased_by: null })
    .where("id", "=", retried.id)
    .execute();
  const fourthRun = await failingWorker.runOnce();
  assert.equal(fourthRun.processed, 1);
  const broken = await instance(brokenInstanceId);
  assert.equal(broken.status, "completed");
  assert.equal(variables(broken).degraded, true);
  assert.deepEqual(await eventTypes(brokenInstanceId), ["instanceCreated", "aiFailed"]);
  const brokenLedger = await db
    .selectFrom("ai_usage_ledger")
    .selectAll()
    .where("instance_id", "=", brokenInstanceId)
    .execute();
  assert.equal(brokenLedger.length, 1);
  assert.match(String((brokenLedger[0]?.metadata as { reason?: string }).reason), /PROVIDER_ERROR/);

  // Timers are consumed by the same worker: an expired timer advances the instance.
  await createWaitingInstance(timerVersionId, timerInstanceId, timerCompiled);
  const timerRow = await db
    .selectFrom("game_instances")
    .selectAll()
    .where("id", "=", timerInstanceId)
    .executeTakeFirstOrThrow();
  assert.equal((timerRow.state_json as { waiting: { kind: string } }).waiting.kind, "timer");
  const scheduledBefore = await db
    .selectFrom("scheduled_jobs")
    .selectAll()
    .where("tenant_id", "=", tenantId)
    .where("instance_id", "=", timerInstanceId)
    .executeTakeFirstOrThrow();
  assert.equal(scheduledBefore.status, "scheduled");

  const timerHandler = createScheduledJobHandler(db);
  // The AI handler must refuse a job row: the two queues stay separate.
  await assert.rejects(async () => handler(scheduledBefore as never));

  setTimerHandler(async (job: { tenant_id: string }) => {
    await timerHandler({ ...(job as never), tenant_id: tenantId });
  });
  const timerWorker = workerWith(async () => undefined, `ai-timer-worker-${suffix}`);
  const timerRun = await timerWorker.runOnce();
  assert.equal(timerRun.claimed, 1);
  assert.equal(timerRun.processed, 1);
  const timerState = await db
    .selectFrom("game_instances")
    .selectAll()
    .where("id", "=", timerInstanceId)
    .executeTakeFirstOrThrow();
  assert.equal(timerState.status, "completed");
  assert.deepEqual(await eventTypes(timerInstanceId), ["instanceCreated", "timerExpired"]);
  const scheduledAfter = await db
    .selectFrom("scheduled_jobs")
    .selectAll()
    .where("id", "=", scheduledBefore.id)
    .executeTakeFirstOrThrow();
  assert.equal(scheduledAfter.status, "completed");

  // A timer that fires after the workflow moved on is a no-op, not a second advance.
  const staleTimer = await timerHandler({
    ...scheduledBefore,
    id: "stale",
    status: "leased",
    tenant_id: tenantId,
  } as never);
  assert.equal(staleTimer.outcome, "skipped");
  assert.equal(staleTimer.reason, "INSTANCE_NOT_WAITING_FOR_TIMER");
  assert.equal((await eventTypes(timerInstanceId)).length, 2);

  console.log("AI command integration test passed");
} finally {
  await db.deleteFrom("ai_usage_ledger").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("pending_commands").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("scheduled_jobs").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("game_events").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("game_instances").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("agent_model_bindings").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("workflow_definitions").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("game_versions").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("games").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("provider_models").where("id", "=", modelId).execute();
  await db.deleteFrom("providers").where("id", "=", providerId).execute();
  await db.deleteFrom("tenant_memberships").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("tenants").where("id", "=", tenantId).execute();
  await db.deleteFrom("users").where("id", "=", userId).execute();
  await closeDb(db);
}
