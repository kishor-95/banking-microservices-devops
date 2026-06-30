/**
 * src/api/auth.js
 *
 * Standalone auth service module — shows exactly how to call auth endpoints
 * using the fixed relative-path pattern. Use this as the reference pattern
 * for any new service file added to the project.
 *
 * USAGE IN A COMPONENT:
 * ──────────────────────────────────────────────────────────────────────────────
 *   import { authService } from "../api/auth";
 *
 *   // Login
 *   const { token, user } = await authService.login("demo", "password123");
 *
 *   // Register
 *   const { token, user } = await authService.register({
 *     username: "jane", password: "secret99", email: "jane@co.com", full_name: "Jane"
 *   });
 *
 *   // Verify token (e.g. on app boot to check if stored token is still valid)
 *   const isValid = await authService.verifyToken();
 */

import client from "./client";   // ← the single shared Axios instance

export const authService = {
  /**
   * POST /api/auth/login
   * Returns: { token: string, user: { user_id, username } }
   */
  async login(username, password) {
    const res = await client.post("/api/auth/login", { username, password });
    return {
      token: res.data.access_token,
      user:  { user_id: res.data.user_id, username: res.data.username },
    };
  },

  /**
   * POST /api/auth/register
   * Returns: { token: string, user: { user_id, username } }
   */
  async register({ username, password, email, full_name }) {
    const res = await client.post("/api/auth/register", {
      username, password, email, full_name,
    });
    return {
      token: res.data.access_token,
      user:  { user_id: res.data.user_id, username: res.data.username },
    };
  },

  /**
   * GET /api/auth/verify
   * Verifies the JWT currently in localStorage.
   * Returns true if valid, false if expired/missing.
   * Does NOT throw — safe to call on app boot.
   */
  async verifyToken() {
    try {
      await client.get("/api/auth/verify");
      return true;
    } catch {
      return false;
    }
  },
};