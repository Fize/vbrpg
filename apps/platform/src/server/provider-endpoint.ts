import { lookup as dnsLookup } from "node:dns/promises";
import { isIP } from "node:net";
import { request as httpsRequest } from "node:https";
import type { ConnectionTestResult, ProviderErrorCode } from "../shared/index.js";
import { AppError } from "./runtime/index.js";

export const CONNECT_TIMEOUT_MS = 3000;
export const TOTAL_TIMEOUT_MS = 8000;
export const MAX_RESPONSE_BYTES = 64 * 1024;

export interface ProviderEndpoint {
  url: URL;
  hostname: string;
}

export type AddressResolver = (hostname: string) => Promise<string[]>;

export const systemAddressResolver: AddressResolver = async (hostname) => {
  const records = await dnsLookup(hostname, { all: true, verbatim: true });
  return records.map((record) => record.address);
};

/** Shape and scheme policy. Destination-address checks happen at resolution time. */
export function parseProviderEndpoint(rawUrl: string): ProviderEndpoint {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new AppError(400, "PROVIDER_ENDPOINT_INVALID", "Provider base URL must be an absolute URL");
  }
  if (url.protocol !== "https:") {
    throw new AppError(400, "PROVIDER_ENDPOINT_INVALID", "Provider base URL must use https");
  }
  if (url.username !== "" || url.password !== "") {
    throw new AppError(400, "PROVIDER_ENDPOINT_INVALID", "Provider base URL must not embed credentials");
  }
  if (url.hash !== "") {
    throw new AppError(400, "PROVIDER_ENDPOINT_INVALID", "Provider base URL must not contain a fragment");
  }
  if (url.hostname === "") {
    throw new AppError(400, "PROVIDER_ENDPOINT_INVALID", "Provider base URL must contain a hostname");
  }
  return { url, hostname: stripBrackets(url.hostname) };
}

function stripBrackets(hostname: string): string {
  return hostname.startsWith("[") && hostname.endsWith("]") ? hostname.slice(1, -1) : hostname;
}

function parseIpv4(value: string): number[] | null {
  const parts = value.split(".");
  if (parts.length !== 4) return null;
  const bytes: number[] = [];
  for (const part of parts) {
    if (!/^\d{1,3}$/.test(part)) return null;
    const byte = Number(part);
    if (byte > 255) return null;
    bytes.push(byte);
  }
  return bytes;
}

function groupsToWords(groups: readonly string[]): number[] | null {
  const words: number[] = [];
  for (let index = 0; index < groups.length; index += 1) {
    const group = groups[index] ?? "";
    if (group.includes(".")) {
      if (index !== groups.length - 1) return null;
      const bytes = parseIpv4(group);
      if (!bytes) return null;
      words.push(((bytes[0] ?? 0) << 8) | (bytes[1] ?? 0), ((bytes[2] ?? 0) << 8) | (bytes[3] ?? 0));
      continue;
    }
    if (!/^[0-9a-fA-F]{1,4}$/.test(group)) return null;
    words.push(Number.parseInt(group, 16));
  }
  return words;
}

function parseIpv6(value: string): number[] | null {
  const zoneIndex = value.indexOf("%");
  const text = zoneIndex === -1 ? value : value.slice(0, zoneIndex);
  if (text === "") return null;
  const halves = text.split("::");
  if (halves.length > 2) return null;
  const head = (halves[0] ?? "") === "" ? [] : (halves[0] ?? "").split(":");
  if (halves.length === 1) {
    const words = groupsToWords(head);
    return words && words.length === 8 ? words : null;
  }
  const tailText = halves[1] ?? "";
  const tail = tailText === "" ? [] : tailText.split(":");
  const headWords = groupsToWords(head);
  const tailWords = groupsToWords(tail);
  if (!headWords || !tailWords) return null;
  const missing = 8 - headWords.length - tailWords.length;
  if (missing < 1) return null;
  return [...headWords, ...new Array<number>(missing).fill(0), ...tailWords];
}

function isBlockedIpv4(bytes: readonly number[]): boolean {
  const a = bytes[0] ?? 0;
  const b = bytes[1] ?? 0;
  const c = bytes[2] ?? 0;
  if (a === 0 || a === 10 || a === 127) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 192 && b === 0 && (c === 0 || c === 2)) return true;
  if (a === 192 && b === 88 && c === 99) return true;
  if (a === 198 && (b === 18 || b === 19)) return true;
  if (a === 198 && b === 51 && c === 100) return true;
  if (a === 203 && b === 0 && c === 113) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  return a >= 224;
}

