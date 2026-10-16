import type { Kysely } from "kysely";
import { getProvider, listProvidersWithModels, type Database } from "../db/index.js";
import { parseProviderEndpoint, type ProviderEndpoint } from "../provider-endpoint.js";
import { openCredential, type CredentialKey } from "../runtime/index.js";

/**
 * The platform's shared model: the first enabled provider and its first model. Nothing binds a seat
 * or a helper to a specific model yet, so one function answers for both the AI seats and the
 * platform's own one-off calls (like generating a word pair).
 */
export interface ModelBinding {
  providerId: string;
  modelId: string;
  endpoint: ProviderEndpoint;
  apiKey: string;
  maxTokens: number;
}

export async function chooseModelBinding(input: {
  db: Kysely<Database>;
  credentialKey: CredentialKey;
  maxTokens: number;
}): Promise<ModelBinding | null> {
  const catalog = await listProvidersWithModels(input.db, { includeDisabled: false });
  const entry = catalog[0];
  const model = entry?.models[0];
  if (!entry || !model) return null;

  const provider = await getProvider(input.db, entry.provider.id);
  if (!provider) return null;

  return {
    providerId: provider.id,
    modelId: model.model_id,
    endpoint: parseProviderEndpoint(provider.base_url),
    apiKey: openCredential(
      {
        credential_ciphertext: provider.credential_ciphertext,
        credential_nonce: provider.credential_nonce,
        credential_tag: provider.credential_tag,
        credential_key_version: provider.credential_key_version,
      },
      provider.id,
      input.credentialKey,
    ),
    maxTokens: input.maxTokens,
  };
}
