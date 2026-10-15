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
export {
  claimPendingCommands,
  claimScheduledJobs,
  completePendingCommand,
  completeScheduledJob,
  createGameInstance,
  failLeasedTask,
  getGameInstance,
  getLatestSnapshot,
  releaseLease,
  setInstanceStatus,
} from "./repositories.js";
export type { DbExecutor, LeaseOptions } from "./repositories.js";
export type {
  AuthSessionsTable,
  AuditLogsTable,
  Database,
  GameEventsTable,
  GameInstancesTable,
  GameParticipantsTable,
  GameSnapshotsTable,
  JsonObject,
  PendingCommandsTable,
  PlatformRole,
  ProviderModelsTable,
  ProviderType,
  ProvidersTable,
  ScheduledJobsTable,
  UsersTable,
} from "./types.js";
