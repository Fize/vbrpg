import { Kysely, PostgresDialect } from "kysely";
import { Pool } from "pg";
import type { Database } from "./types.js";

export interface DbOptions {
  databaseUrl: string;
  maxConnections?: number;
}

export function createDb(options: DbOptions): Kysely<Database> {
  const pool = new Pool({
    connectionString: options.databaseUrl,
    max: options.maxConnections ?? 10,
  });
  return new Kysely<Database>({
    dialect: new PostgresDialect({ pool }),
  });
}

export async function closeDb(db: Kysely<Database>): Promise<void> {
  await db.destroy();
}
