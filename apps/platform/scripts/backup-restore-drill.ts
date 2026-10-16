import { execFile } from "node:child_process";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { Client } from "pg";
import { sql, type Kysely } from "kysely";
import { closeDb, createDb, type Database } from "../src/server/db/index.js";
import { createMatchService, type MatchActor } from "../src/server/match/service.js";
import { createBuiltInRegistry } from "../src/server/games/index.js";

/**
 * Backup and restore drill: dump the source database, restore it into a scratch one, and then read
 * the copy the way the application does. A dump nobody has ever restored is a hope, not a backup.
 *
 *   DATABASE_URL=…  DRILL_DATABASE_URL=…/<name containing "drill">  pnpm backup-restore-drill
 *
 * The scratch database is dropped and recreated by the script, so its name must contain `drill`:
 * that is the guard against pointing it at something real by accident.
 */

const run = promisify(execFile);
const SAMPLE_TABLES = [
  "users",
  "auth_sessions",
  "providers",
  "provider_models",
  "game_instances",
  "game_participants",
  "game_events",
  "audit_logs",
  "kysely_migration",
] as const;

const sourceUrl = process.env.DATABASE_URL;
const targetUrl = process.env.DRILL_DATABASE_URL;
if (!sourceUrl || !targetUrl) {
  console.error("DATABASE_URL and DRILL_DATABASE_URL are required");
  process.exit(1);
}

