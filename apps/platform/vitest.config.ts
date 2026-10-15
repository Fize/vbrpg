import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: {
    projects: [
      {
        test: {
          name: "server",
          environment: "node",
          include: ["src/server/**/*.test.ts", "src/shared/**/*.test.ts"],
        },
      },
      {
        test: {
          name: "browser",
          environment: "happy-dom",
          include: ["src/browser/**/*.test.ts"],
        },
      },
    ],
  },
});
