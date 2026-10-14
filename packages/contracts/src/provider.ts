import { z } from "zod";

const uuidSchema = z.string().uuid();
const instantSchema = z.string().datetime({ offset: true });

export const providerTypeSchema = z.literal("openai_compatible");
export type ProviderType = z.infer<typeof providerTypeSchema>;

export const providerErrorCodeSchema = z.enum([
  "timeout",
  "dns_rejected",
  "tls_error",
  "unauthorized",
  "rate_limited",
  "provider_error",
  "invalid_response",
]);
export type ProviderErrorCode = z.infer<typeof providerErrorCodeSchema>;

const CONNECTION_TEST_MAX_LATENCY_MS = 8000;

/**
 * Shape-only endpoint policy. Destination-address (SSRF) checks happen at request
 * time in the API because they depend on DNS resolution.
 */
export const providerBaseUrlSchema = z
  .string()
  .min(1)
  .max(2048)
  .superRefine((value, ctx) => {
    let url: URL;
    try {
      url = new URL(value);
    } catch {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "baseUrl must be an absolute URL" });
      return;
    }
    if (url.protocol !== "https:") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "baseUrl must use https" });
    }
    if (url.username !== "" || url.password !== "") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "baseUrl must not embed credentials" });
    }
    if (url.hash !== "") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "baseUrl must not contain a fragment" });
    }
    if (url.hostname === "") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "baseUrl must contain a hostname" });
    }
  });

export const providerModelSchema = z
  .object({
    id: uuidSchema,
    providerId: uuidSchema,
    modelId: z.string().min(1).max(200),
    displayName: z.string().min(1).max(100),
    enabled: z.boolean(),
  })
  .strict();

export const providerSchema = z
  .object({
    id: uuidSchema,
    name: z.string().min(1).max(100),
    baseUrl: providerBaseUrlSchema,
    enabled: z.boolean(),
    secretConfigured: z.boolean(),
    models: z.array(providerModelSchema),
  })
  .strict();

export const providerInputSchema = z
  .object({
    name: z.string().min(1).max(100),
    baseUrl: providerBaseUrlSchema,
    apiKey: z.string().min(1).max(4096),
  })
  .strict();

export const updateProviderRequestSchema = z
  .object({
    name: z.string().min(1).max(100).optional(),
    baseUrl: providerBaseUrlSchema.optional(),
    enabled: z.boolean().optional(),
    apiKey: z.string().min(1).max(4096).optional(),
  })
  .strict()
  .refine(
    (value) =>
      value.name !== undefined ||
      value.baseUrl !== undefined ||
      value.enabled !== undefined ||
      value.apiKey !== undefined,
    { message: "At least one of name, baseUrl, enabled or apiKey is required" },
  );

export const createProviderModelRequestSchema = z
  .object({
    modelId: z.string().min(1).max(200),
    displayName: z.string().min(1).max(100),
    enabled: z.boolean().default(true),
  })
  .strict();

export const updateProviderModelRequestSchema = z
  .object({
    modelId: z.string().min(1).max(200).optional(),
    displayName: z.string().min(1).max(100).optional(),
    enabled: z.boolean().optional(),
  })
  .strict()
  .refine(
    (value) => value.modelId !== undefined || value.displayName !== undefined || value.enabled !== undefined,
    { message: "At least one of modelId, displayName or enabled is required" },
  );

export const connectionTestResultSchema = z
  .object({
    ok: z.boolean(),
    latencyMs: z.number().int().min(0).max(CONNECTION_TEST_MAX_LATENCY_MS),
    checkedAt: instantSchema,
    errorCode: providerErrorCodeSchema.nullable(),
  })
  .strict();

export const providerListSchema = z.object({ providers: z.array(providerSchema) }).strict();

/**
 * An agent binds exactly one model. Multi-model selection is intentionally not
 * representable: there is no list/array form of this contract.
 */
export const agentModelBindingSchema = z.object({ providerModelId: uuidSchema }).strict();

export type ProviderModel = z.infer<typeof providerModelSchema>;
export type Provider = z.infer<typeof providerSchema>;
export type ProviderInput = z.infer<typeof providerInputSchema>;
export type UpdateProviderRequest = z.infer<typeof updateProviderRequestSchema>;
export type CreateProviderModelRequest = z.infer<typeof createProviderModelRequestSchema>;
export type UpdateProviderModelRequest = z.infer<typeof updateProviderModelRequestSchema>;
export type ConnectionTestResult = z.infer<typeof connectionTestResultSchema>;
export type AgentModelBinding = z.infer<typeof agentModelBindingSchema>;

export function parseProviderInput(input: unknown): ProviderInput {
  return providerInputSchema.parse(input);
}

export function parseUpdateProviderRequest(input: unknown): UpdateProviderRequest {
  return updateProviderRequestSchema.parse(input);
}

export function parseCreateProviderModelRequest(input: unknown): CreateProviderModelRequest {
  return createProviderModelRequestSchema.parse(input);
}

export function parseUpdateProviderModelRequest(input: unknown): UpdateProviderModelRequest {
  return updateProviderModelRequestSchema.parse(input);
}

export function parseAgentModelBinding(input: unknown): AgentModelBinding {
  return agentModelBindingSchema.parse(input);
}

/**
 * Resolves a binding against a provider catalog. Returns `undefined` when the
 * model is unknown, or when the model or its provider is disabled — a binding
 * to a disabled model must never resolve.
 */
export function resolveAgentModelBinding(
  binding: AgentModelBinding,
  providers: readonly Provider[],
): ProviderModel | undefined {
  for (const provider of providers) {
    if (!provider.enabled) continue;
    const model = provider.models.find((candidate) => candidate.id === binding.providerModelId);
    if (model) return model.enabled ? model : undefined;
  }
  return undefined;
}
