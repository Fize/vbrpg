import { describe, expect, it } from "vitest";
import { loadConfig } from "./config.js";

describe("API configuration", () => {
  it("uses the platform key for the Tencent TokenHub Hy3 default", () => {
    const config = loadConfig({
      NODE_ENV: "test",
      DEEPSEEK_API_KEY: "deepseek-key",
    });

    expect(config.aiApiKey).toBe("deepseek-key");
    expect(config.aiApiBaseUrl).toBe("https://tokenhub.tencentmaas.com/v1");
    expect(config.aiModel).toBe("hy3");
    expect(config.aiContextWindowTokens).toBe(262_144);
    expect(config.aiMaxInputTokens).toBe(196_608);
    expect(config.aiReserveOutputTokens).toBe(16_384);
  });

  it("uses OPENAI_API_KEY when AI_API_KEY is not set", () => {
    const config = loadConfig({
      NODE_ENV: "test",
      OPENAI_API_KEY: "openai-compatible-key",
      AI_API_BASE_URL: "https://example.test/v1",
    });

    expect(config.aiApiKey).toBe("openai-compatible-key");
  });
});
