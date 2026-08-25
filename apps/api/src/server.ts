import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";
import { closeDb, createDb, getActiveAuthSession, getTenantMembership, withTenantContext } from "@vbrpg/db";

const config = loadConfig();
const db = config.databaseUrl ? createDb({ databaseUrl: config.databaseUrl }) : undefined;
const app = buildApp({
  config,
  ...(db
    ? {
      sessionLookup: async (sessionId, tenantId) => withTenantContext(db, { tenantId }, async (transaction) => {
        const session = await getActiveAuthSession(transaction, { tenantId }, sessionId);
        if (!session) return undefined;
        const membership = await getTenantMembership(transaction, { tenantId }, session.user_id);
        if (!membership) return undefined;
        return {
          userId: session.user_id,
          tenantId: session.tenant_id,
          role: membership.role,
          expiresAt: session.expires_at,
          revokedAt: session.revoked_at,
        };
      }),
    }
    : {}),
});

if (db) {
  app.addHook("onClose", async () => closeDb(db));
}

try {
  await app.listen({ host: "0.0.0.0", port: config.port });
} catch (error) {
  app.log.error(error);
  process.exitCode = 1;
}
