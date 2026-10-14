import { randomUUID } from "node:crypto";
import {
  countActiveAdmins,
  createAuthSession,
  createGameInstance,
  createPlatformUser,
  createProvider,
  createProviderModel,
  findPlatformUserByUsername,
  getAuthSessionByTokenHash,
  getGameInstance,
  getPlatformUser,
  getProvider,
  getWorkflowDefinitionByVersion,
  listPlatformUsers,
  listProvidersWithModels,
  recordAuditLog,
  revokeAuthSession,
  revokeUserSessions,
  setAuthSessionCsrfHash,
  touchAuthSession,
  updatePlatformUser,
  updateProvider,
  updateProviderModel,
  createDb,
  platformContext,
  type JsonObject,
  type PlatformUserRecord,
  type ProviderCredentialColumns,
} from "@vbrpg/db";
import type {
  ExternalCommand,
  GameEvent,
  GameState,
  Participant,
  PlayerView,
  PlatformRole,
  ProviderModel,
} from "@vbrpg/contracts";
import { parseGameDefinition, parseGameState } from "@vbrpg/contracts";
import {
  compileGameDefinition,
  createInitialState,
  projectPlayerView,
  type Viewer,
} from "@vbrpg/workflow-engine";
import {
  cancelInstance,
  describeInstance,
  dispatchGameEvent,
  forceInstanceTimeout,
  pauseInstance,
  resumeInstance,
} from "@vbrpg/runtime";
import type {
  AdminInstanceAction,
  AdminInstanceView,
  ForceTimeoutResult,
} from "@vbrpg/runtime";

export interface SessionRecord {
  id: string;
  userId: string;
  csrfTokenHash: Buffer | null;
  idleExpiresAt: Date;
  absoluteExpiresAt: Date;
}

export interface ProviderView {
  id: string;
  name: string;
  baseUrl: string;
  enabled: boolean;
  secretConfigured: boolean;
  models: ProviderModel[];
}

export interface ProviderPatch {
  name?: string;
  baseUrl?: string;
  enabled?: boolean;
  credential?: ProviderCredentialColumns;
}

export interface InstanceView {
  instanceId: string;
  status: GameState["status"];
  currentSequence: number;
  state: GameState;
}

export interface PlatformStore {
  findUserByUsername(username: string): Promise<PlatformUserRecord | undefined>;
  getUser(userId: string): Promise<PlatformUserRecord | undefined>;
  listUsers(): Promise<PlatformUserRecord[]>;
  createUser(input: {
    username: string;
    passwordHash: string;
    role: PlatformRole;
    mustChangePassword: boolean;
  }): Promise<PlatformUserRecord>;
  updateUser(
    userId: string,
    patch: { role?: PlatformRole; active?: boolean; passwordHash?: string; mustChangePassword?: boolean },
  ): Promise<PlatformUserRecord | undefined>;
  countActiveAdmins(): Promise<number>;

  createSession(input: {
    userId: string;
    tokenHash: Buffer;
    csrfTokenHash: Buffer;
    idleExpiresAt: Date;
    absoluteExpiresAt: Date;
  }): Promise<string>;
  findSessionByTokenHash(tokenHash: Buffer): Promise<SessionRecord | undefined>;
  touchSession(sessionId: string, idleExpiresAt: Date): Promise<void>;
  rotateCsrfToken(sessionId: string, csrfTokenHash: Buffer): Promise<void>;
  revokeSession(sessionId: string): Promise<void>;
  revokeUserSessions(userId: string): Promise<void>;

  listProviders(options: { includeDisabled: boolean }): Promise<ProviderView[]>;
  getProviderView(providerId: string): Promise<ProviderView | undefined>;
  getProviderSecret(
    providerId: string,
  ): Promise<{ baseUrl: string; enabled: boolean; sealed: ProviderCredentialColumns } | undefined>;
  createProvider(input: {
    id: string;
    name: string;
    baseUrl: string;
    enabled: boolean;
    credential: ProviderCredentialColumns;
  }): Promise<ProviderView>;
  updateProvider(providerId: string, patch: ProviderPatch): Promise<ProviderView | undefined>;
  createProviderModel(input: {
    providerId: string;
    modelId: string;
    displayName: string;
    enabled: boolean;
  }): Promise<ProviderModel | undefined>;
  updateProviderModel(
    modelRecordId: string,
    patch: { modelId?: string; displayName?: string; enabled?: boolean },
  ): Promise<ProviderModel | undefined>;

