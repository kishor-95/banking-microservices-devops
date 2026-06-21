
import axios from "axios";

// ── Token helpers ─────────────────────────────────────────────────────────────
export const getToken  = ()  => localStorage.getItem("token");
export const setToken  = (t) => localStorage.setItem("token", t);
export const setUser   = (u) => localStorage.setItem("user", JSON.stringify(u));
export const getUser   = ()  => JSON.parse(localStorage.getItem("user") || "null");
export const clearAuth = ()  => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
};
export const isLoggedIn = () => !!getToken();

// ── Single Axios instance — baseURL is empty (same-origin relative) ───────────
const client = axios.create({
  baseURL: "",          // ← relative: uses window.location.origin automatically
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT on every outbound request
client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 401 → clear auth state and redirect to login
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      clearAuth();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── API surface ───────────────────────────────────────────────────────────────
// All paths use /api/ prefix:
//   Dev  → Vite proxy strips /api and forwards to localhost:800X
//   Prod → Nginx strips /api and proxies to Docker service name:port
//
// FastAPI routes stay unchanged (/auth/login, /accounts/me, etc.)
export const api = {
  // ── auth-service (/api/auth → http://auth-service:8001) ────────────────────
  login:    (data) => client.post("/api/auth/login", data),
  register: (data) => client.post("/api/auth/register", data),
  verify:   ()     => client.get("/api/auth/verify"),

  // ── account-service (/api/accounts → http://account-service:8002) ──────────
  getProfile:   ()     => client.get("/api/accounts/profile"),
  getAccounts:  ()     => client.get("/api/accounts/me"),
  openAccount:  (type) => client.post("/api/accounts", { account_type: type }),
  closeAccount: (id)   => client.delete(`/api/accounts/${id}`),

  // ── balance-service (/api/balance → http://balance-service:8003) ───────────
  getAllBalances: ()   => client.get("/api/balance"),
  getBalance:    (id) => client.get(`/api/balance/${id}`),

  // ── transaction-service (/api/transactions → http://transaction-service:8004)
  deposit:    (data)                          => client.post("/api/transactions/deposit", data),
  withdraw:   (data)                          => client.post("/api/transactions/withdraw", data),
  getHistory: (accountId, limit=20, offset=0) =>
    client.get(`/api/transactions/${accountId}?limit=${limit}&offset=${offset}`),
};

export default client;

// ── Error parser ──────────────────────────────────────────────────────────────
/**
 * parseApiError(err) → string
 *
 * FastAPI can return `detail` in two shapes:
 *   • string:  { "detail": "Invalid credentials" }          ← 401/403/404
 *   • array:   { "detail": [{ loc, msg, type }, ...] }      ← 422 validation
 *
 * React Error #31 happens when you do setError(array) and then render {error}
 * in JSX — React cannot render a plain object as a child.
 *
 * This function always returns a plain string safe to pass to setError().
 */
export function parseApiError(err, fallback = "Something went wrong. Try again.") {
  const detail = err?.response?.data?.detail;

  if (!detail) return fallback;

  // Shape 1: plain string
  if (typeof detail === "string") return detail;

  // Shape 2: FastAPI validation array → [ { loc: ["body","email"], msg: "..." } ]
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "field";
        const msg   = e.msg || "invalid";
        // Capitalise field name and clean up FastAPI's internal prefixes
        const label = String(field).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        return `${label}: ${msg}`;
      })
      .join(" · ");
  }

  return fallback;
}
