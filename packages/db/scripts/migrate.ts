import { promises as fs } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { Migrator, sql, type MigrationProvider } from "kysely";
import { closeDb, createDb } from "../src/client.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  throw new Error("DATABASE_URL is required to run platform migrations");
}

const db = createDb({ databaseUrl });
const migrationFolder = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../migrations",
);
const sqlMigrationProvider: MigrationProvider = {
  async getMigrations() {
    const files = (await fs.readdir(migrationFolder))
      .filter((fileName) => fileName.endsWith(".sql"))
      .sort();
    return Object.fromEntries(
      await Promise.all(
        files.map(async (fileName) => {
          const contents = await fs.readFile(path.join(migrationFolder, fileName), "utf8");
          return [fileName.slice(0, -4), { up: async (migrationDb) => { await sql.raw(contents).execute(migrationDb); } }];
        }),
      ),
    );
  },
};
const migrator = new Migrator({
  db,
  provider: sqlMigrationProvider,
});

try {
  const result = await migrator.migrateToLatest();
  for (const migration of result.results ?? []) {
    console.log(JSON.stringify({ migration: migration.migrationName, status: migration.status }));
  }
  if (result.error) {
    throw result.error;
  }
} finally {
  await closeDb(db);
}
