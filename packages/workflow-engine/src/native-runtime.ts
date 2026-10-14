import type {
  ExternalCommand,
  GameDefinition,
  GameEvent,
  GameState,
} from "@vbrpg/contracts";

export interface TransitionResult {
  state: GameState;
  events: GameEvent[];
  commands: ExternalCommand[];
}

export class EngineError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "EngineError";
    this.code = code;
  }
}

type Config = Record<string, unknown>;

function asConfig(value: unknown): Config {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new EngineError("INVALID_NODE_CONFIG", "Node config must be an object");
  }

  return value as Config;
}

function requiredString(config: Config, key: string): string {
  const value = config[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new EngineError("INVALID_NODE_CONFIG", `Node config requires string: ${key}`);
  }

  return value;
}

function requiredPositiveInteger(config: Config, key: string): number {
  const value = config[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new EngineError(
      "INVALID_NODE_CONFIG",
      `Node config requires positive integer: ${key}`,
    );
  }

  return value;
}

function stringArray(config: Config, key: string): string[] {
  const value = config[key];
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new EngineError("INVALID_NODE_CONFIG", `Node config requires string array: ${key}`);
  }

  return value;
}

function nextNodeId(node: GameDefinition["workflow"]["nodes"][number]): string {
  const next = node.next[0];
  if (!next) {
    throw new EngineError("MISSING_NEXT_NODE", `Node ${node.id} has no next node`);
  }

  return next;
}

function findNode(definition: GameDefinition, nodeId: string) {
  const node = definition.workflow.nodes.find((candidate) => candidate.id === nodeId);
  if (!node) {
    throw new EngineError("UNKNOWN_NODE", `Workflow node does not exist: ${nodeId}`);
  }

  return node;
}

function cloneVariables(variables: GameState["variables"]): GameState["variables"] {
  return structuredClone(variables);
}

function participantIdFromEvent(event: GameEvent): string {
  const participantId = event.payload.participantId;
  if (typeof participantId !== "string" || participantId.length === 0) {
    throw new EngineError("INVALID_INPUT", "Player input requires participantId");
  }

  return participantId;
}

function inputValueFromEvent(event: GameEvent): unknown {
  if (!("value" in event.payload)) {
    throw new EngineError("INVALID_INPUT", "Player input requires value");
  }

  return event.payload.value;
}

function advance(state: GameState, nodeId: string): GameState {
  return {
    ...state,
    currentNodeId: nodeId,
    status: "running",
    waiting: null,
  };
}

function setWaiting(
  state: GameState,
  kind: "playerInput" | "collectInput" | "timer" | "ai",
  nodeId: string,
  participantIds: string[] = [],
  deadlineMs?: number,
): GameState {
  return {
    ...state,
    status: "waiting",
    waiting: {
      kind,
      nodeId,
      participantIds,
      ...(deadlineMs === undefined ? {} : { deadlineMs }),
    },
  };
}

function consumePlayerInput(
  definition: GameDefinition,
  state: GameState,
  event: GameEvent,
): GameState {
  const waiting = state.waiting;
  if (!waiting || (waiting.kind !== "playerInput" && waiting.kind !== "collectInput")) {
    throw new EngineError("UNEXPECTED_INPUT", "The instance is not waiting for player input");
  }

  const participantId = participantIdFromEvent(event);
  const value = inputValueFromEvent(event);
  if (waiting.participantIds.length > 0 && !waiting.participantIds.includes(participantId)) {
    throw new EngineError("NOT_ALLOWED", `Participant is not allowed to respond: ${participantId}`);
  }

  const node = findNode(definition, waiting.nodeId);
  const config = asConfig(node.config);
  const variables = cloneVariables(state.variables);

  if (waiting.kind === "playerInput") {
    const inputKey = requiredString(config, "inputKey");
    variables[inputKey] = value;
    return advance({ ...state, variables }, nextNodeId(node));
  }

  const collectionKey = requiredString(config, "collectionKey");
  const collection = variables[collectionKey];
  const collected: Record<string, unknown> =
    typeof collection === "object" && collection !== null && !Array.isArray(collection)
      ? structuredClone(collection) as Record<string, unknown>
      : {};
  if (participantId in collected) {
    throw new EngineError("DUPLICATE_INPUT", `Participant already responded: ${participantId}`);
  }

  collected[participantId] = value;
  variables[collectionKey] = collected;
  const complete = waiting.participantIds.every((id) => id in collected);
  if (!complete) {
    return { ...state, variables };
  }

  return advance({ ...state, variables }, nextNodeId(node));
}

function consumeTimer(
  definition: GameDefinition,
  state: GameState,
  event: GameEvent,
): GameState {
  if (!state.waiting || state.waiting.kind !== "timer") {
    throw new EngineError("UNEXPECTED_TIMER", "The instance is not waiting for a timer");
  }

  const node = findNode(definition, state.waiting.nodeId);
  if (event.payload.nodeId !== node.id) {
    throw new EngineError("INVALID_INPUT", "Timer event does not target the waiting node");
  }

  return advance(state, nextNodeId(node));
}

function consumeAiResult(
  definition: GameDefinition,
  state: GameState,
  event: GameEvent,
): GameState {
  if (!state.waiting || state.waiting.kind !== "ai") {
    throw new EngineError("UNEXPECTED_AI_RESULT", "The instance is not waiting for an AI result");
  }

  const node = findNode(definition, state.waiting.nodeId);
  const config = asConfig(node.config);
  const resultKey = requiredString(config, "resultKey");
  const variables = cloneVariables(state.variables);
  variables[resultKey] = event.payload.result;
  return advance({ ...state, variables }, nextNodeId(node));
}

