export { closeDb, createDb } from "./client.js";
export type { DbOptions } from "./client.js";
export { downMigrationFileName, selectUpMigrationFiles } from "./migrations.js";
export {
  bootstrapPlatformAdmin,
  countActiveAdmins,
  createAuthSession,
  createPlatformUser,
  createProvider,
  createProviderModel,
  deletePlatformUser,
  deleteProvider,
  deleteProviderModel,
  findPlatformUserByUsername,
  getAuthSessionByTokenHash,
  getPlatformUser,
  getProvider,
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
} from "./platform-repositories.js";
export type {
  PlatformUserRecord,
  ProviderCredentialColumns,
  ProviderWithModels,
} from "./platform-repositories.js";
export {
  advanceGameInstance,
  createGameInstance,
  findEventByIdempotencyKey,
  findReadyAiSeats,
  getGameInstance,
  insertGameEvent,
  insertGameParticipants,
  listGameEvents,
  listGameInstances,
  listGameParticipants,
  listSeatsForUser,
  lockGameInstance,
  setInstanceStatus,
  updateGameParticipantStatus,
} from "./repositories.js";
export type { DbExecutor } from "./repositories.js";
export type {
  AuthSessionsTable,
  AuditLogsTable,
  Database,
  GameEventsTable,
  GameInstancesTable,
  GameParticipantsTable,
  JsonObject,
  PlatformRole,
  ProviderModelsTable,
  ProviderType,
  ProvidersTable,
  UsersTable,
} from "./types.js";
