import { z } from "zod";
import { parseCredentialKey, type CredentialKey } from "./secret-box.js";

const configSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  LOG_LEVEL: z.enum(["fatal", "error", "warn", "info", "debug", "trace"]).default("info"),
  DATABASE_URL: z.string().min(1).optional(),
  AUTH_TOKEN_SECRET: z.string().min(16).optional(),
  PLATFORM_CREDENTIAL_KEY: z.string().min(1).optional(),
  PLATFORM_CREDENTIAL_KEY_VERSION: z.coerce.number().int().positive().default(1),
  TRUSTED_WEB_ORIGINS: z.string().optional(),
  DEEPSEEK_API_KEY: z.string().min(1).optional(),
  AI_API_KEY: z.string().min(1).optional(),
  OPENAI_API_KEY: z.string().min(1).optional(),
  AI_API_BASE_URL: z.string().url().default("https://tokenhub.tencentmaas.com/v1"),
  AI_MODEL: z.string().min(1).default("hy3"),
  AI_TIMEOUT_MS: z.coerce.number().int().positive().default(30000),
  AI_CONTEXT_WINDOW_TOKENS: z.coerce.number().int().positive().default(262_144),
  AI_MAX_INPUT_TOKENS: z.coerce.number().int().positive().default(196_608),
  AI_RESERVE_OUTPUT_TOKENS: z.coerce.number().int().positive().default(16_384),
});

export interface ApiConfig {
  environment: "development" | "test" | "production";
  port: number;
  logLevel: "fatal" | "error" | "warn" | "info" | "debug" | "trace";
  databaseUrl?: string;
  authTokenSecret?: string;
  credentialKey?: CredentialKey;
  trustedOrigins: string[];
  sessionCookieSecure: boolean;
  aiApiKey?: string;
  aiApiBaseUrl: string;
  aiModel: string;
  aiTimeoutMs: number;
  aiContextWindowTokens: number;
  aiMaxInputTokens: number;
  aiReserveOutputTokens: number;
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
  const aiApiKey = parsed.DEEPSEEK_API_KEY ?? parsed.AI_API_KEY ?? parsed.OPENAI_API_KEY;
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
    ...(parsed.AUTH_TOKEN_SECRET === undefined ? {} : { authTokenSecret: parsed.AUTH_TOKEN_SECRET }),
    ...(credentialKey === undefined ? {} : { credentialKey }),
    trustedOrigins: resolveTrustedOrigins(parsed),
    // Development stays usable over loopback HTTP; every other environment is https.
    sessionCookieSecure: parsed.NODE_ENV === "production",
    ...(aiApiKey === undefined ? {} : { aiApiKey }),
    aiApiBaseUrl: parsed.AI_API_BASE_URL,
    aiModel: parsed.AI_MODEL,
    aiTimeoutMs: parsed.AI_TIMEOUT_MS,
    aiContextWindowTokens: parsed.AI_CONTEXT_WINDOW_TOKENS,
    aiMaxInputTokens: parsed.AI_MAX_INPUT_TOKENS,
    aiReserveOutputTokens: parsed.AI_RESERVE_OUTPUT_TOKENS,
  };
}
