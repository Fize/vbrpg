import {
  createDb,
  withTenantContext,
  type DbExecutor,
  type JsonObject,
} from "@vbrpg/db";
import type { GameEvent, GameState, ExternalCommand } from "@vbrpg/contracts";
import { dispatchEvent, type CompiledGame } from "@vbrpg/workflow-engine";
import { parseGameState } from "@vbrpg/contracts";

type PlatformDb = ReturnType<typeof createDb>;

export interface DispatchContext {
  tenantId: string;
}

export interface DispatchResult {
  state: GameState;
  commands: ExternalCommand[];
  replayed: boolean;
}

function asJsonObject(value: unknown): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Expected a JSON object");
  }
  return value as JsonObject;
}

async function persistCommands(
  db: DbExecutor,
  context: DispatchContext,
  commands: ExternalCommand[],
): Promise<void> {
  for (const command of commands) {
    if (command.type === "aiGenerate") {
      await db.insertInto("pending_commands").values({
        id: command.commandId,
        tenant_id: context.tenantId,
        instance_id: command.instanceId,
        command_id: command.commandId,
        command_type: command.type,
        payload: command.input,
        max_attempts: command.maxAttempts,
      }).onConflict((conflict) => conflict.columns(["tenant_id", "instance_id", "command_id"]).doNothing()).execute();
    } else if (command.type === "schedule") {
      await db.insertInto("scheduled_jobs").values({
        id: command.commandId,
        tenant_id: context.tenantId,
        instance_id: command.instanceId,
        job_key: command.commandId,
        job_type: command.job,
        payload: { commandId: command.commandId },
        run_at: new Date(command.runAtMs),
      }).onConflict((conflict) => conflict.columns(["tenant_id", "job_key"]).doNothing()).execute();
    } else {
      await db.insertInto("outbox_events").values({
        id: `${command.instanceId}:${command.commandId}`,
        tenant_id: context.tenantId,
        aggregate_type: "game_instance",
        aggregate_id: command.instanceId,
        event_type: command.eventName,
        payload: command.payload,
      }).onConflict((conflict) => conflict.columns(["tenant_id", "id"]).doNothing()).execute();
    }
  }
}

export async function dispatchGameEvent(
  db: PlatformDb,
  context: DispatchContext,
  compiled: CompiledGame,
  event: GameEvent,
): Promise<DispatchResult> {
  return withTenantContext(db, context, async (transaction) => {
    const instance = await transaction
      .selectFrom("game_instances")
      .selectAll()
      .where("tenant_id", "=", context.tenantId)
      .where("id", "=", event.instanceId)
      .forUpdate()
      .executeTakeFirst();
    if (!instance) throw new Error("Game instance not found");

    const existing = await transaction
      .selectFrom("game_events")
      .selectAll()
      .where("tenant_id", "=", context.tenantId)
      .where("instance_id", "=", event.instanceId)
      .where("idempotency_key", "=", event.idempotencyKey)
      .executeTakeFirst();
    if (existing) {
      return {
        state: parseGameState(instance.state_json),
        commands: [],
        replayed: true,
      };
    }
    if (event.sequence !== instance.current_sequence + 1) {
      throw new Error("Event sequence does not match the locked instance");
    }

    const result = dispatchEvent(compiled, parseGameState(instance.state_json), event);
    await transaction.insertInto("game_events").values({
      id: event.eventId,
      tenant_id: context.tenantId,
      instance_id: event.instanceId,
      sequence: event.sequence,
      type: event.type,
      actor_user_id: event.actor?.userId ?? null,
      idempotency_key: event.idempotencyKey,
      occurred_at: new Date(event.occurredAtMs),
      payload: event.payload,
    }).execute();
    await transaction.updateTable("game_instances").set({
      status: result.state.status,
      current_sequence: result.state.sequence,
      state_json: asJsonObject(result.state),
      completed_at: ["completed", "cancelled"].includes(result.state.status) ? new Date() : null,
      updated_at: new Date(),
    }).where("tenant_id", "=", context.tenantId).where("id", "=", event.instanceId).execute();
    await persistCommands(transaction, context, result.commands);
    return { state: result.state, commands: result.commands, replayed: false };
  });
}
