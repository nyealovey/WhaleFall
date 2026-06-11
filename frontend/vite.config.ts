import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "/console/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src")
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:5001",
        changeOrigin: true
      },
      "/static": {
        target: "http://127.0.0.1:5001",
        changeOrigin: true
      }
    }
  },
  test: {
    setupFiles: "./src/setupTests.ts"
  }
});