function embeddedIpv4(words: readonly number[], offset: number): number[] {
  return [
    (words[offset] ?? 0) >> 8,
    (words[offset] ?? 0) & 0xff,
    (words[offset + 1] ?? 0) >> 8,
    (words[offset + 1] ?? 0) & 0xff,
  ];
}

function isBlockedIpv6(words: readonly number[]): boolean {
  const first = words[0] ?? 0;
  const second = words[1] ?? 0;
  if (words.every((word) => word === 0)) return true;
  if (words.slice(0, 7).every((word) => word === 0) && words[7] === 1) return true;
  if ((first & 0xfe00) === 0xfc00) return true;
  if ((first & 0xffc0) === 0xfe80) return true;
  if ((first & 0xff00) === 0xff00) return true;
  if (first === 0x2001 && second === 0x0db8) return true;
  if (first === 0x0064 && second === 0xff9b) return true;
  if (first === 0x2001 && second === 0x0000) return true;
  if (words.slice(0, 5).every((word) => word === 0) && words[5] === 0xffff) {
    return isBlockedIpv4(embeddedIpv4(words, 6));
  }
  if (words.slice(0, 6).every((word) => word === 0)) {
    return isBlockedIpv4(embeddedIpv4(words, 6));
  }
  if (first === 0x2002) {
    return isBlockedIpv4(embeddedIpv4(words, 1));
  }
  return false;
}

/** Returns the rejection reason, or `null` when the literal address is a permitted public one. */
export function classifyAddress(address: string): string | null {
  const text = stripBrackets(address.trim());
  const ipv4 = parseIpv4(text);
  if (ipv4) {
    return isBlockedIpv4(ipv4) ? "non-public IPv4 address" : null;
  }
  const ipv6 = parseIpv6(text);
  if (ipv6) {
    return isBlockedIpv6(ipv6) ? "non-public IPv6 address" : null;
  }
  return "not an IP literal";
}

/**
 * Resolves the endpoint and refuses the request when *any* answer is non-public,
 * so a mixed public/private record set cannot be used to reach a private host.
 */
export async function resolvePublicEndpoint(
  endpoint: ProviderEndpoint,
  resolver: AddressResolver,
  resolveTimeoutMs = CONNECT_TIMEOUT_MS,
): Promise<{ address: string; family: 4 | 6 }> {
  if (isIP(endpoint.hostname) !== 0) {
    const reason = classifyAddress(endpoint.hostname);
    if (reason) {
      throw new AppError(400, "PROVIDER_ENDPOINT_REJECTED", `Provider host is blocked: ${reason}`);
    }
    return { address: endpoint.hostname, family: isIP(endpoint.hostname) === 6 ? 6 : 4 };
  }

  const addresses = await withTimeout(resolver(endpoint.hostname), resolveTimeoutMs);
  if (addresses.length === 0) {
    throw new AppError(400, "PROVIDER_ENDPOINT_REJECTED", "Provider host did not resolve");
  }
  for (const address of addresses) {
    const reason = classifyAddress(address);
    if (reason) {
      throw new AppError(400, "PROVIDER_ENDPOINT_REJECTED", `Provider host resolves to a blocked target: ${reason}`);
    }
  }
  const chosen = addresses[0] as string;
  return { address: chosen, family: isIP(chosen) === 6 ? 6 : 4 };
}

