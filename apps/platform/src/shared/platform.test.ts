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
    expect(providerBaseUrlSchema.parse("https://api.example.com/v1")).toBe("https://api.example.com/v1");
  });
});

describe("platform request contracts", () => {
  it("normalizes usernames", () => {
    expect(normalizeUsername("  Alice.1 ")).toBe("alice.1");
  });

  it("rejects unknown login fields", () => {
    expect(() => parseLoginRequest({ username: "alice", password: "pw", remember: true })).toThrow();
  });

  it("requires a temporary password of at least 12 characters", () => {
    expect(() => parseCreateUserRequest({ username: "alice", temporaryPassword: "short", role: "user" })).toThrow();
    expect(
      parseCreateUserRequest({ username: "alice", temporaryPassword: "a-long-enough-pw", role: "user" }).role,
    ).toBe("user");
  });

  it("rejects an empty provider patch", () => {
    expect(() => parseUpdateProviderRequest({})).toThrow();
  });
});
