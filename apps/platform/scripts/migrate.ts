import { promises as fs } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { Migrator, sql, type Migration, type MigrationProvider } from "kysely";
import { closeDb, createDb } from "../src/server/db/client.js";
import { downMigrationFileName, selectUpMigrationFiles } from "../src/server/db/migrations.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  throw new Error("DATABASE_URL is required to run platform migrations");
}

const downSteps = process.argv.includes("--down")
  ? Number(process.argv.find((argument) => argument.startsWith("--steps="))?.slice(8) ?? 1)
  : 0;
if (!Number.isInteger(downSteps) || downSteps < 0) {
  throw new Error("--steps must be a non-negative integer");
}

const db = createDb({ databaseUrl });
const migrationFolder = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../migrations");

type MigrationRunner = (migrationDb: Parameters<Migration["up"]>[0]) => Promise<void>;

function toRunner(contents: string): MigrationRunner {
  return async (migrationDb) => {
    await sql.raw(contents).execute(migrationDb);
  };
}

const sqlMigrationProvider: MigrationProvider = {
  async getMigrations() {
    const files = selectUpMigrationFiles(await fs.readdir(migrationFolder));
    const entries = await Promise.all(
      files.map(async (fileName): Promise<[string, Migration]> => {
        const name = fileName.slice(0, -4);
        const up = toRunner(await fs.readFile(path.join(migrationFolder, fileName), "utf8"));
        let down: MigrationRunner | undefined;
        try {
          down = toRunner(
            await fs.readFile(path.join(migrationFolder, downMigrationFileName(fileName)), "utf8"),
          );
        } catch {
          down = undefined;
        }
        return [name, down ? { up, down } : { up }];
      }),
    );
    return Object.fromEntries(entries);
  },
};

function report(
  results: ReadonlyArray<{ migrationName: string; status: string }> | undefined,
): void {
  for (const migration of results ?? []) {
    console.log(JSON.stringify({ migration: migration.migrationName, status: migration.status }));
  }
}

const migrator = new Migrator({ db, provider: sqlMigrationProvider });

try {
  if (downSteps === 0) {
    const result = await migrator.migrateToLatest();
    report(result.results);
    if (result.error) throw result.error;
  } else {
    for (let step = 0; step < downSteps; step += 1) {
      const result = await migrator.migrateDown();
      report(result.results);
      if (result.error) throw result.error;
      if (!result.results?.length) break;
    }
  }
} finally {
  await closeDb(db);
}
