import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { SCRYPT_PARAMS, hashPassword, verifyPassword } from "./password.js";

describe("password hashing", () => {
  it("stores a versioned scrypt encoding, never the password", async () => {
    const encoded = await hashPassword("correct horse battery");
    assert.match(
      encoded,
      new RegExp(
        `^scrypt\\$v=1\\$N=${SCRYPT_PARAMS.N},r=${SCRYPT_PARAMS.r},p=${SCRYPT_PARAMS.p}\\$`,
      ),
    );
    assert.ok(!encoded.includes("correct horse battery"));
  });

  it("uses a unique salt per hash", async () => {
    const first = await hashPassword("correct horse battery");
    const second = await hashPassword("correct horse battery");
    assert.notEqual(first, second);
  });

  it("verifies the correct password and rejects a wrong one", async () => {
    const encoded = await hashPassword("correct horse battery");
    assert.equal(await verifyPassword("correct horse battery", encoded), true);
    assert.equal(await verifyPassword("Correct horse battery", encoded), false);
    assert.equal(await verifyPassword("", encoded), false);
  });

  it("fails closed for absent or malformed encodings", async () => {
    assert.equal(await verifyPassword("x", null), false);
    assert.equal(await verifyPassword("x", ""), false);
    assert.equal(await verifyPassword("x", "plaintext"), false);
    assert.equal(await verifyPassword("x", "scrypt$v=9$N=32768,r=8,p=1$AAAA$BBBB"), false);
    assert.equal(await verifyPassword("x", "scrypt$v=1$N=3,r=8,p=1$AAAA$BBBB"), false);
    assert.equal(await verifyPassword("x", "scrypt$v=1$N=32768,r=8,p=1$not-base64!!$BBBB"), false);
  });
});
