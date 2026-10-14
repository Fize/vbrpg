import { randomUUID } from "node:crypto";
import { parseGameEvent, parseGameState, type GameEvent } from "@vbrpg/contracts";
import {
  getAgentModelBinding,
  getGameInstance,
  getProviderModelWithProvider,
  withTenantContext,
  type DbExecutor,
  type JsonObject,
  type TenantContext,
} from "@vbrpg/db";
import { compileGameDefinition, type CompiledGame } from "@vbrpg/workflow-engine";
import type { Kysely } from "kysely";
import type { Database } from "@vbrpg/db";
import {
  buildGameContext,
  createOpenAiCompatibleClient,
  estimateTokens,
  type AiClient,
  type AiConfig,
} from "./ai.js";
import { openCredential, parseCredentialKey, type CredentialKey } from "./secret-box.js";
import { dispatchGameEvent } from "./game-dispatch.js";

const DEFAULT_MAX_TIMEOUT_MS = 30_000;
const DEFAULT_RECENT_EVENT_LIMIT = 50;
const DEFAULT_CONTEXT_WINDOW_TOKENS = 262_144;
const DEFAULT_MAX_INPUT_TOKENS = 196_608;
const DEFAULT_RESERVE_OUTPUT_TOKENS = 16_384;

export interface ClaimedCommand {
  id: string;
  tenant_id: string;
  instance_id: string;
  command_id: string;
  command_type: string;
  payload: unknown;
  attempts: number;
  max_attempts: number;
}

export interface AiCommandDependencies {
  credentialKeyEncoded: string;
  maxTimeoutMs?: number;
  recentEventLimit?: number;
  contextWindowTokens?: number;
  maxInputTokens?: number;
  reserveOutputTokens?: number;
  now?: () => Date;
  /** Test seam: builds the provider client from the resolved binding. */
  createClient?: (config: AiConfig) => AiClient;
}

export type AiCommandOutcome = "completed" | "fallback" | "duplicate" | "skipped";

export interface AiCommandResult {
  outcome: AiCommandOutcome;
  provider?: string;
  model?: string;
  reason?: string;
}

interface AiNodePlan {
  compiled: CompiledGame;
  nodeId: string;
  agentId: string;
  input: Record<string, unknown>;
  timeoutMs: number;
  maxAttempts: number;
  sequence: number;
  state: ReturnType<typeof parseGameState>;
  recentEvents: GameEvent[];
}

export class AiCommandError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "AiCommandError";
  }
}

function asInputRecord(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new AiCommandError("INVALID_COMMAND_PAYLOAD", "AI command payload must be an object");
  }
  return value as Record<string, unknown>;
}

function positiveInteger(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : fallback;
}

function toJsonObject(value: Record<string, unknown>): JsonObject {
  return value as JsonObject;
}

async function loadPlan(
  db: Kysely<Database>,
  context: TenantContext,
  command: ClaimedCommand,
  recentEventLimit: number,
): Promise<AiNodePlan | undefined> {
  return withTenantContext(db, context, async (transaction) => {
    const instance = await getGameInstance(transaction, context, command.instance_id);
    if (!instance) {
      throw new AiCommandError("INSTANCE_NOT_FOUND", "The instance no longer exists");
    }

    const state = parseGameState(instance.state_json);
    if (state.waiting?.kind !== "ai") {
      return undefined;
    }

    const definitionRow = await transaction
      .selectFrom("workflow_definitions")
      .select(["definition_json"])
      .where("tenant_id", "=", context.tenantId)
      .where("game_version_id", "=", instance.game_version_id)
      .executeTakeFirst();
    if (!definitionRow) {
      throw new AiCommandError("DEFINITION_NOT_FOUND", "The game version has no workflow definition");
    }

    const compiled = compileGameDefinition(definitionRow.definition_json);
    const nodeId = state.waiting.nodeId;
    const node = compiled.nodes.get(nodeId);
    if (!node) {
      throw new AiCommandError("NODE_NOT_FOUND", `Waiting node is missing from the definition: ${nodeId}`);
    }
    if (node.type !== "aiGenerate") {
      throw new AiCommandError("NODE_NOT_AI", `Waiting node is not an AI node: ${nodeId}`);
    }

    const config = node.config as Record<string, unknown>;
    const agentId = typeof config.agentId === "string" ? config.agentId : "";
    if (agentId === "") {
      throw new AiCommandError("AGENT_MISSING", `AI node ${nodeId} declares no agent`);
    }
    const resultKey = config.resultKey;
    if (typeof resultKey !== "string" || resultKey === "") {
      throw new AiCommandError("RESULT_KEY_MISSING", `AI node ${nodeId} declares no resultKey`);
    }

    const rows = await transaction
      .selectFrom("game_events")
      .selectAll()
      .where("tenant_id", "=", context.tenantId)
      .where("instance_id", "=", command.instance_id)
      .orderBy("sequence", "desc")
      .limit(recentEventLimit)
      .execute();

    return {
      compiled,
      nodeId,
      agentId,
      input: asInputRecord(command.payload),
      timeoutMs: positiveInteger(config.timeoutMs, DEFAULT_MAX_TIMEOUT_MS),
      maxAttempts: positiveInteger(command.max_attempts, 1),
      sequence: instance.current_sequence + 1,
      state,
      recentEvents: rows.reverse().map((row) =>
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
      ),
    };
  });
}

