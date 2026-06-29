import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src")
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom") || id.includes("node_modules/react-router-dom")) {
            return "react-vendor";
          }
          if (id.includes("node_modules/@tanstack/react-query") || id.includes("node_modules/@tanstack/react-table")) {
            return "query-table";
          }
          if (id.includes("node_modules/@radix-ui/")) {
            return "radix-ui";
          }
          if (id.includes("node_modules/recharts")) {
            return "charts";
          }
          if (id.includes("node_modules/lucide-react")) {
            return "icons";
          }
        }
      }
    }
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
