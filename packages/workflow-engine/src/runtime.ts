import type { GameEvent, GameState, Participant } from "@vbrpg/contracts";
import type { CompiledGame } from "./compiler.js";
import { transition, type TransitionResult } from "./native-runtime.js";

export interface CreateInstanceInput {
  instanceId: string;
  gameVersionId: string;
  engineVersion?: string;
  randomSeed: string;
  participants: Participant[];
  variables?: Record<string, unknown>;
}

export function createInitialState(
  compiled: CompiledGame,
  input: CreateInstanceInput,
): GameState {
  return {
    instanceId: input.instanceId,
    gameVersionId: input.gameVersionId,
    engineVersion: input.engineVersion ?? compiled.definition.manifest.engineVersion,
    sequence: 0,
    status: "created",
    currentNodeId: compiled.entryNodeId,
    variables: structuredClone(input.variables ?? compiled.definition.variables) as Record<string, unknown>,
    participants: structuredClone(input.participants),
    waiting: null,
    randomSeed: input.randomSeed,
  };
}

export function dispatchEvent(
  compiled: CompiledGame,
  state: GameState,
  event: GameEvent,
): TransitionResult {
  return transition(compiled.definition, state, event);
}
