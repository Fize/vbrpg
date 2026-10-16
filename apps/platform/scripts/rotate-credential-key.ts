import { rotateProviderCredentials } from "../src/server/credential-rotation.js";
import { closeDb, createDb } from "../src/server/db/index.js";
import { parseCredentialKey } from "../src/server/runtime/index.js";

/**
 * One-shot credential key rotation. Both keys travel through the environment, never through argv:
 * a command line is visible to every process on the host.
 *
 *   DATABASE_URL=... \
 *   ROTATE_FROM_KEY=<old> ROTATE_FROM_VERSION=1 \
 *   ROTATE_TO_KEY=<new>   ROTATE_TO_VERSION=2 \
 *   pnpm rotate-credential-key
 */

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.error("DATABASE_URL is required");
  process.exit(1);
}

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    console.error(`${name} is required`);
    process.exit(1);
  }
  return value;
}

function version(name: string): number {
  const value = Number(required(name));
  if (!Number.isInteger(value) || value <= 0) {
    console.error(`${name} must be a positive integer`);
    process.exit(1);
  }
  return value;
}

const from = parseCredentialKey(required("ROTATE_FROM_KEY"), version("ROTATE_FROM_VERSION"));
const to = parseCredentialKey(required("ROTATE_TO_KEY"), version("ROTATE_TO_VERSION"));

const db = createDb({ databaseUrl });

try {
  const result = await rotateProviderCredentials({
    db,
    from,
    to,
    report: (line) => console.log(line),
  });
  console.log(
    `Credential rotation finished: ${result.rotated} rotated, ${result.current} already on version ${to.version}.`,
  );
  console.log("Deploy with the new key next, then remove the old one.");
} catch (error) {
  console.error(error instanceof Error ? error.message : "Credential rotation failed");
  process.exitCode = 1;
} finally {
  await closeDb(db);
}
