import { z } from "zod";
import {
  mapStatusToErrorCode,
  performPinnedJsonRequest,
  resolvePublicEndpoint,
  systemAddressResolver,
  type AddressResolver,
  type ProviderEndpoint,
} from "../provider-endpoint.js";
import { AppError } from "../runtime/index.js";

/** A model call may think for a while, but a match cannot wait forever. */
export const MODEL_CALL_TIMEOUT_MS = 60_000;
const MAX_RESPONSE_BYTES = 512 * 1024;

export interface ChatToolCall {
  id: string;
  name: string;
  /** Raw JSON arguments exactly as the provider sent them. */
  arguments: string;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  toolCalls?: ChatToolCall[];
  toolCallId?: string;
  /** Providers that require their own reasoning back (with tools) need it replayed verbatim. */
  reasoningContent?: string | null;
}

export interface ChatTool {
  name: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, { type: "string"; description: string }>;
    required: string[];
  };
}

export interface ModelUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

export interface ModelCallInput {
  endpoint: ProviderEndpoint;
  apiKey: string;
  model: string;
  messages: ChatMessage[];
  tools?: ChatTool[];
  temperature?: number;
  maxTokens?: number;
  timeoutMs?: number;
}

export interface ModelCallOutput {
  content: string | null;
  /** The provider's own reasoning text, when it returns one. */
  reasoning: string | null;
  toolCalls: ChatToolCall[];
  /** Absent when the provider does not report it; never invented. */
  usage: ModelUsage | null;
  finishReason: string | null;
  latencyMs: number;
}

/** Injectable so the client can be tested without a provider and without opening a socket. */
export type ModelTransport = (request: {
  endpoint: ProviderEndpoint;
  pinned: { address: string; family: 4 | 6 };
  headers: Record<string, string>;
  body: string;
  timeoutMs: number;
}) => Promise<{ status: number; body: string }>;

export function chatCompletionsPath(baseUrl: URL): string {
  return `${baseUrl.pathname.replace(/\/+$/, "")}/chat/completions`;
}

const responseSchema = z.object({
  choices: z
    .array(
      z.object({
        finish_reason: z.string().nullish(),
        message: z.object({
          content: z.string().nullish(),
          // OpenAI-compatible providers differ on the field name for reasoning text.
          reasoning_content: z.string().nullish(),
          reasoning: z.string().nullish(),
          tool_calls: z
            .array(
              z.object({
                id: z.string().nullish(),
                function: z.object({
                  name: z.string(),
                  arguments: z.string().default("{}"),
                }),
              }),
            )
            .nullish(),
        }),
      }),
    )
    .default([]),
  usage: z
    .object({
      prompt_tokens: z.number().nullish(),
      completion_tokens: z.number().nullish(),
      total_tokens: z.number().nullish(),
    })
    .nullish(),
});

function toWireMessage(message: ChatMessage): Record<string, unknown> {
  const wire: Record<string, unknown> = { role: message.role, content: message.content };
  if (message.toolCalls !== undefined) {
    wire["tool_calls"] = message.toolCalls.map((call) => ({
      id: call.id,
      type: "function",
      function: { name: call.name, arguments: call.arguments },
    }));
  }
  if (message.toolCallId !== undefined) wire["tool_call_id"] = message.toolCallId;
  if (message.reasoningContent !== undefined) wire["reasoning_content"] = message.reasoningContent;
  return wire;
}

export function createModelClient(
  options: {
    transport?: ModelTransport;
    resolver?: AddressResolver;
    now?: () => number;
  } = {},
) {
  const resolver = options.resolver ?? systemAddressResolver;
  const now = options.now ?? (() => Date.now());
  const transport: ModelTransport =
    options.transport ??
    ((request) =>
      performPinnedJsonRequest({
        endpoint: request.endpoint,
        pinned: request.pinned,
        method: "POST",
        path: chatCompletionsPath(request.endpoint.url),
        headers: request.headers,
        body: request.body,
        timeoutMs: request.timeoutMs,
        maxBytes: MAX_RESPONSE_BYTES,
      }));

  return {
    async call(input: ModelCallInput): Promise<ModelCallOutput> {
      const timeoutMs = input.timeoutMs ?? MODEL_CALL_TIMEOUT_MS;
      // The same guard as the connection test: a private or loopback destination never gets a socket.
      const pinned = await resolvePublicEndpoint(input.endpoint, resolver);

      const body = JSON.stringify({
        model: input.model,
        messages: input.messages.map(toWireMessage),
        ...(input.tools === undefined || input.tools.length === 0
          ? {}
          : {
              tools: input.tools.map((tool) => ({
                type: "function",
                function: {
                  name: tool.name,
                  description: tool.description,
                  parameters: tool.parameters,
                },
              })),
              tool_choice: "auto",
            }),
        ...(input.temperature === undefined ? {} : { temperature: input.temperature }),
        ...(input.maxTokens === undefined ? {} : { max_tokens: input.maxTokens }),
      });

      const startedAt = now();
      let response: { status: number; body: string };
      try {
        response = await transport({
          endpoint: input.endpoint,
          pinned,
          headers: {
            authorization: `Bearer ${input.apiKey}`,
            "content-type": "application/json",
            accept: "application/json",
            "user-agent": "vbrpg-match/1",
          },
          body,
          timeoutMs,
        });
      } catch (error) {
        const code = (error as NodeJS.ErrnoException).code;
        if (code === "ETIMEDOUT" || code === "ERR_SOCKET_CONNECTION_TIMEOUT") {
          throw new AppError(504, "MODEL_TIMEOUT", "The model provider did not answer in time");
        }
        throw new AppError(502, "MODEL_UNREACHABLE", "The model provider could not be reached");
      }
      const latencyMs = now() - startedAt;

      if (response.status < 200 || response.status >= 300) {
        throw new AppError(
          502,
          "MODEL_CALL_FAILED",
          `The model provider answered ${response.status}`,
          {
            status: response.status,
            providerCode: mapStatusToErrorCode(response.status),
          },
        );
      }

      let parsed: unknown;
      try {
        parsed = JSON.parse(response.body);
      } catch {
        throw new AppError(502, "MODEL_BAD_RESPONSE", "The model provider returned malformed JSON");
      }
      const result = responseSchema.safeParse(parsed);
      if (!result.success) {
        throw new AppError(
          502,
          "MODEL_BAD_RESPONSE",
          "The model provider returned an unexpected shape",
        );
      }

      const choice = result.data.choices[0];
      const message = choice?.message;
      const usage = result.data.usage;
      return {
        content: message?.content ?? null,
        reasoning: message?.reasoning_content ?? message?.reasoning ?? null,
        toolCalls: (message?.tool_calls ?? []).map((call) => ({
          id: call.id ?? "",
          name: call.function.name,
          arguments: call.function.arguments,
        })),
        usage:
          usage === null || usage === undefined
            ? null
            : {
                promptTokens: usage.prompt_tokens ?? 0,
                completionTokens: usage.completion_tokens ?? 0,
                totalTokens: usage.total_tokens ?? 0,
              },
        finishReason: choice?.finish_reason ?? null,
        latencyMs,
      };
    },
  };
}

export type ModelClient = ReturnType<typeof createModelClient>;
