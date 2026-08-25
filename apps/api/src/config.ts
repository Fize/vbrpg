import { z } from "zod";

const configSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  LOG_LEVEL: z.enum(["fatal", "error", "warn", "info", "debug", "trace"]).default("info"),
  DATABASE_URL: z.string().min(1).optional(),
  AUTH_TOKEN_SECRET: z.string().min(16).optional(),
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
  aiApiKey?: string;
  aiApiBaseUrl: string;
  aiModel: string;
  aiTimeoutMs: number;
  aiContextWindowTokens: number;
  aiMaxInputTokens: number;
  aiReserveOutputTokens: number;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): ApiConfig {
  const parsed = configSchema.parse(env);
  const aiApiKey = parsed.DEEPSEEK_API_KEY ?? parsed.AI_API_KEY ?? parsed.OPENAI_API_KEY;
  return {
    environment: parsed.NODE_ENV,
    port: parsed.PORT,
    logLevel: parsed.LOG_LEVEL,
    ...(parsed.DATABASE_URL === undefined ? {} : { databaseUrl: parsed.DATABASE_URL }),
    ...(parsed.AUTH_TOKEN_SECRET === undefined ? {} : { authTokenSecret: parsed.AUTH_TOKEN_SECRET }),
    ...(aiApiKey === undefined ? {} : { aiApiKey }),
    aiApiBaseUrl: parsed.AI_API_BASE_URL,
    aiModel: parsed.AI_MODEL,
    aiTimeoutMs: parsed.AI_TIMEOUT_MS,
    aiContextWindowTokens: parsed.AI_CONTEXT_WINDOW_TOKENS,
    aiMaxInputTokens: parsed.AI_MAX_INPUT_TOKENS,
    aiReserveOutputTokens: parsed.AI_RESERVE_OUTPUT_TOKENS,
  };
}
