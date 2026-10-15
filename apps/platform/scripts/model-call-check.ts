import { closeDb, createDb, getProvider, listProvidersWithModels } from "../src/server/db/index.js";
import { openCredential, parseCredentialKey } from "../src/server/runtime/index.js";
import { parseProviderEndpoint } from "../src/server/provider-endpoint.js";
import { createModelClient, type ChatMessage } from "../src/server/llm/client.js";
import { buildSeatPrompt } from "../src/server/llm/prompt.js";
import { undercover } from "../src/server/games/undercover.js";

/**
 * One real model call against a configured provider, using the same prompt the platform will send
 * for a seat. Prints the shape of the answer — never the credential — and exits non-zero unless the
 * model actually called a tool, because a call that produces no action is a failed turn.
 */
const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.error("DATABASE_URL is required");
  process.exit(1);
}
const credentialKey = process.env.PLATFORM_CREDENTIAL_KEY;
if (!credentialKey) {
  console.error("PLATFORM_CREDENTIAL_KEY is required to open the stored credential");
  process.exit(1);
}

const args = process.argv.slice(2);
const flag = (name: string): string | undefined => {
  const index = args.indexOf(name);
  const value = index === -1 ? undefined : args[index + 1];
  return value === undefined || value === "" ? undefined : value;
};

const db = createDb({ databaseUrl });
try {
  const wanted = flag("--provider");
  const catalog = await listProvidersWithModels(db, { includeDisabled: false });
  const entry = wanted === undefined ? catalog[0] : catalog.find((row) => row.provider.name === wanted);
  if (!entry) {
    console.error(wanted === undefined ? "No enabled provider is configured" : `No enabled provider named ${wanted}`);
    process.exit(1);
  }
  const model = flag("--model") === undefined ? entry.models[0] : entry.models.find((row) => row.model_id === flag("--model"));
  if (!model) {
    console.error("The provider has no enabled model to call");
    process.exit(1);
  }

  const key = parseCredentialKey(credentialKey, entry.provider.credential_key_version);
  const apiKey = openCredential(
    {
      credential_ciphertext: entry.provider.credential_ciphertext,
      credential_nonce: entry.provider.credential_nonce,
      credential_tag: entry.provider.credential_tag,
      credential_key_version: entry.provider.credential_key_version,
    },
    entry.provider.id,
    key,
  );

  const seats = ["p1", "p2", "p3", "p4"].map((participantId) => ({
    participantId,
    control: "ai" as const,
    status: "active" as const,
  }));
  const state = undercover.initialState({
    instanceId: "instance-check",
    gameVersionId: `undercover@${undercover.version}`,
    engineVersion: undercover.engineVersion,
    randomSeed: `check-${Date.now()}`,
    participants: seats,
  });
  const prompt = buildSeatPrompt({
    game: undercover,
    state,
    participantId: seats[1]!.participantId,
    seatKeys: { p1: "p1", p2: "p2", p3: "p3", p4: "p4" },
    record: [
      { sequence: 1, type: "instanceCreated", participantId: null, payload: {} },
      { sequence: 2, type: "seatMessage", participantId: seats[0]!.participantId, payload: { text: "我这东西，冬天很常见" } },
    ],
  });

  const messages: ChatMessage[] = [{ role: "system", content: prompt.system }, ...prompt.messages];
  const result = await createModelClient().call({
    endpoint: parseProviderEndpoint(entry.provider.base_url),
    apiKey,
    model: model.model_id,
    messages,
    tools: prompt.tools,
    maxTokens: 3000,
  });

  console.log(
    JSON.stringify(
      {
        provider: entry.provider.name,
        model: model.model_id,
        finishReason: result.finishReason,
        usage: result.usage,
        latencyMs: result.latencyMs,
        toolCalls: result.toolCalls,
        content: result.content,
        reasoningHead: result.reasoning?.slice(0, 160) ?? null,
      },
      null,
      2,
    ),
  );

  if (result.toolCalls.length === 0) {
    console.error(
      result.finishReason === "length"
        ? "No tool call: the token budget ran out while the model was thinking. Raise maxTokens."
        : "No tool call: the model answered in prose instead of acting.",
    );
    process.exitCode = 1;
  }
} finally {
  await closeDb(db);
}
