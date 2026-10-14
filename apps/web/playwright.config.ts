import { defineConfig, devices } from "@playwright/test";

const webPort = 5174;
const apiPort = 3100;
const databaseUrl = process.env.E2E_DATABASE_URL;
const credentialKey = process.env.E2E_CREDENTIAL_KEY;
if (!databaseUrl || !credentialKey) {
  throw new Error("E2E_DATABASE_URL and E2E_CREDENTIAL_KEY are required");
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "pnpm --filter @vbrpg/api dev",
      url: `http://127.0.0.1:${apiPort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
      env: {
        NODE_ENV: "test",
        DATABASE_URL: databaseUrl,
        PLATFORM_CREDENTIAL_KEY: credentialKey,
        TRUSTED_WEB_ORIGINS: `http://127.0.0.1:${webPort}`,
        PORT: String(apiPort),
        LOG_LEVEL: "error",
      },
    },
    {
      command: "pnpm --filter @vbrpg/web dev --host 127.0.0.1 --port 5174",
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
      env: {
        // 开发服务器把 /v1 反向代理到 API；缺省值指向 3000，本机可能被其他进程占用。
        API_PROXY_TARGET: `http://127.0.0.1:${apiPort}`,
      },
    },
  ],
});
