import { randomBytes } from "node:crypto";
import { AppError } from "./errors.js";
import { constantTimeEquals, hashToken } from "./session.js";

export function createCsrfToken(): string {
  return randomBytes(32).toString("base64url");
}

export function hashCsrfToken(token: string): Buffer {
  return hashToken(token);
}

export function csrfTokenMatches(token: string, storedHash: Buffer | null): boolean {
  if (!storedHash) return false;
  return constantTimeEquals(hashCsrfToken(token), storedHash);
}

/**
 * Cookie-authenticated state changes must come from a trusted origin. A missing
 * Origin is rejected because browsers always send it on cross-origin and
 * same-origin `fetch`/form submissions that carry a cookie.
 */
export function assertTrustedOrigin(origin: string | undefined, trustedOrigins: readonly string[]): void {
  if (!origin) {
    throw new AppError(403, "ORIGIN_REQUIRED", "The Origin header is required for this request");
  }
  if (!trustedOrigins.includes(origin)) {
    throw new AppError(403, "ORIGIN_NOT_ALLOWED", "The request origin is not allowed");
  }
}
