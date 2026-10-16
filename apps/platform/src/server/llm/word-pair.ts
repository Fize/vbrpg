import type { Kysely } from "kysely";
import { z } from "zod";
import { AppError, type CredentialKey } from "../runtime/index.js";
import type { Database } from "../db/index.js";
import { chooseModelBinding, type ModelBinding } from "./binding.js";
import { createModelClient, type ChatMessage, type ChatTool, type ModelClient } from "./client.js";

/**
 * The platform's own model call: a word pair for a round of 谁是卧底. The words are input, not game
 * data — this is the helper that fills that input so a table does not have to invent its own.
 *
 * The reply is requested as a tool call rather than free JSON: a tool schema is the one shape every
 * provider on this platform is already asked to produce.
 */
/** Generating a pair is a small completion; a create request must not hang on a slow provider. */
export const WORD_PAIR_TIMEOUT_MS = 15_000;

/**
 * Room for the reasoning a model spends before it calls the tool. A tight budget here truncates the
 * arguments and looks exactly like a model that ignored the instruction — it cost a failed room
 * creation to learn that 256 was not enough.
 */
export const WORD_PAIR_MAX_TOKENS = 1024;

export const WORD_PAIR_TOOL: ChatTool = {
  name: "giveWordPair",
  description: "给出一对相近但不同的词，用于「谁是卧底」的平民与卧底。",
  parameters: {
    type: "object",
    properties: {
      civilian: { type: "string", description: "多数席位拿到的词，常见、好描述" },
      undercover: { type: "string", description: "卧底拿到的词，与前者相近但不能相同" },
    },
    required: ["civilian", "undercover"],
  },
};

const wordPairSchema = z.object({
  civilian: z.string().trim().min(1).max(20),
  undercover: z.string().trim().min(1).max(20),
});

export interface WordPair {
  civilian: string;
  undercover: string;
}

export function buildWordPairPrompt(category: string): { messages: ChatMessage[] } {
  const system = [
    "你在为一个聚会游戏「谁是卧底」准备词对。",
    "大多数席位拿到同一个词，一个席位拿到一个相近但不相同的词。",
    "两个词必须是同一类事物、日常生活中好描述、不能是同一个词，也不要一个词包含另一个。",
    "不要解释，不要输出多余文字，只能用工具调用给出两个词。",
  ].join("\n");

  return {
    messages: [
      { role: "system", content: system },
      { role: "user", content: `分类：${category}` },
    ],
  };
}

/**
 * The create path's view of the platform's model. With no enabled provider it throws, because a
 * match asking for words and silently getting none would fail later and less clearly.
 */
export function createWordPairGenerator(input: {
  db: Kysely<Database>;
  credentialKey: CredentialKey | undefined;
  client?: ModelClient;
}): (category: string) => Promise<WordPair> {
  const client = input.client ?? createModelClient();

  return async (category: string) => {
    if (!input.credentialKey) {
      throw new AppError(409, "NO_CREDENTIAL_KEY", "This deployment has no credential key");
    }
    const binding = await chooseModelBinding({
      db: input.db,
      credentialKey: input.credentialKey,
      maxTokens: WORD_PAIR_MAX_TOKENS,
    });
    if (!binding) {
      throw new AppError(409, "NO_MODEL_CONFIGURED", "No enabled provider and model is configured");
    }
    return generateWordPair({ client, binding, category });
  };
}

/** How many times a bad reply is retried: models occasionally answer in prose instead of a call. */
const WORD_PAIR_ATTEMPTS = 2;

/**
 * One tool call, two words. A reply that is not a usable pair is retried once — a room creation
 * failing because a model had a bad moment is worse than one extra paid call.
 */
export async function generateWordPair(input: {
  client: ModelClient;
  binding: ModelBinding;
  category: string;
}): Promise<WordPair> {
  const prompt = buildWordPairPrompt(input.category);
  let lastError: AppError | null = null;

  for (let attempt = 0; attempt < WORD_PAIR_ATTEMPTS; attempt += 1) {
    const reply = await input.client.call({
      endpoint: input.binding.endpoint,
      model: input.binding.modelId,
      apiKey: input.binding.apiKey,
      messages: prompt.messages,
      tools: [WORD_PAIR_TOOL],
      maxTokens: input.binding.maxTokens,
      timeoutMs: WORD_PAIR_TIMEOUT_MS,
    });

    if (reply.finishReason === "length") {
      lastError = new AppError(502, "MODEL_BAD_RESPONSE", "The model ran out of room mid-answer");
      continue;
    }

    const call = reply.toolCalls[0];
    if (!call) {
      lastError = new AppError(502, "MODEL_BAD_RESPONSE", "The model did not return a word pair");
      continue;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(call.arguments) as unknown;
    } catch {
      lastError = new AppError(
        502,
        "MODEL_BAD_RESPONSE",
        "The model returned an unreadable word pair",
      );
      continue;
    }

    const pair = wordPairSchema.safeParse(parsed);
    if (!pair.success || pair.data.civilian === pair.data.undercover) {
      lastError = new AppError(
        502,
        "MODEL_BAD_RESPONSE",
        "The model returned an unusable word pair",
      );
      continue;
    }
    return pair.data;
  }

  throw lastError ?? new AppError(502, "MODEL_BAD_RESPONSE", "The model returned no word pair");
}
