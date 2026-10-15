import assert from "node:assert/strict";
import { describe, expect, it } from "vitest";
import {
  normalizeUsername,
  parseCreateUserRequest,
  parseLoginRequest,
  parseUpdateProviderRequest,
  providerBaseUrlSchema,
} from "./index.js";

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