interface UsageFields {
  instanceId: string;
  provider: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  metadata: Record<string, unknown>;
}

async function recordUsage(db: DbExecutor, context: TenantContext, fields: UsageFields): Promise<void> {
  await db
    .insertInto("ai_usage_ledger")
    .values({
      id: randomUUID(),
      tenant_id: context.tenantId,
      instance_id: fields.instanceId,
      actor_user_id: null,
      provider: fields.provider,
      model: fields.model,
      input_tokens: fields.inputTokens,
      output_tokens: fields.outputTokens,
      cost_minor_units: "0",
      metadata: toJsonObject(fields.metadata),
    })
    .execute();
}

interface OutcomeEventFields {
  type: "aiResultReceived" | "aiFailed";
  payload: Record<string, unknown>;
  suffix: string;
  now: Date;
}

async function submitOutcomeEvent(
  db: Kysely<Database>,
  context: TenantContext,
  plan: AiNodePlan,
  fields: OutcomeEventFields,
): Promise<AiCommandOutcome> {
  const event: GameEvent = parseGameEvent({
    eventId: `${plan.state.instanceId}:${plan.sequence}:${fields.suffix}`,
    instanceId: plan.state.instanceId,
    sequence: plan.sequence,
    type: fields.type,
    actor: null,
    occurredAtMs: fields.now.getTime(),
    idempotencyKey: `${plan.state.instanceId}:${plan.nodeId}:${plan.sequence}:${fields.suffix}`,
    payload: fields.payload,
  });

  const result = await dispatchGameEvent(db, context, plan.compiled, event);
  if (result.replayed) return "duplicate";
  return fields.type === "aiFailed" ? "fallback" : "completed";
}

interface FallbackFields {
  reason: string;
  provider?: string;
  model?: string;
}

/** Terminal path: the workflow leaves the AI node through its declared fallback branch. */
async function failWithFallback(
  db: Kysely<Database>,
  context: TenantContext,
  plan: AiNodePlan,
  command: ClaimedCommand,
  now: Date,
  fields: FallbackFields,
): Promise<AiCommandResult> {
  const outcome = await submitOutcomeEvent(db, context, plan, {
    type: "aiFailed",
    payload: toJsonObject({
      reason: fields.reason,
      attempts: command.attempts,
      nodeId: plan.nodeId,
      agentId: plan.agentId,
    }),
    suffix: "ai-failed",
    now,
  });

  if (fields.provider !== undefined && fields.model !== undefined) {
    await recordUsage(db, context, {
      instanceId: plan.state.instanceId,
      provider: fields.provider,
      model: fields.model,
      inputTokens: 0,
      outputTokens: 0,
      metadata: {
        commandId: command.command_id,
        nodeId: plan.nodeId,
        agentId: plan.agentId,
        attempts: command.attempts,
        outcome,
        reason: fields.reason,
      },
    });
  }

  return {
    outcome,
    ...(fields.provider === undefined ? {} : { provider: fields.provider }),
    ...(fields.model === undefined ? {} : { model: fields.model }),
    reason: fields.reason,
  };
}

