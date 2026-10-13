import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { parseGameEvent, parseGameState, participantSchema } from "@vbrpg/contracts";
import { compileGameDefinition, createInitialState, DefinitionCompileError, dispatchEvent } from "@vbrpg/workflow-engine";
import { AppError } from "../errors.js";
import type { AiClient } from "../ai.js";

const compileRequestSchema = z.object({ definition: z.unknown() });
const dispatchRequestSchema = z.object({
  definition: z.unknown(),
  state: z.unknown(),
  event: z.unknown(),
});
const instanceRequestSchema = z.object({
  definition: z.unknown(),
  instanceId: z.string().min(1),
  gameVersionId: z.string().min(1),
  randomSeed: z.string().min(1),
  participants: z.array(z.unknown()).default([]),
  variables: z.record(z.unknown()).optional(),
});

function compile(input: unknown) {
  try {
    return compileGameDefinition(input);
  } catch (error) {
    if (error instanceof DefinitionCompileError) {
      throw new AppError(400, "INVALID_GAME_DEFINITION", error.message);
    }
    throw error;
  }
}

export async function registerRuntimeRoutes(app: FastifyInstance, aiClient?: AiClient): Promise<void> {
  app.post("/v1/mvp/runtime/compile", async (request) => {
    const body = compileRequestSchema.parse(request.body);
    const compiled = compile(body.definition);
    return {
      definitionHash: compiled.definitionHash,
      entryNodeId: compiled.entryNodeId,
      nodeCount: compiled.nodes.size,
    };
  });

  app.post("/v1/mvp/runtime/dispatch", async (request) => {
    const body = dispatchRequestSchema.parse(request.body);
    const compiled = compile(body.definition);
    const result = dispatchEvent(compiled, parseGameState(body.state), parseGameEvent(body.event));
    return {
      state: result.state,
      commands: result.commands,
    };
  });

  app.post("/v1/mvp/runtime/instances", async (request) => {
    const body = instanceRequestSchema.parse(request.body);
    const compiled = compile(body.definition);
    const state = createInitialState(compiled, {
      instanceId: body.instanceId,
      gameVersionId: body.gameVersionId,
      randomSeed: body.randomSeed,
      participants: body.participants.map((participant) => participantSchema.parse(participant)),
      ...(body.variables === undefined ? {} : { variables: body.variables }),
    });
    return { state };
  });

  app.post("/v1/mvp/runtime/ai-dispatch", async (request) => {
    if (!aiClient) {
      throw new AppError(503, "AI_NOT_CONFIGURED", "AI demo client is not configured");
    }
    const body = dispatchRequestSchema.extend({
      recentEvents: z.array(z.unknown()).default([]),
    }).parse(request.body);
    const compiled = compile(body.definition);
    const state = parseGameState(body.state);
    const event = parseGameEvent(body.event);
    const first = dispatchEvent(compiled, state, event);
    const command = first.commands.find((candidate) => candidate.type === "aiGenerate");
    if (!command || command.type !== "aiGenerate") {
      throw new AppError(400, "AI_COMMAND_NOT_AVAILABLE", "The event did not produce an AI command");
    }
    const recentEvents = body.recentEvents
      .map((item) => parseGameEvent(item))
      .filter((candidate) => candidate.instanceId === first.state.instanceId && candidate.sequence <= first.state.sequence);
    const result = await aiClient.generate({ input: command.input, state: first.state, recentEvents });
    const aiEvent = {
      eventId: `${event.eventId}:ai-result`,
      instanceId: event.instanceId,
      sequence: first.state.sequence + 1,
      type: "aiResultReceived" as const,
      actor: null,
      occurredAtMs: event.occurredAtMs,
      idempotencyKey: `${event.idempotencyKey}:ai-result`,
      payload: { result },
    };
    const second = dispatchEvent(compiled, first.state, aiEvent);
    return { state: second.state, commands: second.commands, aiResult: result };
  });
}
