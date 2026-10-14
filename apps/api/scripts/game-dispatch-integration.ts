import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import {
  closeDb,
  createDb,
  getGameInstance,
} from "@vbrpg/db";
import { compileGameDefinition, createInitialState } from "@vbrpg/workflow-engine";
import type { GameEvent } from "@vbrpg/contracts";
import { dispatchGameEvent } from "@vbrpg/runtime";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.log("Game dispatch integration test skipped: DATABASE_URL is not configured");
  process.exit(0);
}

const db = createDb({ databaseUrl });
const suffix = randomUUID();
const tenantId = `dispatch-tenant-${suffix}`;
const userId = `dispatch-user-${suffix}`;
const gameId = `dispatch-game-${suffix}`;
const versionId = `dispatch-version-${suffix}`;
const instanceId = `dispatch-instance-${suffix}`;

const compiled = compileGameDefinition({
  manifest: {
    gameId,
    slug: `dispatch-game-${suffix}`,
    version: "1.0.0",
    dslVersion: "v1",
    engineVersion: "native-test",
    authorId: userId,
    license: "MIT",
  },
  workflow: {
    entryNodeId: "start",
    nodes: [
      { id: "start", type: "start", config: {}, next: ["timer"] },
      { id: "timer", type: "timer", config: { durationMs: 1 }, next: ["end"] },
      { id: "end", type: "end", config: {}, next: [] },
    ],
  },
  roles: [],
  variables: {},
  visibility: {},
  presentation: {},
});

try {
  await db.insertInto("tenants").values({ id: tenantId, slug: tenantId, name: "Dispatch Integration", status: "active" }).execute();
  await db.insertInto("users").values({ id: userId, username: userId }).execute();
  await db.insertInto("tenant_memberships").values({ tenant_id: tenantId, user_id: userId, role: "developer" }).execute();
  await db.insertInto("games").values({
    id: gameId,
    tenant_id: tenantId,
    slug: `dispatch-game-${suffix}`,
    code: `dispatch-${suffix.slice(0, 8)}`,
    name: "Dispatch Integration",
    owner_user_id: userId,
    visibility: "private",
  }).execute();
  await db.insertInto("game_versions").values({
    id: versionId,
    tenant_id: tenantId,
    game_id: gameId,
    version: "1.0.0",
    dsl_version: "v1",
    engine_version: "native-test",
    created_by: userId,
  }).execute();
  const initialState = createInitialState(compiled, {
    instanceId,
    gameVersionId: versionId,
    randomSeed: "dispatch-seed",
    participants: [],
  });
  await db.insertInto("game_instances").values({
    id: instanceId,
    tenant_id: tenantId,
    game_version_id: versionId,
    state_json: initialState,
  }).execute();

  const createEvent: GameEvent = {
    eventId: `${instanceId}-event-1`,
    instanceId,
    sequence: 1,
    type: "instanceCreated",
    actor: null,
    occurredAtMs: Date.now(),
    idempotencyKey: `${instanceId}-create`,
    payload: {},
  };
  const first = await dispatchGameEvent(db, { tenantId }, compiled, createEvent);
  assert.equal(first.replayed, false);
  assert.equal(first.state.status, "waiting");
  assert.equal(first.commands[0]?.type, "schedule");

  const replay = await dispatchGameEvent(db, { tenantId }, compiled, createEvent);
  assert.equal(replay.replayed, true);
  assert.equal(replay.commands.length, 0);

  const timerEvent: GameEvent = {
    eventId: `${instanceId}-event-2`,
    instanceId,
    sequence: 2,
    type: "timerExpired",
    actor: null,
    occurredAtMs: Date.now(),
    idempotencyKey: `${instanceId}-timer`,
    payload: { nodeId: "timer" },
  };
  const second = await dispatchGameEvent(db, { tenantId }, compiled, timerEvent);
  assert.equal(second.state.status, "completed");
  assert.equal((await db.selectFrom("game_events").select("id").where("instance_id", "=", instanceId).execute()).length, 2);
  assert.equal((await db.selectFrom("scheduled_jobs").select("id").where("instance_id", "=", instanceId).execute()).length, 1);
  assert.equal((await getGameInstance(db, { tenantId }, instanceId))?.current_sequence, 2);
  console.log("Game dispatch integration test passed");
} finally {
  await db.deleteFrom("game_instances").where("id", "=", instanceId).execute();
  await db.deleteFrom("game_versions").where("id", "=", versionId).execute();
  await db.deleteFrom("games").where("id", "=", gameId).execute();
  await db.deleteFrom("tenant_memberships").where("tenant_id", "=", tenantId).execute();
  await db.deleteFrom("tenants").where("id", "=", tenantId).execute();
  await db.deleteFrom("users").where("id", "=", userId).execute();
  await closeDb(db);
}
