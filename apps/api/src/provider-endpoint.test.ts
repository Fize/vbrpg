import assert from "node:assert/strict";
import { describe, expect, it } from "vitest";
import {
  classifyAddress,
  mapStatusToErrorCode,
  modelsPath,
  parseProviderEndpoint,
  resolvePublicEndpoint,
  testProviderConnection,
} from "./provider-endpoint.js";
import { AppError } from "./errors.js";

describe("provider endpoint policy", () => {
  it("accepts a public https endpoint", () => {
    assert.equal(parseProviderEndpoint("https://api.example.com/v1").hostname, "api.example.com");
  });

  it("rejects plain http, credentials and fragments", () => {
    expect(() => parseProviderEndpoint("http://api.example.com/v1")).toThrow(AppError);
    expect(() => parseProviderEndpoint("https://user:pass@api.example.com/v1")).toThrow(AppError);
    expect(() => parseProviderEndpoint("https://api.example.com/v1#frag")).toThrow(AppError);
    expect(() => parseProviderEndpoint("not-a-url")).toThrow(AppError);
  });

  it("derives the fixed probe path from the configured base URL", () => {
    assert.equal(modelsPath(new URL("https://api.example.com/v1")), "/v1/models");
    assert.equal(modelsPath(new URL("https://api.example.com/v1/")), "/v1/models");
    assert.equal(modelsPath(new URL("https://api.example.com")), "/models");
  });
});

describe("address classification", () => {
  const blocked = [
    "127.0.0.1",
    "127.9.9.9",
    "10.0.0.1",
    "172.16.0.1",
    "172.31.255.255",
    "192.168.1.1",
    "169.254.169.254",
    "0.0.0.0",
    "100.64.0.1",
    "192.0.0.1",
    "192.0.2.1",
    "198.18.0.1",
    "198.51.100.1",
    "203.0.113.1",
    "224.0.0.1",
    "240.0.0.1",
    "255.255.255.255",
    "::1",
    "::",
    "fe80::1",
    "fc00::1",
    "fd12:3456::1",
    "ff02::1",
    "::ffff:127.0.0.1",
    "::ffff:10.1.1.1",
    "::ffff:192.168.0.1",
    "64:ff9b::7f00:1",
    "2002:7f00:0001::",
    "2001:db8::1",
    "2001:0:0:0:0:0:0:1",
  ];

  const allowed = [
    "8.8.8.8",
    "1.1.1.1",
    "104.20.23.154",
    "2606:4700::1111",
    "2001:4860:4860::8888",
  ];

  for (const address of blocked) {
    it(`blocks ${address}`, () => {
      assert.notEqual(classifyAddress(address), null);
    });
  }

  for (const address of allowed) {
    it(`allows ${address}`, () => {
      assert.equal(classifyAddress(address), null);
    });
  }

  it("treats a non-literal as unusable", () => {
    assert.notEqual(classifyAddress("api.example.com"), null);
  });

  it("strips an IPv6 zone identifier before classification", () => {
    assert.notEqual(classifyAddress("fe80::1%en0"), null);
  });
});

describe("endpoint resolution", () => {
  it("rejects a hostname whose answer set contains a private address", async () => {
    await expect(
      resolvePublicEndpoint(parseProviderEndpoint("https://api.example.com/v1"), async () => [
        "93.184.216.34",
        "10.0.0.5",
      ]),
    ).rejects.toThrow(AppError);
  });

  it("rejects an empty answer set", async () => {
    await expect(
      resolvePublicEndpoint(parseProviderEndpoint("https://api.example.com/v1"), async () => []),
    ).rejects.toThrow(AppError);
  });

  it("pins the first public answer", async () => {
    const resolved = await resolvePublicEndpoint(
      parseProviderEndpoint("https://api.example.com/v1"),
      async () => ["93.184.216.34"],
    );
    assert.deepEqual(resolved, { address: "93.184.216.34", family: 4 });
  });

  it("rejects a public DNS name behind an IP-literal private host", async () => {
    await expect(
      resolvePublicEndpoint(parseProviderEndpoint("https://169.254.169.254/latest"), async () => [
        "8.8.8.8",
      ]),
    ).rejects.toThrow(AppError);
  });

  it("reports a resolver failure as a rejected destination, not a success", async () => {
    const result = await testProviderConnection({
      endpoint: parseProviderEndpoint("https://api.example.com/v1"),
      apiKey: "sk-test",
      resolver: async () => {
        throw new Error("ENOTFOUND");
      },
    });
    assert.equal(result.ok, false);
    assert.equal(result.errorCode, "dns_rejected");
    assert.ok(result.latencyMs >= 0 && result.latencyMs <= 8000);
  });

  it("never issues a request for a private destination", async () => {
    const result = await testProviderConnection({
      endpoint: parseProviderEndpoint("https://api.example.com/v1"),
      apiKey: "sk-test",
      resolver: async () => ["127.0.0.1"],
    });
    assert.equal(result.ok, false);
    assert.equal(result.errorCode, "dns_rejected");
  });
});

describe("status mapping", () => {
  it("maps upstream status codes to a closed error-code set", () => {
    assert.equal(mapStatusToErrorCode(200), null);
    assert.equal(mapStatusToErrorCode(204), null);
    assert.equal(mapStatusToErrorCode(401), "unauthorized");
    assert.equal(mapStatusToErrorCode(403), "unauthorized");
    assert.equal(mapStatusToErrorCode(429), "rate_limited");
    assert.equal(mapStatusToErrorCode(302), "provider_error");
    assert.equal(mapStatusToErrorCode(404), "provider_error");
    assert.equal(mapStatusToErrorCode(500), "provider_error");
  });
});
