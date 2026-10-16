import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { AppError } from "./runtime/index.js";

export const SESSION_COOKIE_NAME = "vbrpg_session";
export const SESSION_IDLE_MS = 30 * 60_000;
export const SESSION_ABSOLUTE_MS = 12 * 60 * 60_000;
/** Idle expiry is refreshed lazily so every request does not write to PostgreSQL. */
export const LAST_SEEN_THROTTLE_MS = 5 * 60_000;

export function createSessionToken(): string {
  return randomBytes(32).toString("base64url");
}

export function hashToken(token: string): Buffer {
  return createHash("sha256").update(token, "utf8").digest();
}

export function idleExpiry(now: Date, absoluteExpiresAt: Date): Date {
  const candidate = new Date(now.getTime() + SESSION_IDLE_MS);
  return candidate < absoluteExpiresAt ? candidate : absoluteExpiresAt;
}

export function buildSessionCookie(
  token: string,
  absoluteExpiresAt: Date,
  secure: boolean,
): string {
  const attributes = [
    `${SESSION_COOKIE_NAME}=${token}`,
    "HttpOnly",
    "SameSite=Lax",
    "Path=/",
    `Max-Age=${Math.max(0, Math.floor((absoluteExpiresAt.getTime() - Date.now()) / 1000))}`,
  ];
  if (secure) attributes.push("Secure");
  return attributes.join("; ");
}

export function clearSessionCookie(secure: boolean): string {
  const attributes = [`${SESSION_COOKIE_NAME}=`, "HttpOnly", "SameSite=Lax", "Path=/", "Max-Age=0"];
  if (secure) attributes.push("Secure");
  return attributes.join("; ");
}

export function readSessionCookie(cookieHeader: string | undefined): string | undefined {
  if (!cookieHeader) return undefined;
  for (const part of cookieHeader.split(";")) {
    const separator = part.indexOf("=");
    if (separator === -1) continue;
    if (part.slice(0, separator).trim() !== SESSION_COOKIE_NAME) continue;
    const value = part.slice(separator + 1).trim();
    return value === "" ? undefined : value;
  }
  return undefined;
}

export function constantTimeEquals(left: Buffer, right: Buffer): boolean {
  return left.length === right.length && timingSafeEqual(left, right);
}

export function sessionInvalid(): AppError {
  return new AppError(401, "SESSION_INVALID", "Authentication session is invalid or expired");
}
