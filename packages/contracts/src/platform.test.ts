import assert from "node:assert/strict";
import { describe, expect, it } from "vitest";
import {
  agentModelBindingRecordSchema,
  agentModelBindingSchema,
  normalizeUsername,
  parseAgentModelBinding,
  parseAgentModelBindingRecord,
  parseCreateUserRequest,
  parseLoginRequest,
  parseUpdateProviderRequest,
  providerBaseUrlSchema,
  resolveAgentModelBinding,
  type Provider,
} from "./index.js";

const MODEL_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_MODEL_ID = "22222222-2222-4222-8222-222222222222";

function catalog(overrides: Partial<Provider> = {}): Provider[] {
  const provider: Provider = {
    id: "33333333-3333-4333-8333-333333333333",
    name: "primary",
    baseUrl: "https://api.example.com/v1",
    enabled: true,
    secretConfigured: true,
    models: [
      { id: MODEL_ID, providerId: "33333333-3333-4333-8333-333333333333", modelId: "hy3", displayName: "Hy3", enabled: true },
      { id: OTHER_MODEL_ID, providerId: "33333333-3333-4333-8333-333333333333", modelId: "old", displayName: "Old", enabled: false },
    ],
    ...overrides,
  };
  return [provider];
}

describe("agent model binding", () => {
  it("accepts exactly one provider model id", () => {
    assert.deepEqual(parseAgentModelBinding({ providerModelId: MODEL_ID }), { providerModelId: MODEL_ID });
  });

  it("rejects a list of models", () => {
    expect(() => agentModelBindingSchema.parse({ providerModelId: [MODEL_ID] })).toThrow();
  });

  it("rejects two model fields", () => {
    expect(() =>
      agentModelBindingSchema.parse({ providerModelId: MODEL_ID, fallbackProviderModelId: OTHER_MODEL_ID }),
    ).toThrow();
  });

  it("rejects a non-uuid model reference", () => {
    expect(() => agentModelBindingSchema.parse({ providerModelId: "hy3" })).toThrow();
  });

  it("scopes a persisted binding to a game version and an agent", () => {
    const record = parseAgentModelBindingRecord({
      gameVersionId: "44444444-4444-4444-8444-444444444444",
      agentId: "seer",
      providerModelId: MODEL_ID,
    });

    assert.equal(record.agentId, "seer");
    expect(() =>
      agentModelBindingRecordSchema.parse({ agentId: "seer", providerModelId: MODEL_ID }),
    ).toThrow();
    expect(() =>
      agentModelBindingRecordSchema.parse({
        gameVersionId: "44444444-4444-4444-8444-444444444444",
        agentId: "seer",
        providerModelId: MODEL_ID,
        fallbackProviderModelId: OTHER_MODEL_ID,
      }),
    ).toThrow();
  });

  it("resolves only enabled models of enabled providers", () => {
    assert.equal(resolveAgentModelBinding({ providerModelId: MODEL_ID }, catalog())?.modelId, "hy3");
    assert.equal(resolveAgentModelBinding({ providerModelId: OTHER_MODEL_ID }, catalog()), undefined);
    assert.equal(resolveAgentModelBinding({ providerModelId: MODEL_ID }, catalog({ enabled: false })), undefined);
    assert.equal(resolveAgentModelBinding({ providerModelId: MODEL_ID }, []), undefined);
  });
});

describe("provider endpoint contract", () => {
  it("requires https", () => {
    expect(() => providerBaseUrlSchema.parse("http://api.example.com/v1")).toThrow();
  });

  it("rejects embedded credentials", () => {
    expect(() => providerBaseUrlSchema.parse("https://user:pass@api.example.com/v1")).toThrow();
  });

  it("rejects fragments", () => {
    expect(() => providerBaseUrlSchema.parse("https://api.example.com/v1#frag")).toThrow();
  });

  it("accepts a public https endpoint", () => {
    assert.equal(providerBaseUrlSchema.parse("https://api.example.com/v1"), "https://api.example.com/v1");
  });
});

describe("platform request contracts", () => {
  it("normalizes usernames", () => {
    assert.equal(normalizeUsername("  Alice.1 "), "alice.1");
  });

  it("rejects unknown login fields", () => {
    expect(() => parseLoginRequest({ username: "alice", password: "pw", remember: true })).toThrow();
  });

  it("requires a temporary password of at least 12 characters", () => {
    expect(() => parseCreateUserRequest({ username: "alice", temporaryPassword: "short", role: "user" })).toThrow();
    assert.equal(
      parseCreateUserRequest({ username: "alice", temporaryPassword: "a-long-enough-pw", role: "user" }).role,
      "user",
    );
  });

  it("rejects an empty provider patch", () => {
    expect(() => parseUpdateProviderRequest({})).toThrow();
  });
});
