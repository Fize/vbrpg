import { parseGameEvent, parseGameState, type GameEvent, type GameState } from "@vbrpg/contracts";
import { getGameInstance, withTenantContext, type TenantContext } from "@vbrpg/db";
import { compileGameDefinition, type CompiledGame } from "@vbrpg/workflow-engine";
import type { Kysely } from "kysely";
import type { Database } from "@vbrpg/db";

export class RuntimeTaskError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "RuntimeTaskError";
  }
}

export interface LoadedInstance {
  state: GameState;
  currentSequence: number;
  compiled: CompiledGame;
}

/** Both the AI and the timer handler need the same pair: authoritative state plus its definition. */
export async function loadInstanceWithDefinition(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
): Promise<LoadedInstance | undefined> {
  return withTenantContext(db, context, async (transaction) => {
    const instance = await getGameInstance(transaction, context, instanceId);
    if (!instance) return undefined;

    const definitionRow = await transaction
      .selectFrom("workflow_definitions")
      .select(["definition_json"])
      .where("tenant_id", "=", context.tenantId)
      .where("game_version_id", "=", instance.game_version_id)
      .executeTakeFirst();
    if (!definitionRow) {
      throw new RuntimeTaskError(
        "DEFINITION_NOT_FOUND",
        `The game version has no workflow definition: ${instance.game_version_id}`,
      );
    }

    return {
      state: parseGameState(instance.state_json),
      currentSequence: instance.current_sequence,
      compiled: compileGameDefinition(definitionRow.definition_json),
    };
  });
}

export async function loadRecentEvents(
  db: Kysely<Database>,
  context: TenantContext,
  instanceId: string,
  limit: number,
): Promise<GameEvent[]> {
  return withTenantContext(db, context, async (transaction) => {
    const rows = await transaction
      .selectFrom("game_events")
      .selectAll()
      .where("tenant_id", "=", context.tenantId)
      .where("instance_id", "=", instanceId)
      .orderBy("sequence", "desc")
      .limit(limit)
      .execute();
    return rows.reverse().map((row) =>
      parseGameEvent({
        eventId: row.id,
        instanceId: row.instance_id,
        sequence: row.sequence,
        type: row.type,
        actor: row.actor_user_id === null ? null : { userId: row.actor_user_id },
        occurredAtMs: row.occurred_at.getTime(),
        idempotencyKey: row.idempotency_key,
        payload: row.payload,
      }),
    );
  });
}
