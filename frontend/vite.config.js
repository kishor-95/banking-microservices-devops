/**
 * vite.config.js  —  FIXED
 *
 * ROOT CAUSES THIS FILE HAD:
 * ─────────────────────────────────────────────────────────────────────────────
 * 1. Proxy matched bare path prefixes (/auth, /accounts, /balance, /transactions)
 *    with NO /api/ namespace. This collides with React Router paths and is
 *    inconsistent with what Nginx does in production. Any navigation to
 *    "/accounts" would be intercepted by the proxy instead of React Router.
 *
 * 2. No `rewrite` rule → the full path was forwarded verbatim.
 *    /auth/login → http://localhost:8001/auth/login  (OK by accident)
 *    But with /api/ prefix: /api/auth/login → http://localhost:8001/api/auth/login
 *    FastAPI would 404 because it only knows /auth/login (no /api prefix).
 *
 * 3. Vite proxy only runs during `npm run dev`. In the Docker production build,
 *    Vite is not running — Nginx is serving the static bundle. So this proxy
 *    config has ZERO effect in production. The fix is making sure Nginx mirrors
 *    exactly what this proxy does (both strip /api, both route by service prefix).
 *
 * THE FIX:
 * ─────────────────────────────────────────────────────────────────────────────
 * All proxy rules now match /api/<service> and use `rewrite` to strip /api
 * before forwarding to the backend. This mirrors exactly what Nginx does.
 *
 * Dev flow:  browser → Vite dev server (:3000) → strips /api → localhost:800X
 * Prod flow: browser → Nginx (:80) → strips /api → auth-service:8001 (Docker DNS)
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

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