async function withTimeout<T>(operation: Promise<T>, timeoutMs: number): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  try {
    return await Promise.race([
      operation,
      new Promise<never>((_resolve, reject) => {
        timer = setTimeout(() => reject(new Error("DNS resolution timed out")), timeoutMs);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export function modelsPath(url: URL): string {
  return `${url.pathname.replace(/\/+$/, "")}/models`;
}

export function mapStatusToErrorCode(status: number): ProviderErrorCode | null {
  if (status === 401 || status === 403) return "unauthorized";
  if (status === 429) return "rate_limited";
  if (status >= 200 && status < 300) return null;
  return "provider_error";
}

export interface ConnectionTestOptions {
  endpoint: ProviderEndpoint;
  apiKey: string;
  resolver?: AddressResolver;
  now?: () => Date;
}

/**
 * Fixed-shape probe against an OpenAI-compatible `GET /models`. The caller cannot
 * supply method, path, headers or body, so the request cannot be repurposed.
 */
export async function testProviderConnection(
  options: ConnectionTestOptions,
): Promise<ConnectionTestResult> {
  const resolver = options.resolver ?? systemAddressResolver;
  const now = options.now ?? (() => new Date());
  const startedAt = Date.now();
  const checkedAt = () => now().toISOString();

  let pinned: { address: string; family: 4 | 6 };
  try {
    pinned = await resolvePublicEndpoint(options.endpoint, resolver);
  } catch (error) {
    const timedOut = error instanceof Error && error.message === "DNS resolution timed out";
    return {
      ok: false,
      latencyMs: elapsed(startedAt),
      checkedAt: checkedAt(),
      errorCode: timedOut ? "timeout" : "dns_rejected",
    };
  }

  try {
    const status = await performPinnedRequest(options.endpoint, pinned, options.apiKey);
    const errorCode = mapStatusToErrorCode(status);
    return {
      ok: errorCode === null,
      latencyMs: elapsed(startedAt),
      checkedAt: checkedAt(),
      errorCode,
    };
  } catch (error) {
    return {
      ok: false,
      latencyMs: elapsed(startedAt),
      checkedAt: checkedAt(),
      errorCode: classifyRequestError(error),
    };
  }
}

function elapsed(startedAt: number): number {
  return Math.min(TOTAL_TIMEOUT_MS, Math.max(0, Date.now() - startedAt));
}

function classifyRequestError(error: unknown): ProviderErrorCode {
  const code = (error as NodeJS.ErrnoException).code;
  if (code === "ETIMEDOUT" || code === "ERR_SOCKET_CONNECTION_TIMEOUT" || code === "ESOCKETTIMEDOUT") {
    return "timeout";
  }
  if (
    typeof code === "string" &&
    (code.startsWith("ERR_TLS") ||
      code.startsWith("CERT_") ||
      code === "DEPTH_ZERO_SELF_SIGNED_CERT" ||
      code === "UNABLE_TO_VERIFY_LEAF_SIGNATURE")
  ) {
    return "tls_error";
  }
  if (code === "ERR_RESPONSE_BODY_TOO_LARGE" || code === "ERR_INVALID_RESPONSE_BODY") {
    return "invalid_response";
  }
  return "provider_error";
}

interface PinnedAddress {
  address: string;
  family: 4 | 6;
}

/**
 * Node may request every address at once (`options.all`) for happy-eyeballs.
 * Both shapes return the single validated address, so the socket can only ever
 * connect to the destination that was checked.
 */
function pinnedLookup(pinned: PinnedAddress) {
  return (
    _hostname: string,
    options: { all?: boolean },
    callback: (
      error: NodeJS.ErrnoException | null,
      address: string | Array<{ address: string; family: number }>,
      family?: number,
    ) => void,
  ): void => {
    if (options.all) {
      callback(null, [{ address: pinned.address, family: pinned.family }]);
      return;
    }
    callback(null, pinned.address, pinned.family);
  };
}

function performPinnedRequest(
  endpoint: ProviderEndpoint,
  pinned: PinnedAddress,
  apiKey: string,
): Promise<number> {
  return new Promise<number>((resolve, reject) => {
    // The socket destination is the address that was validated: no second DNS
    // lookup happens, so a rebinding record cannot redirect the connection.
    const request = httpsRequest(
      {
        protocol: "https:",
        hostname: endpoint.hostname,
        port: endpoint.url.port === "" ? 443 : Number(endpoint.url.port),
        path: modelsPath(endpoint.url),
        method: "GET",
        servername: endpoint.hostname,
        headers: {
          authorization: `Bearer ${apiKey}`,
          accept: "application/json",
          "user-agent": "vbrpg-connection-test/1",
        },
        timeout: CONNECT_TIMEOUT_MS,
        lookup: pinnedLookup(pinned) as never,
      },
      (response) => {
        let received = 0;
        const status = response.statusCode ?? 0;
        response.on("data", (chunk: Buffer) => {
          received += chunk.length;
          if (received > MAX_RESPONSE_BYTES) {
            const error: NodeJS.ErrnoException = new Error("Provider response exceeded the size limit");
            error.code = "ERR_RESPONSE_BODY_TOO_LARGE";
            request.destroy();
            reject(error);
          }
        });
        response.on("end", () => resolve(status));
        response.on("error", reject);
      },
    );

    const totalTimer = setTimeout(() => {
      const error: NodeJS.ErrnoException = new Error("Provider connection test timed out");
      error.code = "ETIMEDOUT";
      request.destroy(error);
      reject(error);
    }, TOTAL_TIMEOUT_MS);

    const finish = () => clearTimeout(totalTimer);
    request.on("timeout", () => {
      const error: NodeJS.ErrnoException = new Error("Provider connection timed out");
      error.code = "ETIMEDOUT";
      request.destroy(error);
    });
    request.on("close", finish);
    request.on("error", (error) => {
      finish();
      reject(error);
    });
    request.end();
  });
}
