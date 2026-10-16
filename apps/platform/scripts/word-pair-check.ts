import { chooseModelBinding } from "../src/server/llm/binding.js";
import { createModelClient } from "../src/server/llm/client.js";
import { buildWordPairPrompt, WORD_PAIR_TOOL } from "../src/server/llm/word-pair.js";
import { closeDb, createDb, listProvidersWithModels } from "../src/server/db/index.js";
import { parseCredentialKey } from "../src/server/runtime/index.js";

/**
 * One real call to the configured model, with the word-pair prompt, printing the raw reply. When
 * generation fails in production this is what says whether the model answered in prose, in JSON or
 * not at all.
 */
const databaseUrl = process.env.DATABASE_URL;
const credentialKey = process.env.PLATFORM_CREDENTIAL_KEY;
const category = process.argv[2] ?? "水果";
if (!databaseUrl || !credentialKey) {
  console.log("Word pair check skipped: DATABASE_URL and PLATFORM_CREDENTIAL_KEY are required");
  process.exit(0);
}

const db = createDb({ databaseUrl });
try {
  const binding = await chooseModelBinding({
    db,
    credentialKey: parseCredentialKey(credentialKey, Number(process.env.PLATFORM_CREDENTIAL_KEY_VERSION ?? 1)),
    maxTokens: 256,
  });
  if (!binding) {
    console.log("No enabled provider and model is configured");
    process.exit(1);
  }
  console.log(`Provider ${binding.providerId} · model ${binding.modelId} · category ${category}`);
  console.log((await listProvidersWithModels(db)).map((entry) => entry.provider.name).join(", "));

  const prompt = buildWordPairPrompt(category);
  const reply = await createModelClient().call({
    endpoint: binding.endpoint,
    model: binding.modelId,
    apiKey: binding.apiKey,
    messages: prompt.messages,
    tools: [WORD_PAIR_TOOL],
    maxTokens: binding.maxTokens,
    timeoutMs: 15_000,
  });
  console.log(
    JSON.stringify(
      {
        finishReason: reply.finishReason,
        content: reply.content,
        toolCalls: reply.toolCalls,
        usage: reply.usage,
      },
      null,
      2,
    ),
  );
} finally {
  await closeDb(db);
}
