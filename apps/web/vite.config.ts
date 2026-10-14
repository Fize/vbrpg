import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/v1": {
        target: process.env.API_PROXY_TARGET ?? "http://localhost:3000",
        changeOrigin: false,
      },
    },
  },
});
