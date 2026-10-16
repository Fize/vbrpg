import type { FastifyInstance } from "fastify";
import type { Kysely } from "kysely";
import { parseGenerateWordPairRequest, type WordPair } from "../../shared/index.js";
import { authenticatePlatformWithCsrf, type PlatformRequestContext } from "../platform-auth.js";
import { AppError, type CredentialKey } from "../runtime/index.js";
import { chooseModelBinding } from "../llm/binding.js";
import { createModelClient, type ModelClient } from "../llm/client.js";
import { generateWordPair } from "../llm/word-pair.js";
import type { Database } from "../db/index.js";

/** A word pair for a round, produced by the platform's own model rather than shipped in the game. */
export interface WordPairService {
  generate(category: string): Promise<WordPair>;
}

export function createWordPairService(input: {
  db: Kysely<Database>;
  credentialKey: CredentialKey | undefined;
  client?: ModelClient;
}): WordPairService {
  const client = input.client ?? createModelClient();

  return {
    async generate(category: string) {
      if (!input.credentialKey) {
        throw new AppError(409, "NO_CREDENTIAL_KEY", "This deployment has no credential key");
      }
      const binding = await chooseModelBinding({
        db: input.db,
        credentialKey: input.credentialKey,
        maxTokens: 256,
      });
      if (!binding) {
        throw new AppError(
          409,
          "NO_MODEL_CONFIGURED",
          "No enabled provider and model is configured",
        );
      }
      return generateWordPair({ client, binding, category });
    },
  };
}

export async function registerWordPairRoutes(
  app: FastifyInstance,
  context: PlatformRequestContext,
  wordPairs: WordPairService,
): Promise<void> {
  app.post(
    "/v1/word-pairs",
    { preHandler: authenticatePlatformWithCsrf(context) },
    async (request) => {
      const principal = request.platformPrincipal!;
      if (!context.limiters.wordPairByUser.allow(principal.userId)) {
        throw new AppError(429, "RATE_LIMITED", "Too many word pairs requested");
      }
      const body = parseGenerateWordPairRequest(request.body);
      return wordPairs.generate(body.category);
    },
  );
}
