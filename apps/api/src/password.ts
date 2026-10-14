import { randomBytes, scrypt as scryptCallback, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

const scrypt = promisify(scryptCallback) as (
  password: string | Buffer,
  salt: string | Buffer,
  keylen: number,
  options: { N: number; r: number; p: number; maxmem: number },
) => Promise<Buffer>;

export const SCRYPT_VERSION = 1;
/** Re-evaluate these against production hardware before release (memory vs. latency). */
export const SCRYPT_PARAMS = { N: 32768, r: 8, p: 1 } as const;
const SALT_BYTES = 16;
const KEY_BYTES = 32;
// 128 * N * r is ~33.5 MiB at the chosen parameters, above Node's 32 MiB default cap.
const MAX_MEM = 128 * SCRYPT_PARAMS.N * SCRYPT_PARAMS.r * 2;

export async function hashPassword(password: string): Promise<string> {
  const salt = randomBytes(SALT_BYTES);
  const key = await derive(password, salt, SCRYPT_PARAMS);
  return [
    "scrypt",
    `v=${SCRYPT_VERSION}`,
    `N=${SCRYPT_PARAMS.N},r=${SCRYPT_PARAMS.r},p=${SCRYPT_PARAMS.p}`,
    salt.toString("base64"),
    key.toString("base64"),
  ].join("$");
}

export async function verifyPassword(password: string, encoded: string | null): Promise<boolean> {
  if (!encoded) return false;
  const parts = encoded.split("$");
  if (parts.length !== 5 || parts[0] !== "scrypt" || parts[1] !== `v=${SCRYPT_VERSION}`) {
    return false;
  }
  const params = parseParams(parts[2] ?? "");
  if (!params) return false;
  let salt: Buffer;
  let expected: Buffer;
  try {
    salt = Buffer.from(parts[3] ?? "", "base64");
    expected = Buffer.from(parts[4] ?? "", "base64");
  } catch {
    return false;
  }
  if (salt.length === 0 || expected.length === 0) return false;
  const actual = await derive(password, salt, params, expected.length);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

function parseParams(value: string): { N: number; r: number; p: number } | null {
  const fields = new Map(
    value.split(",").map((entry) => {
      const [key, raw] = entry.split("=");
      return [key ?? "", Number(raw)];
    }),
  );
  const N = fields.get("N");
  const r = fields.get("r");
  const p = fields.get("p");
  if (!Number.isInteger(N) || !Number.isInteger(r) || !Number.isInteger(p)) return null;
  if (!N || !r || !p || N <= 1 || (N & (N - 1)) !== 0 || r <= 0 || p <= 0) return null;
  return { N, r, p };
}

async function derive(
  password: string,
  salt: Buffer,
  params: { N: number; r: number; p: number },
  keyLength = KEY_BYTES,
): Promise<Buffer> {
  return scrypt(password, salt, keyLength, {
    N: params.N,
    r: params.r,
    p: params.p,
    maxmem: Math.max(MAX_MEM, 128 * params.N * params.r * 2),
  });
}
