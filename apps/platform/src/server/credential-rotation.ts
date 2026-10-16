import type { Kysely } from "kysely";
import { listProviderCredentials, updateProvider, type Database } from "./db/index.js";
import { openCredential, sealCredential, type CredentialKey } from "./runtime/index.js";

export interface RotationResult {
  /** Credentials re-sealed onto the new key. */
  rotated: number;
  /** Credentials that were already on it. */
  current: number;
}

/**
 * Re-seals every provider credential from one key version to another. The runtime only ever holds
 * one key, so rotation is a one-shot migration rather than a key ring: run this with both keys
 * available, then deploy with the new one and drop the old.
 *
 * It refuses rather than guesses: a row sealed with a version that is neither `from` nor `to` stops
 * the run, and a row the old key cannot open stops it too, because that means the wrong old key.
 * Stopping leaves the rows already rotated on the new version; re-running resumes, as long as the
 * old key is still at hand. Procedure and rollback: `docs/operations/credential-rotation.md`.
 */
export async function rotateProviderCredentials(input: {
  db: Kysely<Database>;
  from: CredentialKey;
  to: CredentialKey;
  report?: (line: string) => void;
}): Promise<RotationResult> {
  if (input.from.version === input.to.version) {
    throw new Error("The old and the new key version are the same; nothing to rotate");
  }

  const rows = await listProviderCredentials(input.db);
  let rotated = 0;
  let current = 0;

  for (const row of rows) {
    if (row.credential_key_version === input.to.version) {
      current += 1;
      continue;
    }
    if (row.credential_key_version !== input.from.version) {
      throw new Error(
        `Provider ${row.id} is sealed with key version ${row.credential_key_version}, ` +
          `which is neither ${input.from.version} nor ${input.to.version}`,
      );
    }

    let plaintext: string;
    try {
      plaintext = openCredential(
        {
          credential_ciphertext: row.credential_ciphertext,
          credential_nonce: row.credential_nonce,
          credential_tag: row.credential_tag,
          credential_key_version: row.credential_key_version,
        },
        row.id,
        input.from,
      );
    } catch {
      throw new Error(`Provider ${row.id} cannot be opened with the old key; nothing was changed`);
    }

    const sealed = sealCredential(plaintext, row.id, input.to);
    // The credential is replaced, never logged: only the id and the version move through stdout.
    await updateProvider(input.db, row.id, { credential: sealed });
    rotated += 1;
    input.report?.(
      `rotated provider ${row.id}: version ${input.from.version} -> ${input.to.version}`,
    );
  }

  return { rotated, current };
}
