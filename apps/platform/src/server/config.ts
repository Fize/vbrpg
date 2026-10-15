import { z } from "zod";
import { parseCredentialKey, type CredentialKey } from "./runtime/index.js";

const configSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  LOG_LEVEL: z.enum(["fatal", "error", "warn", "info", "debug", "trace"]).default("info"),
  DATABASE_URL: z.string().min(1).optional(),
  PLATFORM_CREDENTIAL_KEY: z.string().min(1).optional(),
  PLATFORM_CREDENTIAL_KEY_VERSION: z.coerce.number().int().positive().default(1),
  TRUSTED_WEB_ORIGINS: z.string().optional(),
});

export interface ApiConfig {
  environment: "development" | "test" | "production";
  port: number;
  logLevel: "fatal" | "error" | "warn" | "info" | "debug" | "trace";
  databaseUrl?: string;
  credentialKey?: CredentialKey;
  trustedOrigins: string[];
  sessionCookieSecure: boolean;
}

const DEVELOPMENT_ORIGINS = [
  "http://localhost:5173",
  "http://localhost:3000",
  "http://127.0.0.1:5173",
];

function resolveTrustedOrigins(parsed: { NODE_ENV: string; TRUSTED_WEB_ORIGINS?: string | undefined }): string[] {
  const configured = (parsed.TRUSTED_WEB_ORIGINS ?? "")
    .split(",")
    .map((origin) => origin.trim())
    .filter((origin) => origin !== "");
  if (parsed.NODE_ENV === "production") {
    if (configured.length === 0) {
      throw new Error("TRUSTED_WEB_ORIGINS is required in production");
    }
    for (const origin of configured) {
      if (!origin.startsWith("https://")) {
        throw new Error(`TRUSTED_WEB_ORIGINS must use https in production: ${origin}`);
      }
    }
    return configured;
  }
  return configured.length > 0 ? configured : DEVELOPMENT_ORIGINS;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): ApiConfig {
  const parsed = configSchema.parse(env);
  const credentialKey = parsed.PLATFORM_CREDENTIAL_KEY
    ? parseCredentialKey(parsed.PLATFORM_CREDENTIAL_KEY, parsed.PLATFORM_CREDENTIAL_KEY_VERSION)
    : undefined;
  if (parsed.NODE_ENV === "production" && !credentialKey) {
    throw new Error("PLATFORM_CREDENTIAL_KEY is required in production");
  }
  return {
    environment: parsed.NODE_ENV,
    port: parsed.PORT,
    logLevel: parsed.LOG_LEVEL,
    ...(parsed.DATABASE_URL === undefined ? {} : { databaseUrl: parsed.DATABASE_URL }),
    ...(credentialKey === undefined ? {} : { credentialKey }),
    trustedOrigins: resolveTrustedOrigins(parsed),
    // Development stays usable over loopback HTTP; every other environment is https.
    sessionCookieSecure: parsed.NODE_ENV === "production",
  };
}