  createInstance(input: {
    instanceId: string;
    gameVersionId: string;
    randomSeed: string;
    participants: Participant[];
    variables?: Record<string, unknown>;
  }): Promise<GameState | undefined>;
  getInstanceState(instanceId: string): Promise<InstanceView | undefined>;
  appendEvent(
    instanceId: string,
    event: GameEvent,
  ): Promise<{ state: GameState; commands: ExternalCommand[]; replayed: boolean } | undefined>;
  projectInstanceView(instanceId: string, viewer: Viewer): Promise<PlayerView | undefined>;
  pauseInstance(instanceId: string): Promise<AdminInstanceAction>;
  resumeInstance(instanceId: string): Promise<AdminInstanceAction>;
  cancelInstance(instanceId: string): Promise<AdminInstanceAction>;
  forceInstanceTimeout(instanceId: string): Promise<ForceTimeoutResult>;
  describeInstance(instanceId: string): Promise<AdminInstanceView | undefined>;

  recordAudit(input: {
    actorUserId: string | null;
    action: string;
    resourceType: string;
    resourceId?: string | null;
    metadata?: Record<string, unknown>;
    succeeded: boolean;
  }): Promise<void>;
}

export function createPlatformStore(db: ReturnType<typeof createDb>): PlatformStore {
  return {
    findUserByUsername: (username) => findPlatformUserByUsername(db, username),
    getUser: (userId) => getPlatformUser(db, userId),
    listUsers: () => listPlatformUsers(db),
    createUser: (input) =>
      createPlatformUser(db, {
        id: randomUUID(),
        username: input.username,
        passwordHash: input.passwordHash,
        role: input.role,
        mustChangePassword: input.mustChangePassword,
      }),
    updateUser: (userId, patch) => updatePlatformUser(db, userId, patch),
    countActiveAdmins: () => countActiveAdmins(db),

    createSession: async (input) => {
      const sessionId = randomUUID();
      await createAuthSession(db, {
        id: sessionId,
        userId: input.userId,
        tokenHash: input.tokenHash,
        csrfTokenHash: input.csrfTokenHash,
        idleExpiresAt: input.idleExpiresAt,
        absoluteExpiresAt: input.absoluteExpiresAt,
      });
      return sessionId;
    },
    findSessionByTokenHash: async (tokenHash) => {
      const row = await getAuthSessionByTokenHash(db, tokenHash);
      if (!row) return undefined;
      return {
        id: row.id,
        userId: row.user_id,
        csrfTokenHash: row.csrf_token_hash,
        idleExpiresAt: row.expires_at,
        absoluteExpiresAt: row.absolute_expires_at,
      };
    },
    touchSession: (sessionId, idleExpiresAt) => touchAuthSession(db, sessionId, idleExpiresAt),
    rotateCsrfToken: (sessionId, csrfTokenHash) => setAuthSessionCsrfHash(db, sessionId, csrfTokenHash),
    revokeSession: (sessionId) => revokeAuthSession(db, sessionId),
    revokeUserSessions: (userId) => revokeUserSessions(db, userId),

    listProviders: async (options) => {
      const rows = await listProvidersWithModels(db, { includeDisabled: options.includeDisabled });
      return rows.map((row) => toProviderView(row.provider, row.models));
    },
    getProviderView: async (providerId) => {
      const rows = await listProvidersWithModels(db, { includeDisabled: true });
      const match = rows.find((row) => row.provider.id === providerId);
      return match ? toProviderView(match.provider, match.models) : undefined;
    },
    getProviderSecret: async (providerId) => {
      const row = await getProvider(db, providerId);
      if (!row) return undefined;
      return {
        baseUrl: row.base_url,
        enabled: row.enabled,
        sealed: {
          credential_ciphertext: row.credential_ciphertext,
          credential_nonce: row.credential_nonce,
          credential_tag: row.credential_tag,
          credential_key_version: row.credential_key_version,
        },
      };
    },
    createProvider: async (input) => {
      const row = await createProvider(db, {
        id: input.id,
        name: input.name,
        baseUrl: input.baseUrl,
        enabled: input.enabled,
        credential: input.credential,
      });
      return toProviderView(row, []);
    },
    updateProvider: async (providerId, patch) => {
      const row = await updateProvider(db, providerId, patch);
      return row ? toProviderView(row, []) : undefined;
    },
    createProviderModel: async (input) => {
      const row = await createProviderModel(db, {
        id: randomUUID(),
        providerId: input.providerId,
        modelId: input.modelId,
        displayName: input.displayName,
        enabled: input.enabled,
      });
      return row
        ? {
          id: row.id,
          providerId: row.provider_id,
          modelId: row.model_id,
          displayName: row.display_name,
          enabled: row.enabled,
        }
        : undefined;
    },
    updateProviderModel: async (modelRecordId, patch) => {
      const row = await updateProviderModel(db, modelRecordId, patch);
      return row
        ? {
          id: row.id,
          providerId: row.provider_id,
          modelId: row.model_id,
          displayName: row.display_name,
          enabled: row.enabled,
        }
        : undefined;
    },

    createInstance: async (input) => {
      const definition = await getWorkflowDefinitionByVersion(db, platformContext, input.gameVersionId);
      if (definition === undefined) return undefined;
      const compiled = compileGameDefinition(definition);
      const state = createInitialState(compiled, {
        instanceId: input.instanceId,
        gameVersionId: input.gameVersionId,
        randomSeed: input.randomSeed,
        participants: input.participants,
        ...(input.variables === undefined ? {} : { variables: input.variables }),
      });
      await createGameInstance(db, platformContext, {
        id: input.instanceId,
        gameVersionId: input.gameVersionId,
        status: state.status,
        currentSequence: state.sequence,
        stateJson: state as unknown as JsonObject,
      });
      return state;
    },
    getInstanceState: async (instanceId) => {
      const row = await getGameInstance(db, platformContext, instanceId);
      if (!row) return undefined;
      const state = { ...parseGameState(row.state_json), status: row.status };
      return {
        instanceId: row.id,
        status: state.status,
        currentSequence: row.current_sequence,
        state,
      };
    },
    appendEvent: async (instanceId, event) => {
      const row = await getGameInstance(db, platformContext, instanceId);
      if (!row) return undefined;
      const definition = await getWorkflowDefinitionByVersion(db, platformContext, row.game_version_id);
      if (definition === undefined) {
        throw new Error("Instance references a game version without a workflow definition");
      }
      const compiled = compileGameDefinition(definition);
      return dispatchGameEvent(db, platformContext, compiled, event);
    },

    projectInstanceView: async (instanceId, viewer) => {
      const row = await getGameInstance(db, platformContext, instanceId);
      if (!row) return undefined;
      const definition = await getWorkflowDefinitionByVersion(db, platformContext, row.game_version_id);
      if (definition === undefined) {
        throw new Error("Instance references a game version without a workflow definition");
      }
      return projectPlayerView(parseGameDefinition(definition), parseGameState(row.state_json), viewer);
    },

    pauseInstance: (instanceId) => pauseInstance(db, platformContext, instanceId),
    resumeInstance: (instanceId) => resumeInstance(db, platformContext, instanceId),
    cancelInstance: (instanceId) => cancelInstance(db, platformContext, instanceId),
    forceInstanceTimeout: (instanceId) => forceInstanceTimeout(db, platformContext, instanceId),
    describeInstance: (instanceId) => describeInstance(db, platformContext, instanceId),

    recordAudit: (input) =>
      recordAuditLog(db, {
        id: randomUUID(),
        actorUserId: input.actorUserId,
        action: input.action,
        resourceType: input.resourceType,
        resourceId: input.resourceId ?? null,
        metadata: input.metadata ?? {},
        succeeded: input.succeeded,
      }),
  };
}

function toProviderView(
  provider: {
    id: string;
    name: string;
    base_url: string;
    enabled: boolean;
    credential_ciphertext: Buffer;
  },
  models: ReadonlyArray<{
    id: string;
    provider_id: string;
    model_id: string;
    display_name: string;
    enabled: boolean;
  }>,
): ProviderView {
  return {
    id: provider.id,
    name: provider.name,
    baseUrl: provider.base_url,
    enabled: provider.enabled,
    secretConfigured: provider.credential_ciphertext.length > 0,
    models: models.map((model) => ({
      id: model.id,
      providerId: model.provider_id,
      modelId: model.model_id,
      displayName: model.display_name,
      enabled: model.enabled,
    })),
  };
}
