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


// ── Example: Login component using authService directly ───────────────────────
//
// import { useState } from "react";
// import { useNavigate } from "react-router-dom";
// import { authService } from "../api/auth";
// import { useAuth } from "../context/AuthContext";
//
// export default function LoginForm() {
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [error,    setError]    = useState("");
//   const [loading,  setLoading]  = useState(false);
//   const { login }  = useAuth();
//   const navigate   = useNavigate();
//
//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     setError("");
//     setLoading(true);
//     try {
//       const { token, user } = await authService.login(username, password);
//       //
//       // What happens next in the network tab (CORRECT behavior after fix):
//       // Request:  POST http://localhost/api/auth/login    ← same origin, port 80
//       // Nginx:    strips /api → POST http://auth-service:8001/auth/login
//       // Response: 200 { access_token, user_id, username }
//       //
//       // WRONG behavior (before fix):
//       // Request:  POST http://localhost:8001/auth/login   ← direct port hit
//       // Browser:  ERR_BLOCKED_BY_CLIENT (ad blocker / CORS / port not exposed)
//       //
//       login(token, user);
//       navigate("/dashboard");
//     } catch (err) {
//       setError(err.response?.data?.detail || "Login failed");
//     } finally {
//       setLoading(false);
//     }
//   };
//
//   return (
//     <form onSubmit={handleSubmit}>
//       <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" />
//       <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" />
//       {error && <p style={{ color: "red" }}>{error}</p>}
//       <button type="submit" disabled={loading}>{loading ? "Signing in…" : "Sign In"}</button>
//     </form>
//   );
// }
