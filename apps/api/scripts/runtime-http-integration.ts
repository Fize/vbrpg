import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { closeDb, createDb, createPlatformUser, PLATFORM_TENANT_ID } from "@vbrpg/db";
import { loadConfig } from "../src/config.js";
import { buildApp } from "../src/app.js";
import { hashPassword } from "../src/password.js";
import { createPlatformStore } from "../src/store.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.log("Runtime HTTP integration test skipped: DATABASE_URL is not configured");
  process.exit(0);
}

const db = createDb({ databaseUrl });
const suffix = randomUUID();
const username = `runtime-admin-${suffix.slice(0, 8)}`;
const password = "runtime-integration-1";
const gameId = `runtime-game-${suffix}`;
const versionId = `runtime-version-${suffix}`;
const userId = `runtime-user-${suffix}`;
const ORIGIN = "http://localhost:5173";

let instanceId: string | undefined;

try {
  await db
    .insertInto("tenants")
    .values({ id: PLATFORM_TENANT_ID, slug: PLATFORM_TENANT_ID, name: "Platform", status: "active" })
    .onConflict((conflict) => conflict.column("id").doNothing())
    .execute();
  await createPlatformUser(db, {
    id: userId,
    username,
    passwordHash: await hashPassword(password),
    role: "admin",
    mustChangePassword: false,
  });

  await db
    .insertInto("games")
    .values({
      id: gameId,
      tenant_id: PLATFORM_TENANT_ID,
      slug: `runtime-game-${suffix.slice(0, 8)}`,
      code: `rt-${suffix.slice(0, 8)}`,
      name: "Runtime HTTP Integration",
      owner_user_id: userId,
      visibility: "private",
    })
    .execute();
  await db
    .insertInto("game_versions")
    .values({
      id: versionId,
      tenant_id: PLATFORM_TENANT_ID,
      game_id: gameId,
      version: "1.0.0",
      dsl_version: "v1",
      engine_version: "native-test",
      created_by: userId,
    })
    .execute();
  await db
    .insertInto("workflow_definitions")
    .values({
      id: `definition-${versionId}`,
      tenant_id: PLATFORM_TENANT_ID,
      game_version_id: versionId,
      schema_version: "v1",
      definition_json: {
        manifest: {
          gameId,
          slug: `runtime-game-${suffix.slice(0, 8)}`,
          version: "1.0.0",
          dslVersion: "v1",
          engineVersion: "native-test",
          authorId: userId,
          license: "MIT",
        },
        workflow: {
          entryNodeId: "start",
          nodes: [
            { id: "start", type: "start", config: {}, next: ["ask"] },
            {
              id: "ask",
              type: "waitForPlayerInput",
              config: { inputKey: "answer", participantId: "p1" },
              next: ["end"],
            },
            { id: "end", type: "end", config: {}, next: [] },
          ],
        },
        roles: [],
        variables: {},
        visibility: {},
        presentation: {},
      },
    })
    .execute();

  const app = buildApp({
    config: loadConfig({
      NODE_ENV: "test",
      TRUSTED_WEB_ORIGINS: ORIGIN,
      PLATFORM_CREDENTIAL_KEY: process.env.PLATFORM_CREDENTIAL_KEY ?? "unused-in-this-script",
      DATABASE_URL: databaseUrl,
    }),
    platformStore: createPlatformStore(db),
  });

  const login = await app.inject({
    method: "POST",
    url: "/v1/auth/login",
    headers: { origin: ORIGIN },
    payload: { username, password },
  });
  assert.equal(login.statusCode, 200);
  const cookieHeader = login.headers["set-cookie"];
  const cookie = Array.isArray(cookieHeader) ? (cookieHeader[0] ?? "") : (cookieHeader ?? "");
  const csrf = (login.json() as { csrfToken: string }).csrfToken;
  const writeHeaders = { origin: ORIGIN, cookie, "x-csrf-token": csrf };

  const created = await app.inject({
    method: "POST",
    url: "/v1/instances",
    headers: writeHeaders,
    payload: { gameVersionId: versionId, randomSeed: "runtime-seed" },
  });
  assert.equal(created.statusCode, 201);
  const createdBody = created.json() as {
    instanceId: string;
    state: { status: string; sequence: number; waiting: { kind: string } | null };
  };
  instanceId = createdBody.instanceId;
  assert.equal(createdBody.state.status, "waiting");
  assert.equal(createdBody.state.waiting?.kind, "playerInput");

  const read = await app.inject({
    method: "GET",
    url: `/v1/instances/${instanceId}`,
    headers: { cookie },
  });
  assert.equal(read.statusCode, 200);
  assert.equal((read.json() as { currentSequence: number }).currentSequence, 1);

  const eventHeaders = { ...writeHeaders, "idempotency-key": "answer-1" };
  const answered = await app.inject({
    method: "POST",
    url: `/v1/instances/${instanceId}/events`,
    headers: eventHeaders,
    payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
  });
  assert.equal(answered.statusCode, 200);
  const answeredBody = answered.json() as { state: { status: string; sequence: number }; replayed: boolean };
  assert.equal(answeredBody.replayed, false);
  assert.equal(answeredBody.state.status, "completed");
  assert.equal(answeredBody.state.sequence, 2);

  // The retry must replay the recorded outcome, not advance the instance a second time.
  const retried = await app.inject({
    method: "POST",
    url: `/v1/instances/${instanceId}/events`,
    headers: eventHeaders,
    payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "yes" } },
  });
  assert.equal(retried.statusCode, 200);
  assert.equal((retried.json() as { replayed: boolean }).replayed, true);
  assert.equal((retried.json() as { state: { sequence: number } }).state.sequence, 2);

  const rejected = await app.inject({
    method: "POST",
    url: `/v1/instances/${instanceId}/events`,
    headers: { ...writeHeaders, "idempotency-key": "answer-2" },
    payload: { type: "playerInputReceived", payload: { participantId: "p1", value: "no" } },
  });
  assert.equal(rejected.statusCode, 409);
  assert.equal(rejected.json().code, "UNEXPECTED_INPUT");

  const events = await db
    .selectFrom("game_events")
    .select(["type", "sequence"])
    .where("instance_id", "=", instanceId)
    .orderBy("sequence", "asc")
    .execute();
  assert.deepEqual(
    events.map((row) => [row.sequence, row.type]),
    [[1, "instanceCreated"], [2, "playerInputReceived"]],
  );
  const instanceRow = await db
    .selectFrom("game_instances")
    .select(["status", "current_sequence"])
    .where("id", "=", instanceId)
    .executeTakeFirstOrThrow();
  assert.equal(instanceRow.status, "completed");
  assert.equal(instanceRow.current_sequence, 2);

  console.log("Runtime HTTP integration test passed");
} finally {
  if (instanceId !== undefined) {
    await db.deleteFrom("game_events").where("instance_id", "=", instanceId).execute();
    await db.deleteFrom("game_instances").where("id", "=", instanceId).execute();
  }
  await db.deleteFrom("workflow_definitions").where("game_version_id", "=", versionId).execute();
  await db.deleteFrom("game_versions").where("id", "=", versionId).execute();
  await db.deleteFrom("games").where("id", "=", gameId).execute();
  await db.deleteFrom("auth_sessions").where("user_id", "=", userId).execute();
  await db.deleteFrom("audit_logs").where("actor_user_id", "=", userId).execute();
  await db.deleteFrom("tenant_memberships").where("user_id", "=", userId).execute();
  await db.deleteFrom("users").where("id", "=", userId).execute();
  await closeDb(db);
}