const source = new URL(sourceUrl);
const target = new URL(targetUrl);
const targetName = target.pathname.replace(/^\//, "");
if (!targetName.includes("drill")) {
  console.error(`The drill database name must contain "drill", refusing to touch ${targetName}`);
  process.exit(1);
}
if (targetName === source.pathname.replace(/^\//, "")) {
  console.error("The drill database must not be the source database");
  process.exit(1);
}

/**
 * `pg_dump`/`pg_restore` may be wrapped (e.g. `docker exec -i <container> pg_dump`). A wrapped tool
 * usually reaches PostgreSQL through a different address than this process does, so the URLs it
 * should use are overridable too.
 */
const pgDump = process.env.PG_DUMP ?? "pg_dump";
const pgRestore = process.env.PG_RESTORE ?? "pg_restore";
const dumpUrl = process.env.PG_DUMP_URL ?? sourceUrl;
const restoreUrl = process.env.PG_RESTORE_URL ?? targetUrl;

function maintenanceUrl(): string {
  const url = new URL(targetUrl as string);
  url.pathname = "/postgres";
  return url.toString();
}

async function recreateTarget(): Promise<void> {
  const client = new Client({ connectionString: maintenanceUrl() });
  await client.connect();
  try {
    await client.query(`drop database if exists "${targetName}" with (force)`);
    await client.query(`create database "${targetName}"`);
  } finally {
    await client.end();
  }
}

async function dropTarget(): Promise<void> {
  const client = new Client({ connectionString: maintenanceUrl() });
  await client.connect();
  try {
    await client.query(`drop database if exists "${targetName}" with (force)`);
  } finally {
    await client.end();
  }
}

async function dumpTo(file: string): Promise<number> {
  const started = Date.now();
  // The redirect happens on this host, so a container-wrapped pg_dump still writes locally.
  await run("/bin/sh", [
    "-c",
    `${pgDump} --format=custom --no-owner --dbname='${dumpUrl}' > '${file}'`,
  ]);
  return Date.now() - started;
}

async function restoreFrom(file: string): Promise<number> {
  const started = Date.now();
  await run("/bin/sh", [
    "-c",
    `${pgRestore} --no-owner --exit-on-error --dbname='${restoreUrl}' < '${file}'`,
  ]);
  return Date.now() - started;
}

async function rowCounts(db: Kysely<Database>): Promise<Record<string, number>> {
  const counts: Record<string, number> = {};
  for (const table of SAMPLE_TABLES) {
    // Table names come from the list above; `sql.table` quotes them, nothing is interpolated raw.
    const result = await sql<{ count: string }>`
      select count(*)::text as count from ${sql.table(table)}
    `.execute(db);
    counts[table] = Number(result.rows[0]?.count ?? 0);
  }
  return counts;
}

/** What the copy must reproduce exactly: the same match, read through the same code path. */
async function sampleMatch(db: Kysely<Database>) {
  const newest = await db
    .selectFrom("game_instances")
    .select(["id", "current_sequence", "status"])
    .orderBy("created_at", "desc")
    .limit(1)
    .executeTakeFirst();
  if (!newest) return null;

  const service = createMatchService({ db, registry: createBuiltInRegistry() });
  const actor: MatchActor = { userId: randomUUID(), isAdmin: false };
  const detail = await service.read({ actor, instanceId: newest.id });
  return {
    instanceId: detail.summary.instanceId,
    sequence: detail.summary.sequence,
    status: detail.summary.status,
    stepId: detail.summary.stepId,
    seats: detail.seats.map((seat) => `${seat.key}:${seat.control}:${seat.status}`),
    events: detail.record.map((row) => `${row.sequence}:${row.type}`),
    totalTokens: detail.record.reduce((sum, row) => sum + (row.usage?.totalTokens ?? 0), 0),
  };
}

const sourceDb = createDb({ databaseUrl: sourceUrl });
const targetDb = createDb({ databaseUrl: targetUrl });
const workDir = await mkdtemp(path.join(tmpdir(), "vbrpg-drill-"));
const dumpFile = path.join(workDir, "backup.pgc");
let exitCode = 0;

try {
  console.log(`Drill: ${source.pathname} -> ${target.pathname}`);

  await recreateTarget();

  const dumpMs = await dumpTo(dumpFile);
  const { size } = await stat(dumpFile);
  console.log(`Dump: ${(size / 1024 / 1024).toFixed(2)} MiB in ${dumpMs} ms`);

  const restoreMs = await restoreFrom(dumpFile);
  console.log(`Restore: ${restoreMs} ms`);

  const sourceCounts = await rowCounts(sourceDb);
  const targetCounts = await rowCounts(targetDb);
  for (const table of SAMPLE_TABLES) {
    if (sourceCounts[table] !== targetCounts[table]) {
      throw new Error(
        `Row count mismatch in ${table}: source ${sourceCounts[table]}, restored ${targetCounts[table]}`,
      );
    }
  }
  console.log(
    `Row counts match across ${SAMPLE_TABLES.length} tables (${Object.values(targetCounts).reduce(
      (sum, count) => sum + count,
      0,
    )} rows).`,
  );

  const sourceMatch = await sampleMatch(sourceDb);
  const targetMatch = await sampleMatch(targetDb);
  if (JSON.stringify(sourceMatch) !== JSON.stringify(targetMatch)) {
    throw new Error("The restored copy does not read back as the same match");
  }
  console.log(
    sourceMatch === null
      ? "No match to compare yet; the copy is schema-complete and empty."
      : `Sample match ${sourceMatch.instanceId} reads back identically: ` +
          `${sourceMatch.events.length} rows, sequence ${sourceMatch.sequence}, ` +
          `${sourceMatch.totalTokens} tokens.`,
  );

  console.log(
    "Drill passed: the backup restores into a usable database, and the application reads it.",
  );
} catch (error) {
  exitCode = 1;
  console.error(`Drill failed: ${error instanceof Error ? error.message : String(error)}`);
} finally {
  await closeDb(sourceDb);
  await closeDb(targetDb);
  await rm(workDir, { recursive: true, force: true });
  if (process.env.DRILL_KEEP === "1") {
    console.log(`DRILL_KEEP=1: leaving ${targetName} in place`);
  } else {
    await dropTarget().catch(() => undefined);
  }
  process.exit(exitCode);
}
