import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { describe, expect, it } from "vitest";
import {
  openCredential,
  parseCredentialKey,
  sealCredential,
  type CredentialKey,
} from "./secret-box.js";

const providerId = "11111111-1111-4111-8111-111111111111";
const otherProviderId = "22222222-2222-4222-8222-222222222222";

function key(version = 1): CredentialKey {
  return { version, key: randomBytes(32) };
}

describe("provider credential sealing", () => {
  it("round-trips a secret", () => {
    const credentialKey = key();
    const sealed = sealCredential("sk-secret-value", providerId, credentialKey);
    assert.equal(openCredential(sealed, providerId, credentialKey), "sk-secret-value");
  });

  it("never stores the plaintext in any column", () => {
    const sealed = sealCredential("sk-secret-value", providerId, key());
    const bytes = Buffer.concat([
      sealed.credential_ciphertext,
      sealed.credential_nonce,
      sealed.credential_tag,
    ]).toString("latin1");
    assert.ok(!bytes.includes("sk-secret-value"));
  });

  it("fails closed when the ciphertext is moved to another provider", () => {
    const credentialKey = key();
    const sealed = sealCredential("sk-secret-value", providerId, credentialKey);
    expect(() => openCredential(sealed, otherProviderId, credentialKey)).toThrow();
  });

  it("fails closed on tampering", () => {
    const credentialKey = key();
    const sealed = sealCredential("sk-secret-value", providerId, credentialKey);
    const tampered = {
      ...sealed,
      credential_ciphertext: Buffer.from(sealed.credential_ciphertext),
    };
    tampered.credential_ciphertext[0] = (tampered.credential_ciphertext[0] ?? 0) ^ 0xff;
    expect(() => openCredential(tampered, providerId, credentialKey)).toThrow();
  });

  it("fails closed with the wrong key", () => {
    const sealed = sealCredential("sk-secret-value", providerId, key());
    expect(() => openCredential(sealed, providerId, key())).toThrow();
  });

  it("fails closed when the key version does not match", () => {
    const sealed = sealCredential("sk-secret-value", providerId, key(1));
    expect(() => openCredential(sealed, providerId, key(2))).toThrow();
  });

  it("rejects a master key of the wrong length", () => {
    expect(() => parseCredentialKey(randomBytes(16).toString("base64"), 1)).toThrow();
    expect(() => parseCredentialKey(randomBytes(32).toString("base64"), 0)).toThrow();
    assert.equal(parseCredentialKey(randomBytes(32).toString("base64"), 1).version, 1);
  });
});
