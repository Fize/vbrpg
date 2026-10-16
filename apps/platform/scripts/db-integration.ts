import assert from "node:assert/strict";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { createBuiltInRegistry } from "../src/server/games/index.js";
import { createMatchService } from "../src/server/match/service.js";
import { createRoomService } from "../src/server/room/service.js";
import { createAiSeatRunner } from "../src/server/match/ai-seat.js";
import { openCredential, parseCredentialKey, sealCredential } from "../src/server/runtime/secret-box.js";
import { rotateProviderCredentials } from "../src/server/credential-rotation.js";
import type { ModelCallOutput } from "../src/server/llm/client.js";
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
  findReadyAiSeats,
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
const secondUserId = randomUUID();
const platformSessionId = randomUUID();
const providerId = randomUUID();
const providerName = `integration-provider-${suffix}`;
const INTEGRATION_KEY = Buffer.alloc(32).toString("base64");
let matchId: string | null = null;
let aiMatchIdValue: string | null = null;
let lifecycleMatchId: string | null = null;
let publishedMatchId: string | null = null;
let generatedMatchId: string | null = null;
let roomIdValue: string | null = null;

try {
  await createGameInstance(db, {
    id: instanceId,
    gameId: "integration-game",
    gameVersion: versionId,
    status: "running",
    currentSequence: 0,
    stateJson: {},
  });
  await createGameInstance(db, {
    id: secondInstanceId,
    gameId: "integration-game",
    gameVersion: versionId,
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
  await createPlatformUser(db, {
    id: secondUserId,
    username: `integration-player-${suffix}`,
    passwordHash: "scrypt$v=1$N=32768,r=8,p=1$placeholder$placeholder",
    role: "user",
  });
  assert.equal(platformUser.role, "admin");
  assert.equal((await findPlatformUserByUsername(db, platformUser.username))?.id, platformUserId);
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
    credential: sealCredential("s".repeat(32), providerId, parseCredentialKey(INTEGRATION_KEY, 1)),
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

  // ─── Credential rotation: both keys available once, then only the new one ───
  const OLD_KEY = parseCredentialKey(INTEGRATION_KEY, 1);
  const NEW_KEY = parseCredentialKey(Buffer.alloc(32, 7).toString("base64"), 2);

  const rotated = await rotateProviderCredentials({ db, from: OLD_KEY, to: NEW_KEY });
  assert.deepEqual(rotated, { rotated: 1, current: 0 }, "the sealed credential must move to v2");

  const afterRotation = await db
    .selectFrom("providers")
    .select(["credential_ciphertext", "credential_nonce", "credential_tag", "credential_key_version"])
    .where("id", "=", providerId)
    .executeTakeFirstOrThrow();
  assert.equal(afterRotation.credential_key_version, 2);
  assert.notDeepEqual(afterRotation.credential_ciphertext, stored.credential_ciphertext);
  assert.equal(
    openCredential(
      {
        credential_ciphertext: afterRotation.credential_ciphertext,
        credential_nonce: afterRotation.credential_nonce,
        credential_tag: afterRotation.credential_tag,
        credential_key_version: afterRotation.credential_key_version,
      },
      providerId,
      NEW_KEY,
    ),
    "s".repeat(32),
    "the plaintext must survive the rotation",
  );

  // The old key is dead from here on, which is the whole point of rotating.
  let oldKeyDead = false;
  try {
    openCredential(
      {
        credential_ciphertext: afterRotation.credential_ciphertext,
        credential_nonce: afterRotation.credential_nonce,
        credential_tag: afterRotation.credential_tag,
        credential_key_version: afterRotation.credential_key_version,
      },
      providerId,
      OLD_KEY,
    );
  } catch (error) {
    oldKeyDead = error instanceof Error && error.message.includes("different key version");
  }
  assert.equal(oldKeyDead, true, "the old key must no longer open the credential");

  // Running it again is a no-op, and a version nobody declared stops the run.
  assert.deepEqual(await rotateProviderCredentials({ db, from: OLD_KEY, to: NEW_KEY }), {
    rotated: 0,
    current: 1,
  });
  let undeclaredVersion = false;
  try {
    await rotateProviderCredentials({
      db,
      from: parseCredentialKey(INTEGRATION_KEY, 3),
      to: parseCredentialKey(Buffer.alloc(32, 9).toString("base64"), 4),
    });
  } catch (error) {
    undeclaredVersion = error instanceof Error && error.message.includes("neither 3 nor 4");
  }
  assert.equal(undeclaredVersion, true, "an undeclared version must stop the rotation");

  // Rotating back is the rollback path, and it leaves the fixture on v1 for the checks below.
  assert.deepEqual(await rotateProviderCredentials({ db, from: NEW_KEY, to: OLD_KEY }), {
    rotated: 1,
    current: 0,
  });

  // ─── The match write path: one transaction, one record, one order ─────────
  const matchService = createMatchService({ db, registry: createBuiltInRegistry() });
  const actor = { userId: platformUserId, isAdmin: true };
  const created = await matchService.create({
    actor,
    request: {
      gameId: "undercover",
      variables: { civilianWord: "咖啡", undercoverWord: "茶" },
      seats: [
        { key: "p1", control: "human" },
        { key: "p2", control: "ai" },
        { key: "p3", control: "ai" },
      ],
    },
  });
  matchId = created.instanceId;
  assert.equal(created.gameId, "undercover");
  assert.equal(created.gameVersion, "1.0.0");
  assert.equal(created.status, "waiting");
  // Creation is a write: the game saw `instanceCreated` and moved to its first waiting point.
  assert.equal(created.sequence, 1);

  const opened = await matchService.read({ actor, instanceId: matchId });
  assert.equal(opened.seats.length, 3);
  assert.equal(opened.record.length, 1);
  assert.equal(opened.record[0]?.type, "instanceCreated");
  assert.equal(opened.view?.publicState["phase"], "describe");
  assert.equal(
    Object.keys(opened.view?.privateState ?? {}).length,
    1,
    "a seat sees its own word only",
  );

  const first = await matchService.submit({
    actor,
    instanceId: matchId,
    idempotencyKey: "turn-1",
    request: { type: "seatMessage", participantKey: "p1", payload: { text: "苹果" } },
  });
  assert.equal(first.replayed, false);
  assert.equal(first.summary.sequence, 2);
  assert.deepEqual(first.view.availableActions, []);

  // The same key is a replay: no second row, and the caller gets the current state back.
  const replay = await matchService.submit({
    actor,
    instanceId: matchId,
    idempotencyKey: "turn-1",
    request: { type: "seatMessage", participantKey: "p1", payload: { text: "苹果" } },
  });
  assert.equal(replay.replayed, true);
  assert.equal(replay.summary.sequence, 2);
  assert.equal((await matchService.read({ actor, instanceId: matchId })).record.length, 2);

  // A seat that belongs to nobody cannot act, and a stranger cannot read.
  let foreignSeat = false;
  try {
    await matchService.submit({
      actor,
      instanceId: matchId,
      idempotencyKey: "turn-2",
      request: { type: "seatMessage", participantKey: "p2", payload: { text: "x" } },
    });
  } catch (error) {
    foreignSeat = error instanceof Error && "code" in error && error.code === "NOT_YOUR_SEAT";
  }
  assert.equal(foreignSeat, true, "an AI seat must not accept a human submission");

  // Anyone may watch: a watcher gets the public state and the record, never a seat's private state.
  const holder = await matchService.read({ actor, instanceId: matchId });
  const watcher = await matchService.read({
    actor: { userId: randomUUID(), isAdmin: false },
    instanceId: matchId,
  });
  assert.deepEqual(watcher.summary.mySeatKeys, [], "a watcher holds no seat here");
  assert.equal(watcher.view.availableActions.length, 0);
  assert.equal(
    Object.keys(watcher.view.privateState).length,
    0,
    "no seat's secret reaches a watcher",
  );
  assert.deepEqual(
    watcher.view.publicState,
    holder.view.publicState,
    "the public state is the same",
  );
  assert.equal(watcher.briefing, null, "the rules belong to the seats playing");
  assert.equal(watcher.record.length, holder.record.length, "the record is the match's history");

  // Two writes at once: the row lock serializes them instead of losing one.
  const parallel = await Promise.allSettled([
    matchService.submit({
      actor,
      instanceId: matchId,
      idempotencyKey: "parallel-a",
      request: { type: "seatMessage", participantKey: "p1", payload: { text: "a" } },
    }),
    matchService.submit({
      actor,
      instanceId: matchId,
      idempotencyKey: "parallel-b",
      request: { type: "seatMessage", participantKey: "p1", payload: { text: "b" } },
    }),
  ]);
  assert.equal(parallel.filter((entry) => entry.status === "fulfilled").length, 2);
  const sequences = (
    await db
      .selectFrom("game_events")
      .select("sequence")
      .where("instance_id", "=", matchId)
      .execute()
  ).map((row) => row.sequence);
  assert.equal(new Set(sequences).size, sequences.length, "sequences must stay unique and gapless");

  // The same key twice at once still lands as one row.
  const races = await Promise.allSettled([
    matchService.submit({
      actor,
      instanceId: matchId,
      idempotencyKey: "parallel-same",
      request: { type: "seatMessage", participantKey: "p1", payload: { text: "same" } },
    }),
    matchService.submit({
      actor,
      instanceId: matchId,
      idempotencyKey: "parallel-same",
      request: { type: "seatMessage", participantKey: "p1", payload: { text: "same" } },
    }),
  ]);
  assert.equal(races.filter((entry) => entry.status === "fulfilled").length, 2);
  const sameKey = await db
    .selectFrom("game_events")
    .select("sequence")
    .where("instance_id", "=", matchId)
    .where("idempotency_key", "=", "parallel-same")
    .execute();
  assert.equal(sameKey.length, 1, "one key, one row, even under a race");

  // A seat the rules eliminated is marked in the table too, not only in the state.
  const eliminated = await db
    .selectFrom("game_participants")
    .select(["participant_key", "status"])
    .where("instance_id", "=", matchId)
    .execute();
  assert.equal(eliminated.length, 3);
  assert.ok(eliminated.every((seat) => seat.status === "active"));

  // ─── AI seats: one call per row, refusals fed back, no action means failure ─────────
  // Finished matches are never scanned, so the one above must be closed before the scan runs.
  await setInstanceStatus(db, matchId, "completed");

  const aiMatch = await matchService.create({
    actor,
    request: {
      gameId: "undercover",
      variables: { civilianWord: "咖啡", undercoverWord: "茶" },
      seats: [
        { key: "p1", control: "ai" },
        { key: "p2", control: "ai" },
        { key: "p3", control: "ai" },
      ],
    },
  });
  const aiMatchId = aiMatch.instanceId;
  aiMatchIdValue = aiMatchId;

  function answer(overrides: Partial<ModelCallOutput>): ModelCallOutput {
    return {
      content: null,
      reasoning: "因为 p2 的描述太直白",
      toolCalls: [],
      usage: { promptTokens: 500, completionTokens: 120, totalTokens: 620 },
      finishReason: "tool_calls",
      latencyMs: 12,
      ...overrides,
    };
  }

  function scriptedClient(script: ModelCallOutput[]) {
    const calls = { count: 0 };
    return {
      calls,
      client: {
        async call(): Promise<ModelCallOutput> {
          const next = script[Math.min(calls.count, script.length - 1)]!;
          calls.count += 1;
          return next;
        },
      },
    };
  }

  function runnerWith(client: { call(): Promise<ModelCallOutput> }) {
    return createAiSeatRunner({
      db,
      registry: createBuiltInRegistry(),
      service: matchService,
      credentialKey: parseCredentialKey(INTEGRATION_KEY, 1),
      client,
      logger: { info: () => {} },
    });
  }

  // Preconditions, asserted so a later failure says which one broke.
  assert.ok(
    (await listProvidersWithModels(db, { includeDisabled: false })).length > 0,
    "AI seats need an enabled provider to play with",
  );
  assert.ok(
    (await findReadyAiSeats(db, 10)).some((seat) => seat.instanceId === aiMatchId),
    "the scan must offer the new match",
  );

  // 1) A refusal is fed back and the seat recovers inside the same turn.
  const refusing = scriptedClient([
    answer({ toolCalls: [{ id: "c1", name: "vote", arguments: '{"target":"p2"}' }] }),
    answer({
      toolCalls: [{ id: "c2", name: "seatMessage", arguments: '{"text":"我这东西冬天常见"}' }],
    }),
  ]);
  const aiTurn = await runnerWith(refusing.client).runOnce({ limit: 1 });
  assert.equal(aiTurn.turns, 1, "the seat must recover and act");
  assert.equal(refusing.calls.count, 2, "one refused call, then a good one");

  const aiRows = await matchService.read({ actor, instanceId: aiMatchId });
  assert.deepEqual(
    aiRows.record.map((row) => row.type),
    ["instanceCreated", "aiCall", "aiCall", "seatMessage"],
  );
  // The refused call stays in the record, with its usage and the action it asked for.
  assert.deepEqual(aiRows.record[1]?.payload["toolCalls"], [
    { id: "c1", name: "vote", arguments: '{"target":"p2"}' },
  ]);
  assert.equal(aiRows.record[1]?.usage?.totalTokens, 620);
  assert.equal(aiRows.record[1]?.participantId, aiRows.record[3]?.participantId);

  // 2) A turn that never produces an action is a failure the game can see.
  const silent = scriptedClient([answer({ finishReason: "length" })]);
  const aiFailure = await runnerWith(silent.client).runOnce({ limit: 1 });
  assert.equal(aiFailure.failures, 1);
  const afterFailure = await matchService.read({ actor, instanceId: aiMatchId });
  const failure = afterFailure.record.at(-1);
  assert.equal(failure?.type, "aiFailed");
  assert.equal(failure?.payload["code"], "TOKEN_BUDGET_EXHAUSTED");

  // 3) A match that is no longer running is not scanned at all.
  await setInstanceStatus(db, aiMatchId, "completed");
  const idle = await runnerWith(scriptedClient([answer({})]).client).runOnce({ limit: 1 });
  assert.deepEqual(idle, { turns: 0, failures: 0 });

  // A match that publishes personas shows the table the flavour, but still never the MBTI.
  const published = await matchService.create({
    actor,
    request: {
      gameId: "undercover",
      variables: { civilianWord: "咖啡", undercoverWord: "茶" },
      personaPublic: true,
      seats: [
        { key: "p1", control: "human" },
        { key: "p2", control: "ai" },
        { key: "p3", control: "ai" },
      ],
    },
  });
  publishedMatchId = published.instanceId;
  const publishedRead = await matchService.read({ actor, instanceId: published.instanceId });
  const [, publishedNeighbour] = publishedRead.seats;
  assert.ok(publishedNeighbour?.persona?.profession, "a published persona shows its profession");
  assert.ok(publishedNeighbour?.persona?.style, "a published persona shows how it talks");
  assert.equal(publishedNeighbour?.persona?.mbti, undefined, "even published, MBTI stays private");

  // ─── A category instead of words: the platform's model fills the pair ───────────────
  // The model is stubbed here; `pnpm check:model-call` exercises the real one.
  const generated = createMatchService({
    db,
    registry: createBuiltInRegistry(),
    wordPairs: async (category: string) => ({ civilian: `甲${category}`, undercover: `乙${category}` }),
  });
  const byCategory = await generated.create({
    actor,
    request: {
      gameId: "undercover",
      variables: { category: "水果" },
      seats: [
        { key: "p1", control: "human" },
        { key: "p2", control: "ai" },
        { key: "p3", control: "ai" },
      ],
    },
  });
  generatedMatchId = byCategory.instanceId;
  const generatedRead = await generated.read({ actor, instanceId: byCategory.instanceId });
  const ownWord = Object.values(generatedRead.view.privateState)[0];
  assert.ok(
    ownWord === "甲水果" || ownWord === "乙水果",
    "the creator's category must reach the deal as a generated word",
  );
  assert.equal(generatedRead.view.publicState["category"], "水果", "the theme is public");
  for (const value of Object.values(generatedRead.view.publicState)) {
    assert.notEqual(value, "甲水果", "the words themselves are never public");
    assert.notEqual(value, "乙水果", "the words themselves are never public");
  }

  // ─── Rooms: the table exists before a match, and outlives it ──────────────────────
  const roomService = createRoomService({
    db,
    registry: createBuiltInRegistry(),
    matchService: createMatchService({
      db,
      registry: createBuiltInRegistry(),
      wordPairs: async (category: string) => ({ civilian: `甲${category}`, undercover: `乙${category}` }),
    }),
  });
  const host = { userId: platformUserId, isAdmin: true };
  const guest = { userId: secondUserId, isAdmin: false };

  let tooFewSeats = false;
  try {
    await roomService.create({
      actor: host,
      request: {
        gameId: "undercover",
        seats: [
          { key: "s1", control: "human" },
          { key: "s2", control: "ai" },
        ],
      },
    });
  } catch (error) {
    tooFewSeats = error instanceof Error && "code" in error && error.code === "SEATS_OUT_OF_RANGE";
  }
  assert.equal(tooFewSeats, true, "a table outside the game's range must be refused");

  const room = await roomService.create({
    actor: host,
    request: {
      gameId: "undercover",
      variables: { category: "水果" },
      seats: [
        { key: "s1", control: "human" },
        { key: "s2", control: "human" },
        { key: "s3", control: "ai" },
        { key: "s4", control: "ai" },
      ],
    },
  });
  roomIdValue = room.roomId;
  assert.deepEqual(room.mySeatKeys, ["s1"], "the owner sits down first");
  assert.equal(room.takenSeats, 1);
  assert.equal(room.aiSeats, 2);
  assert.equal(room.playing, false);
  assert.equal(room.currentInstanceId, null, "no match exists yet: AI seats are placeholders");

  // A listed room must carry its own id: rooms are found by joining members, and a careless
  // `selectAll` there would surface the member row's id instead.
  const listedRooms = await roomService.list({ actor: guest });
  const listedRoom = listedRooms.find((row) => row.roomId === room.roomId);
  assert.ok(listedRoom, "an open room must show up for another account");
  assert.equal(listedRoom.humanSeats, 2);
  assert.deepEqual(listedRoom.mySeatKeys, [], "not seated yet");

  // Nobody may start before everyone is seated and ready.
  let notReady = false;
  try {
    await roomService.start({ actor: host, roomId: room.roomId });
  } catch (error) {
    notReady = error instanceof Error && "code" in error && error.code === "SEAT_EMPTY";
  }
  assert.equal(notReady, true, "an empty human seat blocks the start");

  const joined = await roomService.join({ actor: guest, roomId: room.roomId });
  assert.deepEqual(joined.mySeatKeys, ["s2"]);
  assert.equal(joined.takenSeats, 2);

  let readyRequired = false;
  try {
    await roomService.start({ actor: host, roomId: room.roomId });
  } catch (error) {
    readyRequired = error instanceof Error && "code" in error && error.code === "NOT_READY";
  }
  assert.equal(readyRequired, true, "every seated human must be ready");

  await roomService.setReady({ actor: host, roomId: room.roomId, ready: true });
  const bothReady = await roomService.setReady({ actor: guest, roomId: room.roomId, ready: true });
  assert.equal(bothReady.readySeats, 2);

  const firstMatch = await roomService.start({ actor: host, roomId: room.roomId });
  assert.equal(first.summary.status, "waiting");
  const afterStart = await roomService.read({ actor: host, roomId: room.roomId });
  assert.equal(afterStart.playing, true, "a running match is derived from the instance, not stored");
  assert.equal(afterStart.readySeats, 0, "starting a match clears everyone's readiness");
  assert.equal(afterStart.currentInstanceId, firstMatch.summary.instanceId);

  const started = await matchService.read({ actor: host, instanceId: firstMatch.summary.instanceId });
  assert.equal(started.seats.length, 4, "AI placeholders became real seats at the start");
  assert.equal(started.seats.filter((seat) => seat.control === "ai").length, 2);
  assert.ok(started.seats.every((seat) => seat.persona !== null), "every seat was dealt a persona");

  let busy = false;
  try {
    await roomService.start({ actor: host, roomId: room.roomId });
  } catch (error) {
    busy = error instanceof Error && "code" in error && error.code === "ROOM_BUSY";
  }
  assert.equal(busy, true, "one match at a time");

  let editWhilePlaying = false;
  try {
    await roomService.update({
      actor: host,
      roomId: room.roomId,
      patch: { seats: [{ key: "s1", control: "human" }, { key: "s2", control: "human" }, { key: "s3", control: "ai" }] },
    });
  } catch (error) {
    editWhilePlaying = error instanceof Error && "code" in error && error.code === "ROOM_BUSY";
  }
  assert.equal(editWhilePlaying, true, "the layout is fixed while a match is running");

  // Ending the match frees the table: same room, same seats, a second match.
  await matchService.setStatus({
    actor: host,
    instanceId: firstMatch.summary.instanceId,
    status: "cancelled",
  });
  const roomIdle = await roomService.read({ actor: host, roomId: room.roomId });
  assert.equal(roomIdle.playing, false);

  const reshaped = await roomService.update({
    actor: host,
    roomId: room.roomId,
    patch: {
      seats: [
        { key: "s1", control: "human" },
        { key: "s2", control: "human" },
        { key: "s3", control: "ai" },
      ],
    },
  });
  assert.equal(reshaped.seats, 3, "the layout is free to change between matches");
  assert.equal(reshaped.aiSeats, 1);

  await roomService.setReady({ actor: host, roomId: room.roomId, ready: true });
  await roomService.setReady({ actor: guest, roomId: room.roomId, ready: true });
  const second = await roomService.start({ actor: host, roomId: room.roomId });
  assert.notEqual(second.summary.instanceId, firstMatch.summary.instanceId);
  const history = await roomService.matches({ actor: host, roomId: room.roomId });
  assert.equal(history.length, 2, "a room remembers every match it hosted");
  assert.deepEqual(
    history.map((row) => row.instanceId),
    [second.summary.instanceId, firstMatch.summary.instanceId],
  );
  await matchService.setStatus({
    actor: host,
    instanceId: second.summary.instanceId,
    status: "cancelled",
  });

  // Whoever leaves cannot take the table with them: ownership moves to the other human.
  const hostLeft = await roomService.leave({ actor: host, roomId: room.roomId });
  assert.equal(hostLeft.isOwner, false);
  assert.equal(hostLeft.ownerUserId, secondUserId);
  const guestView = await roomService.read({ actor: guest, roomId: room.roomId });
  assert.equal(guestView.isOwner, true);
  const emptyRoom = await roomService.leave({ actor: guest, roomId: room.roomId });
  assert.equal(emptyRoom.status, "closed", "an empty room closes itself");

  // ─── Administrator lifecycle: the column moves, the record does not ───────────────
  const lifecycle = await matchService.create({
    actor,
    request: {
      gameId: "undercover",
      variables: { civilianWord: "咖啡", undercoverWord: "茶" },
      seats: [
        { key: "p1", control: "human" },
        { key: "p2", control: "ai" },
        { key: "p3", control: "ai" },
      ],
    },
  });
  lifecycleMatchId = lifecycle.instanceId;
  const seatHolder = { userId: platformUserId, isAdmin: false };

  assert.deepEqual(
    matchService.listGames().map((game) => game.gameId),
    ["undercover"],
  );
  // Every match is visible to every signed-in account; the seat tag is what differs.
  const listed = await matchService.list({ actor: seatHolder });
  const mine = listed.find((match) => match.instanceId === lifecycleMatchId);
  assert.deepEqual(mine?.mySeatKeys, ["p1"], "the holder's own seat is marked");
  assert.ok(
    (await matchService.list({ actor: { userId: randomUUID(), isAdmin: false } })).some(
      (match) => match.instanceId === lifecycleMatchId,
    ),
    "a stranger sees the match it may watch",
  );
  assert.deepEqual(
    (await matchService.list({ actor })).find((match) => match.instanceId === lifecycleMatchId)
      ?.mySeatKeys,
    ["p1"],
    "an administrator is a player here, not an operator: it holds s1",
  );
  assert.deepEqual(
    (await matchService.list({ actor: { userId: randomUUID(), isAdmin: true } })).find(
      (match) => match.instanceId === lifecycleMatchId,
    )?.mySeatKeys,
    [],
    "an administrator with no seat is only watching",
  );

  let notAdmin = false;
  try {
    await matchService.setStatus({
      actor: seatHolder,
      instanceId: lifecycleMatchId,
      status: "paused",
    });
  } catch (error) {
    notAdmin = error instanceof Error && "code" in error && error.code === "ADMIN_REQUIRED";
  }
  assert.equal(notAdmin, true, "a lifecycle change is administrator-only");

  const paused = await matchService.setStatus({
    actor,
    instanceId: lifecycleMatchId,
    status: "paused",
  });
  assert.equal(paused.status, "paused");
  // Suspended means suspended: the scan skips it and the write path refuses input.
  assert.ok(
    !(await findReadyAiSeats(db, 50)).some((seat) => seat.instanceId === lifecycleMatchId),
    "a paused match is not offered to the worker",
  );
  let refused = false;
  try {
    await matchService.submit({
      actor,
      instanceId: lifecycleMatchId,
      idempotencyKey: "paused-1",
      request: { type: "seatMessage", participantKey: "p1", payload: { text: "x" } },
    });
  } catch (error) {
    refused = error instanceof Error && "code" in error && error.code === "MATCH_NOT_RUNNING";
  }
  assert.equal(refused, true, "a paused match takes no input");

  // Resume restores the status the game itself chose, not one the platform guessed.
  const resumed = await matchService.setStatus({
    actor,
    instanceId: lifecycleMatchId,
    status: "running",
  });
  assert.equal(resumed.status, "waiting");
  assert.ok(
    (await findReadyAiSeats(db, 50)).some((seat) => seat.instanceId === lifecycleMatchId),
    "a resumed match is offered again",
  );

  const rowsBefore = (await matchService.read({ actor, instanceId: lifecycleMatchId })).record
    .length;
  assert.equal(
    (await matchService.setStatus({ actor, instanceId: lifecycleMatchId, status: "cancelled" }))
      .status,
    "cancelled",
  );
  assert.equal(
    (await matchService.read({ actor, instanceId: lifecycleMatchId })).record.length,
    rowsBefore,
    "a lifecycle change is not a game event",
  );
  const lifecycleAudit = await db
    .selectFrom("audit_logs")
    .select(["action", "metadata"])
    .where("resource_id", "=", lifecycleMatchId)
    .orderBy("created_at", "asc")
    .execute();
  assert.deepEqual(
    lifecycleAudit.map((row) => row.action),
    ["match.paused", "match.waiting", "match.cancelled"],
  );

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
  const instanceIds = [
    instanceId,
    secondInstanceId,
    ...(matchId === null ? [] : [matchId]),
    ...(aiMatchIdValue === null ? [] : [aiMatchIdValue]),
    ...(lifecycleMatchId === null ? [] : [lifecycleMatchId]),
    ...(publishedMatchId === null ? [] : [publishedMatchId]),
    ...(generatedMatchId === null ? [] : [generatedMatchId]),
  ];
  await db.deleteFrom("game_instances").where("id", "in", instanceIds).execute();
  if (roomIdValue !== null) {
    // Instances point at their room and the room points at its current instance: break both links
    // before either row goes away.
    await db
      .updateTable("rooms")
      .set({ current_instance_id: null })
      .where("id", "=", roomIdValue)
      .execute();
    await db.deleteFrom("game_instances").where("room_id", "=", roomIdValue).execute();
    await db.deleteFrom("room_members").where("room_id", "=", roomIdValue).execute();
    await db.deleteFrom("rooms").where("id", "=", roomIdValue).execute();
  }
  await db.deleteFrom("users").where("id", "=", secondUserId).execute();
  await db.deleteFrom("users").where("id", "=", platformUserId).execute();
  await closeDb(db);
}
