import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  test: {
    projects: [
      {
        plugins: [vue()],
        test: {
          name: "server",
          environment: "node",
          include: ["src/server/**/*.test.ts", "src/shared/**/*.test.ts"],
        },
      },
      {
        plugins: [vue()],
        test: {
          name: "browser",
          environment: "happy-dom",
          include: ["src/browser/**/*.test.ts"],
        },
      },
    ],
  },
});
