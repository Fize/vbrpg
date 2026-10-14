import { createHmac, timingSafeEqual } from "node:crypto";
import { AppError } from "@vbrpg/runtime";

export const tenantRoles = ["owner", "admin", "developer", "player"] as const;
export type TenantRole = (typeof tenantRoles)[number];

export interface AuthPrincipal {
  userId: string;
  tenantId: string;
  roles: TenantRole[];
  sessionId: string;
  issuedAt: number;
  expiresAt: number;
}

export interface AuthSessionRecord {
  userId: string;
  tenantId: string;
  role: TenantRole;
  expiresAt: Date;
  revokedAt: Date | null;
}

export type AuthSessionLookup = (
  sessionId: string,
  tenantId: string,
) => Promise<AuthSessionRecord | undefined>;

interface TokenClaims {
  sub: string;
  tid: string;
  roles: TenantRole[];
  sid: string;
  iat: number;
  exp: number;
}

const header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IlZCUkdQIn0";

function encode(value: string): string {
  return Buffer.from(value, "utf8").toString("base64url");
}

function sign(input: string, secret: string): string {
  return createHmac("sha256", secret).update(input).digest("base64url");
}

function assertSecret(secret: string): void {
  if (secret.length < 16) {
    throw new Error("AUTH_TOKEN_SECRET must contain at least 16 characters");
  }
}

function isRole(value: unknown): value is TenantRole {
  return typeof value === "string" && (tenantRoles as readonly string[]).includes(value);
}

function parseClaims(value: unknown): TokenClaims {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Token payload must be an object");
  }
  const claims = value as Record<string, unknown>;
  if (
    typeof claims.sub !== "string" ||
    typeof claims.tid !== "string" ||
    typeof claims.sid !== "string" ||
    !Array.isArray(claims.roles) ||
    claims.roles.some((role) => !isRole(role)) ||
    typeof claims.iat !== "number" ||
    !Number.isInteger(claims.iat) ||
    typeof claims.exp !== "number" ||
    !Number.isInteger(claims.exp)
  ) {
    throw new Error("Token payload has invalid claims");
  }
  return {
    sub: claims.sub,
    tid: claims.tid,
    roles: claims.roles,
    sid: claims.sid,
    iat: claims.iat,
    exp: claims.exp,
  };
}

export function createAccessToken(
  principal: Omit<AuthPrincipal, "issuedAt" | "expiresAt">,
  secret: string,
  options: { now?: number; ttlSeconds?: number } = {},
): string {
  assertSecret(secret);
  const issuedAt = options.now ?? Math.floor(Date.now() / 1000);
  const ttlSeconds = options.ttlSeconds ?? 900;
  if (!Number.isInteger(ttlSeconds) || ttlSeconds <= 0) {
    throw new Error("Token TTL must be a positive integer");
  }
  const claims: TokenClaims = {
    sub: principal.userId,
    tid: principal.tenantId,
    roles: [...principal.roles],
    sid: principal.sessionId,
    iat: issuedAt,
    exp: issuedAt + ttlSeconds,
  };
  const encodedPayload = encode(JSON.stringify(claims));
  const signingInput = `${header}.${encodedPayload}`;
  return `vbrpg.v1.${signingInput}.${sign(signingInput, secret)}`;
}

export function verifyAccessToken(
  token: string,
  secret: string,
  now = Math.floor(Date.now() / 1000),
): AuthPrincipal {
  assertSecret(secret);
  const parts = token.split(".");
  if (parts.length !== 5 || parts[0] !== "vbrpg" || parts[1] !== "v1") {
    throw new Error("Invalid token format");
  }
  const encodedPayload = parts[3];
  const providedSignature = parts[4];
  if (!encodedPayload || !providedSignature) {
    throw new Error("Invalid token signature");
  }
  const signingInput = `${header}.${encodedPayload}`;
  const expectedSignature = sign(signingInput, secret);
  const expectedBytes = Buffer.from(expectedSignature);
  const providedBytes = Buffer.from(providedSignature);
  if (expectedBytes.length !== providedBytes.length || !timingSafeEqual(expectedBytes, providedBytes)) {
    throw new Error("Invalid token signature");
  }

  let claims: TokenClaims;
  try {
    claims = parseClaims(JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf8")));
  } catch {
    throw new Error("Invalid token payload");
  }
  if (claims.exp <= now || claims.iat > now + 60) {
    throw new Error("Token is expired or not yet valid");
  }
  return {
    userId: claims.sub,
    tenantId: claims.tid,
    roles: [...claims.roles],
    sessionId: claims.sid,
    issuedAt: claims.iat,
    expiresAt: claims.exp,
  };
}

export function bearerToken(authorization: string | undefined): string {
  if (!authorization) {
    throw new AppError(401, "AUTH_REQUIRED", "Authentication is required");
  }
  const match = /^Bearer\s+(.+)$/i.exec(authorization);
  if (!match?.[1]) {
    throw new AppError(401, "INVALID_AUTHORIZATION", "Authorization must use a Bearer token");
  }
  return match[1];
}

export function authenticate(
  authorization: string | undefined,
  tenantHeader: string | undefined,
  secret: string | undefined,
): AuthPrincipal {
  if (!secret) {
    throw new AppError(503, "AUTH_NOT_CONFIGURED", "Authentication is not configured");
  }
  let principal: AuthPrincipal;
  try {
    principal = verifyAccessToken(bearerToken(authorization), secret);
  } catch (error) {
    if (error instanceof AppError) throw error;
    throw new AppError(401, "INVALID_TOKEN", "Authentication token is invalid or expired");
  }
  if (!tenantHeader || tenantHeader !== principal.tenantId) {
    throw new AppError(403, "TENANT_CONTEXT_MISMATCH", "Tenant context does not match the authenticated user");
  }
  return principal;
}

export function requireRole(principal: AuthPrincipal, allowed: TenantRole[]): AuthPrincipal {
  if (!allowed.some((role) => principal.roles.includes(role))) {
    throw new AppError(403, "INSUFFICIENT_ROLE", "The authenticated user lacks the required tenant role");
  }
  return principal;
}

export async function authenticateWithSession(
  authorization: string | undefined,
  tenantHeader: string | undefined,
  secret: string | undefined,
  lookup: AuthSessionLookup,
  now = new Date(),
): Promise<AuthPrincipal> {
  const principal = authenticate(authorization, tenantHeader, secret);
  const session = await lookup(principal.sessionId, principal.tenantId);
  if (
    !session ||
    session.userId !== principal.userId ||
    session.tenantId !== principal.tenantId ||
    session.revokedAt !== null ||
    session.expiresAt <= now
  ) {
    throw new AppError(401, "SESSION_INVALID", "Authentication session is invalid or expired");
  }
  return { ...principal, roles: [session.role], expiresAt: Math.floor(session.expiresAt.getTime() / 1000) };
}
