import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

export const CREDENTIAL_KEY_BYTES = 32;
const NONCE_BYTES = 12;
const AAD_PREFIX = "vbrpg:provider-credential:v1:";

export interface CredentialKey {
  version: number;
  key: Buffer;
}

/** Field names match the persisted provider credential columns. */
export interface SealedCredential {
  credential_ciphertext: Buffer;
  credential_nonce: Buffer;
  credential_tag: Buffer;
  credential_key_version: number;
}

export function parseCredentialKey(encoded: string, version: number): CredentialKey {
  const key = Buffer.from(encoded, "base64");
  if (key.length !== CREDENTIAL_KEY_BYTES) {
    throw new Error(`PLATFORM_CREDENTIAL_KEY must decode to ${CREDENTIAL_KEY_BYTES} bytes`);
  }
  if (!Number.isInteger(version) || version <= 0) {
    throw new Error("Credential key version must be a positive integer");
  }
  return { version, key };
}

/** `providerId` is bound as associated data so a ciphertext cannot be moved between providers. */
function associatedData(providerId: string): Buffer {
  return Buffer.from(`${AAD_PREFIX}${providerId}`, "utf8");
}

export function sealCredential(
  plaintext: string,
  providerId: string,
  key: CredentialKey,
): SealedCredential {
  const nonce = randomBytes(NONCE_BYTES);
  const cipher = createCipheriv("aes-256-gcm", key.key, nonce);
  cipher.setAAD(associatedData(providerId));
  const ciphertext = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  return {
    credential_ciphertext: ciphertext,
    credential_nonce: nonce,
    credential_tag: cipher.getAuthTag(),
    credential_key_version: key.version,
  };
}

export function openCredential(
  sealed: SealedCredential,
  providerId: string,
  key: CredentialKey,
): string {
  if (sealed.credential_key_version !== key.version) {
    throw new Error("Credential was sealed with a different key version");
  }
  const decipher = createDecipheriv("aes-256-gcm", key.key, sealed.credential_nonce);
  decipher.setAAD(associatedData(providerId));
  decipher.setAuthTag(sealed.credential_tag);
  return Buffer.concat([decipher.update(sealed.credential_ciphertext), decipher.final()]).toString(
    "utf8",
  );
}
