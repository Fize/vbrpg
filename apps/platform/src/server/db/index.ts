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
  findPlatformUserByUsername,
  getAuthSessionByTokenHash,
  getPlatformUser,
  getProvider,
  getProviderModelWithProvider,
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
  ProviderModelWithProvider,
  ProviderWithModels,
} from "./platform-repositories.js";
export { createGameInstance, getGameInstance, setInstanceStatus } from "./repositories.js";
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
