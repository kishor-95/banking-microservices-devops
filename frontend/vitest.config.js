import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  // ── Vitest ────────────────────────────────────────────────────────────────
  test: {
    globals:      true,
    environment:  "jsdom",
    setupFiles:   "./src/__tests__/setup.js",
    clearMocks:   true,
  },

  server: {
    port: 3000,
    proxy: {
      // /api/auth/* → http://localhost:8001/auth/*
      "/api/auth": {
        target:      "http://localhost:8001",
        changeOrigin: true,
        rewrite:     (path) => path.replace(/^\/api/, ""),
      },
      // /api/accounts/* → http://localhost:8002/accounts/*
      "/api/accounts": {
        target:      "http://localhost:8002",
        changeOrigin: true,
        rewrite:     (path) => path.replace(/^\/api/, ""),
      },
      // /api/balance/* → http://localhost:8003/balance/*
      "/api/balance": {
        target:      "http://localhost:8003",
        changeOrigin: true,
        rewrite:     (path) => path.replace(/^\/api/, ""),
      },
      // /api/transactions/* → http://localhost:8004/transactions/*
      "/api/transactions": {
        target:      "http://localhost:8004",
        changeOrigin: true,
        rewrite:     (path) => path.replace(/^\/api/, ""),
      },
    },
  },

  build: {
    outDir:    "dist",
    sourcemap: false,
  },
});