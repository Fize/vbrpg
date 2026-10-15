import type { Kysely, Selectable, Transaction } from "kysely";
import type { Database, GameInstancesTable, JsonObject } from "./types.js";

export type DbExecutor = Kysely<Database> | Transaction<Database>;

export async function getGameInstance(
  db: DbExecutor,
  instanceId: string,
): Promise<Selectable<GameInstancesTable> | undefined> {
  return db
    .selectFrom("game_instances")
    .selectAll()
    .where("id", "=", instanceId)
    .executeTakeFirst();
}

export async function createGameInstance(
  db: DbExecutor,
  input: {
    id: string;
    gameVersionId: string;
    status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled";
    currentSequence: number;
    stateJson: JsonObject;
  },
): Promise<void> {
  await db
    .insertInto("game_instances")
    .values({
      id: input.id,
      game_version_id: input.gameVersionId,
      status: input.status,
      current_sequence: input.currentSequence,
      state_json: input.stateJson,
    })
    .execute();
}

/** Platform-level lifecycle change: pause, resume, cancel. Never a game event. */
export async function setInstanceStatus(
  db: DbExecutor,
  instanceId: string,
  status: "created" | "running" | "waiting" | "paused" | "completed" | "cancelled",
): Promise<boolean> {
  const result = await db
    .updateTable("game_instances")
    .set({ status, updated_at: new Date() })
    .where("id", "=", instanceId)
    .executeTakeFirst();
  return Number(result.numUpdatedRows ?? 0) > 0;
}