function consumeAiFailure(
  definition: GameDefinition,
  state: GameState,
): GameState {
  if (!state.waiting || state.waiting.kind !== "ai") {
    throw new EngineError("UNEXPECTED_AI_FAILURE", "The instance is not waiting for an AI result");
  }

  const node = findNode(definition, state.waiting.nodeId);
  return advance(state, requiredString(asConfig(node.config), "fallbackNodeId"));
}

function runAutomaticNodes(
  definition: GameDefinition,
  initialState: GameState,
  event: GameEvent,
): { state: GameState; commands: ExternalCommand[] } {
  let state = initialState;
  const commands: ExternalCommand[] = [];
  const visited = new Set<string>();

  for (let step = 0; step < 100; step += 1) {
    const node = findNode(definition, state.currentNodeId);
    if (visited.has(node.id)) {
      throw new EngineError("AUTOMATIC_LOOP", `Automatic workflow loop reached node: ${node.id}`);
    }
    visited.add(node.id);

    const config = asConfig(node.config);
    switch (node.type) {
      case "start":
        state = advance(state, nextNodeId(node));
        continue;
      case "setVariable": {
        const variables = cloneVariables(state.variables);
        variables[requiredString(config, "key")] = config.value;
        state = advance({ ...state, variables }, nextNodeId(node));
        continue;
      }
      case "branch": {
        const variable = state.variables[requiredString(config, "variable")];
        const expected = config.equals;
        const branch = variable === expected ? "whenTrue" : "whenFalse";
        state = advance(state, requiredString(config, branch));
        continue;
      }
      case "waitForPlayerInput":
        return {
          state: setWaiting(
            state,
            "playerInput",
            node.id,
            config.participantId === undefined ? [] : [requiredString(config, "participantId")],
          ),
          commands,
        };
      case "collectInput":
      case "vote":
        return {
          state: setWaiting(state, "collectInput", node.id, stringArray(config, "participantIds")),
          commands,
        };
      case "timer": {
        const durationMs = requiredPositiveInteger(config, "durationMs");
        const deadlineMs = event.occurredAtMs + durationMs;
        state = setWaiting(state, "timer", node.id, [], deadlineMs);
        commands.push({
          commandId: `${state.instanceId}:schedule:${state.sequence}:${node.id}`,
          instanceId: state.instanceId,
          type: "schedule",
          runAtMs: deadlineMs,
          job: "timerExpired",
        });
        return { state, commands };
      }
      case "aiGenerate": {
        const agentId = requiredString(config, "agentId");
        const timeoutMs = requiredPositiveInteger(config, "timeoutMs");
        const maxAttempts = requiredPositiveInteger(config, "maxAttempts");
        const fallbackNodeId = requiredString(config, "fallbackNodeId");
        const input = config.input;
        if (typeof input !== "object" || input === null || Array.isArray(input)) {
          throw new EngineError("INVALID_NODE_CONFIG", "AI input must be an object");
        }
        state = setWaiting(state, "ai", node.id);
        commands.push({
          commandId: `${state.instanceId}:ai:${state.sequence}:${node.id}`,
          instanceId: state.instanceId,
          type: "aiGenerate",
          agentId,
          input: input as Record<string, unknown>,
          timeoutMs,
          maxAttempts,
          fallbackNodeId,
        });
        return { state, commands };
      }
      case "emitEvent": {
        const eventName = requiredString(config, "eventName");
        const payload = config.payload;
        if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
          throw new EngineError("INVALID_NODE_CONFIG", "Emitted event payload must be an object");
        }
        commands.push({
          commandId: `${state.instanceId}:emit:${state.sequence}:${node.id}`,
          instanceId: state.instanceId,
          type: "emit",
          eventName,
          payload: payload as Record<string, unknown>,
        });
        state = advance(state, nextNodeId(node));
        continue;
      }
      case "end":
        return { state: { ...state, status: "completed", waiting: null }, commands };
      default:
        throw new EngineError("UNSUPPORTED_NODE", `Native spike does not support node: ${node.type}`);
    }
  }

  throw new EngineError("AUTOMATIC_LOOP", "Automatic workflow exceeded the 100-node safety limit");
}

export function transition(
  definition: GameDefinition,
  state: GameState,
  event: GameEvent,
): TransitionResult {
  if (event.instanceId !== state.instanceId) {
    throw new EngineError("INSTANCE_MISMATCH", "Event belongs to a different instance");
  }
  if (event.sequence !== state.sequence + 1) {
    throw new EngineError("SEQUENCE_MISMATCH", "Event sequence must advance exactly once");
  }

  let nextState: GameState = { ...state, sequence: event.sequence };
  if (event.type === "instanceCreated") {
    if (state.status !== "created") {
      throw new EngineError("INVALID_LIFECYCLE", "Instance can only be created once");
    }
    nextState = { ...nextState, status: "running" };
  } else if (event.type === "playerInputReceived") {
    nextState = consumePlayerInput(definition, nextState, event);
  } else if (event.type === "timerExpired") {
    nextState = consumeTimer(definition, nextState, event);
  } else if (event.type === "aiResultReceived") {
    nextState = consumeAiResult(definition, nextState, event);
  } else if (event.type === "aiFailed") {
    nextState = consumeAiFailure(definition, nextState);
  } else {
    throw new EngineError("UNSUPPORTED_EVENT", `Native spike does not support event: ${event.type}`);
  }

  const automatic = runAutomaticNodes(definition, nextState, event);
  return {
    state: automatic.state,
    events: [event],
    commands: automatic.commands,
  };
}