export async function runAiCommand(
  db: Kysely<Database>,
  context: TenantContext,
  command: ClaimedCommand,
  dependencies: AiCommandDependencies,
): Promise<AiCommandResult> {
  if (command.command_type !== "aiGenerate") {
    throw new AiCommandError("UNSUPPORTED_COMMAND", `Unsupported command type: ${command.command_type}`);
  }

  const now = dependencies.now ?? (() => new Date());
  const maxTimeoutMs = dependencies.maxTimeoutMs ?? DEFAULT_MAX_TIMEOUT_MS;
  const maxInputTokens = dependencies.maxInputTokens ?? DEFAULT_MAX_INPUT_TOKENS;
  const buildClient = dependencies.createClient ?? createOpenAiCompatibleClient;

  const plan = await loadPlan(db, context, command, dependencies.recentEventLimit ?? DEFAULT_RECENT_EVENT_LIMIT);
  if (!plan) {
    return { outcome: "skipped", reason: "INSTANCE_NOT_WAITING_FOR_AI" };
  }

  const binding = await getAgentModelBinding(db, context, {
    gameVersionId: plan.state.gameVersionId,
    agentId: plan.agentId,
  });
  if (!binding) {
    return failWithFallback(db, context, plan, command, now(), { reason: "AGENT_NOT_BOUND" });
  }

  const catalog = await getProviderModelWithProvider(db, binding.providerModelId);
  if (!catalog || !catalog.provider.enabled || !catalog.model.enabled) {
    return failWithFallback(db, context, plan, command, now(), {
      reason: catalog ? "MODEL_DISABLED" : "MODEL_NOT_FOUND",
    });
  }

  const provider = catalog.provider;
  const model = catalog.model;

  let client: AiClient;
  try {
    const key: CredentialKey = parseCredentialKey(
      dependencies.credentialKeyEncoded,
      provider.credential_key_version,
    );
    client = buildClient({
      apiKey: openCredential(
        {
          credential_ciphertext: provider.credential_ciphertext,
          credential_nonce: provider.credential_nonce,
          credential_tag: provider.credential_tag,
          credential_key_version: provider.credential_key_version,
        },
        provider.id,
        key,
      ),
      baseUrl: provider.base_url,
      model: model.model_id,
      timeoutMs: Math.min(plan.timeoutMs, maxTimeoutMs),
      contextWindowTokens: dependencies.contextWindowTokens ?? DEFAULT_CONTEXT_WINDOW_TOKENS,
      maxInputTokens,
      reserveOutputTokens: dependencies.reserveOutputTokens ?? DEFAULT_RESERVE_OUTPUT_TOKENS,
    });
  } catch (error) {
    return failWithFallback(db, context, plan, command, now(), {
      reason: `CREDENTIAL_UNAVAILABLE: ${error instanceof Error ? error.message : String(error)}`,
    });
  }

  let result: unknown;
  try {
    result = await client.generate({
      input: plan.input,
      state: plan.state,
      recentEvents: plan.recentEvents,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    if (command.attempts >= plan.maxAttempts) {
      return failWithFallback(db, context, plan, command, now(), {
        reason: `PROVIDER_ERROR: ${detail}`,
        provider: provider.name,
        model: model.model_id,
      });
    }
    // Remaining attempts stay with the worker lease so retry backoff lives in one place.
    throw new AiCommandError("PROVIDER_RETRY", detail);
  }

  const prompt = buildGameContext(plan.state, plan.recentEvents, maxInputTokens);
  const outcome = await submitOutcomeEvent(db, context, plan, {
    type: "aiResultReceived",
    payload: toJsonObject({ result: result ?? null }),
    suffix: "ai-result",
    now: now(),
  });
  await recordUsage(db, context, {
    instanceId: plan.state.instanceId,
    provider: provider.name,
    model: model.model_id,
    inputTokens: estimateTokens(prompt) + estimateTokens(JSON.stringify(plan.input)),
    outputTokens: estimateTokens(JSON.stringify(result ?? null)),
    metadata: {
      commandId: command.command_id,
      nodeId: plan.nodeId,
      agentId: plan.agentId,
      providerModelId: binding.providerModelId,
      attempts: command.attempts,
      outcome,
    },
  });

  return { outcome, provider: provider.name, model: model.model_id };
}

export function createAiCommandHandler(
  db: Kysely<Database>,
  dependencies: AiCommandDependencies,
): (command: ClaimedCommand) => Promise<AiCommandResult> {
  return async (command) => runAiCommand(db, { tenantId: command.tenant_id }, command, dependencies);
}
