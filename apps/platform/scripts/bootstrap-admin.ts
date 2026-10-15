import { createInterface } from "node:readline/promises";
import { bootstrapPlatformAdmin, closeDb, createDb } from "../src/server/db/index.js";
import { newPasswordSchema, normalizeUsername, usernameSchema } from "../src/shared/index.js";
import { hashPassword } from "../src/server/password.js";

/**
 * One-time operator bootstrap for the first administrator. Refuses to run when an
 * active administrator already exists, and never prints or persists the password
 * outside the password hash.
 */
const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.error("DATABASE_URL is required");
  process.exit(1);
}

const args = process.argv.slice(2);
const db = createDb({ databaseUrl });

try {
  const username = usernameSchema.parse(
    normalizeUsername(readFlag(args, "--username") ?? (await prompt("Username: "))),
  );
  const password = newPasswordSchema.parse(readFlag(args, "--password") ?? (await promptPassword()));
  const passwordHash = await hashPassword(password);
  const result = await bootstrapPlatformAdmin(db, { username, passwordHash });
  if (result.created) {
    console.log("Initial administrator created. The password must be changed at first login.");
  } else {
    console.error("Refusing to bootstrap: an active administrator already exists");
    process.exitCode = 1;
  }
} finally {
  await closeDb(db);
}

function readFlag(argv: readonly string[], flag: string): string | undefined {
  const index = argv.indexOf(flag);
  const value = index === -1 ? undefined : argv[index + 1];
  return value === undefined || value === "" ? undefined : value;
}

async function prompt(label: string): Promise<string> {
  const readline = createInterface({ input: process.stdin, output: process.stdout });
  try {
    return (await readline.question(label)).trim();
  } finally {
    readline.close();
  }
}

/** Reads without echoing so the password is not left in the terminal scrollback. */
async function promptPassword(): Promise<string> {
  const stdin = process.stdin;
  if (!stdin.isTTY) {
    console.error("No TTY available: pass --password explicitly");
    process.exit(1);
  }
  process.stdout.write("Password: ");
  stdin.setRawMode(true);
  stdin.resume();
  const chunks: string[] = [];
  try {
    for await (const chunk of stdin) {
      const text = String(chunk);
      if (text === "\r" || text === "\n") break;
      if (text === "\u0003") throw new Error("Bootstrap cancelled");
      if (text === "\u007f") {
        chunks.pop();
        continue;
      }
      chunks.push(text);
    }
  } finally {
    stdin.setRawMode(false);
    stdin.pause();
    process.stdout.write("\n");
  }
  return chunks.join("");
}
