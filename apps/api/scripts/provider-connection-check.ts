import { parseProviderEndpoint, testProviderConnection } from "../src/provider-endpoint.js";

/**
 * Live smoke check for the pinned connection-test path. Requires outbound network
 * access and is therefore not part of the default test run; use it when validating
 * SSRF controls against real public endpoints.
 *
 * Usage: pnpm --filter @vbrpg/api exec tsx scripts/provider-connection-check.ts [baseUrl]
 */
const targets = process.argv.slice(2);
const baseUrls = targets.length > 0 ? targets : ["https://api.openai.com/v1", "https://example.com"];

let failures = 0;
for (const baseUrl of baseUrls) {
  const result = await testProviderConnection({
    endpoint: parseProviderEndpoint(baseUrl),
    apiKey: "sk-invalid-not-a-real-key",
  });
  const reachable = result.errorCode !== "dns_rejected" && result.errorCode !== "tls_error";
  console.log(JSON.stringify({ baseUrl, reachable, ...result }));
  if (!reachable) failures += 1;
}

// A `dns_rejected` or `tls_error` here means the request never reached the provider.
if (failures > 0) {
  console.error(`${failures} of ${baseUrls.length} endpoints were not reachable through the pinned path`);
  process.exitCode = 1;
}
