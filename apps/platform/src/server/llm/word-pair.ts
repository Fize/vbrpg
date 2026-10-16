import { z } from "zod";
import { AppError } from "../runtime/index.js";
import type { ChatMessage, ChatTool, ModelClient } from "./client.js";
import type { ModelBinding } from "./binding.js";

/**
 * The platform's own model call: a word pair for a round of 谁是卧底. The words are input, not game
 * data — this is the helper that fills that input so a table does not have to invent its own.
 *
 * The reply is requested as a tool call rather than free JSON: a tool schema is the one shape every
 * provider on this platform is already asked to produce.
 */
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

/** One call, one tool call, two words. Anything else is a bad reply, not a retry loop. */
export async function generateWordPair(input: {
  client: ModelClient;
  binding: ModelBinding;
  category: string;
}): Promise<WordPair> {
  const prompt = buildWordPairPrompt(input.category);
  const reply = await input.client.call({
    endpoint: input.binding.endpoint,
    model: input.binding.modelId,
    apiKey: input.binding.apiKey,
    messages: prompt.messages,
    tools: [WORD_PAIR_TOOL],
    maxTokens: input.binding.maxTokens,
  });

  const call = reply.toolCalls[0];
  if (!call) {
    throw new AppError(502, "MODEL_BAD_RESPONSE", "The model did not return a word pair");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(call.arguments) as unknown;
  } catch {
    throw new AppError(502, "MODEL_BAD_RESPONSE", "The model returned an unreadable word pair");
  }

  const pair = wordPairSchema.safeParse(parsed);
  if (!pair.success || pair.data.civilian === pair.data.undercover) {
    throw new AppError(502, "MODEL_BAD_RESPONSE", "The model returned an unusable word pair");
  }
  return pair.data;
}
