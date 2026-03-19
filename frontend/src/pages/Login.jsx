import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, parseApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [mode,    setMode]    = useState("login"); // "login" | "register"
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");      // always a string now
  const { login } = useAuth();
  const navigate  = useNavigate();

  const [form, setForm] = useState({
    username: "", password: "", email: "", full_name: "",
  });

  const set = (field) => (e) => {
    setError("");
    setForm((f) => ({ ...f, [field]: e.target.value }));
  };

  // ── Client-side validation (runs before any API call) ──────────────────────
  const validate = () => {
    if (!form.username.trim()) return "Username is required.";
    if (form.username.trim().length < 3) return "Username must be at least 3 characters.";
    if (!form.password)        return "Password is required.";
    if (form.password.length < 8) return "Password must be at least 8 characters.";
    if (mode === "register") {
      if (!form.email.trim())  return "Email is required.";
      // Basic email format check — FastAPI's EmailStr is stricter, but catch the obvious cases
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return "Enter a valid email address.";
    }
    return null; // all good
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setLoading(true);
    try {
      const payload =
        mode === "login"
          ? { username: form.username.trim().toLowerCase(), password: form.password }
          : {
              username:  form.username.trim().toLowerCase(),
              password:  form.password,
              email:     form.email.trim(),
              full_name: form.full_name.trim() || undefined,
            };

      const res = mode === "login"
        ? await api.login(payload)
        : await api.register(payload);

      const { access_token, user_id, username } = res.data;
      login(access_token, { user_id, username });

      // Auto-create a checking account on first register
      if (mode === "register") {
        try { await api.openAccount("checking"); } catch (_) { /* non-fatal */ }
      }

      navigate("/dashboard");
    } catch (err) {
      // ← parseApiError handles both string and array detail shapes safely
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      {/* Ambient background effects */}
      <div style={styles.orb1} />
      <div style={styles.orb2} />

      <div style={styles.card}>
        {/* Logo */}
        <div style={styles.logo}>
          <div style={styles.logoIcon}>⬡</div>
          <span style={styles.logoText}>VAULTX</span>
        </div>
        <p style={styles.tagline}>
          {mode === "login" ? "Sign in to your account" : "Open your account"}
        </p>

        {/* Tab switcher */}
        <div style={styles.tabs}>
          {["login", "register"].map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(""); }}
              style={{ ...styles.tab, ...(mode === m ? styles.tabActive : {}) }}
            >
              {m === "login" ? "Sign In" : "Register"}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={styles.form}>
          {mode === "register" && (
            <>
              <Field label="Full Name" type="text" value={form.full_name}
                     onChange={set("full_name")} placeholder="Jane Smith" />
              <Field label="Email *" type="email" value={form.email}
                     onChange={set("email")} placeholder="jane@example.com" />
            </>
          )}
          <Field label="Username *" type="text" value={form.username}
                 onChange={set("username")} placeholder="your_username" />
          <Field label="Password *" type="password" value={form.password}
                 onChange={set("password")} placeholder="•••••••• (min 8 chars)" />

          {/* error is always a string here — no React Error #31 risk */}
          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" style={styles.btn} disabled={loading}>
            {loading ? <Spinner /> : (mode === "login" ? "Sign In" : "Create Account")}
          </button>
        </form>

        {/*mode === "login" && (
          <p style={styles.hint}>
            Demo credentials: <code style={styles.code}>demo / password123</code>
          </p>
        )*/}
      </div>
    </div>
  );
}

function Field({ label, ...props }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={styles.field}>
      <label style={styles.label}>{label}</label>
      <input
        {...props}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{ ...styles.input, ...(focused ? styles.inputFocused : {}) }}
      />
    </div>
  );
}

function Spinner() {
  return (
    <span style={styles.spinner} />
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const styles = {
  page: {
    minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
    background: "#080c14", position: "relative", overflow: "hidden", padding: "24px",
    fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
  },
  orb1: {
    position: "absolute", width: 500, height: 500, borderRadius: "50%",
    background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)",
    top: -100, left: -100, pointerEvents: "none",
  },
  orb2: {
    position: "absolute", width: 400, height: 400, borderRadius: "50%",
    background: "radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%)",
    bottom: -80, right: -80, pointerEvents: "none",
  },
  card: {
    background: "rgba(255,255,255,0.04)", backdropFilter: "blur(24px)",
    border: "1px solid rgba(255,255,255,0.08)", borderRadius: 20,
    padding: "40px 36px", width: "100%", maxWidth: 420, position: "relative",
    boxShadow: "0 32px 80px rgba(0,0,0,0.5)",
  },
  logo:     { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 },
  logoIcon: { fontSize: 28, color: "#6366f1", lineHeight: 1, textShadow: "0 0 20px rgba(99,102,241,0.7)" },
  logoText: {
    fontSize: 22, fontWeight: 800, letterSpacing: "0.15em",
    background: "linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%)",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
  },
  tagline:  { color: "#64748b", fontSize: 14, marginBottom: 28 },
  tabs: {
    display: "flex", background: "rgba(255,255,255,0.04)",
    borderRadius: 10, padding: 4, marginBottom: 28, gap: 4,
  },
  tab: {
    flex: 1, padding: "8px 0", border: "none", borderRadius: 8,
    background: "transparent", color: "#64748b", fontSize: 14,
    fontWeight: 600, cursor: "pointer", transition: "all 0.2s",
  },
  tabActive: {
    background: "rgba(99,102,241,0.2)", color: "#e2e8f0",
    boxShadow: "0 0 0 1px rgba(99,102,241,0.3)",
  },
  form:  { display: "flex", flexDirection: "column", gap: 18 },
  field: { display: "flex", flexDirection: "column", gap: 6 },
  label: { color: "#94a3b8", fontSize: 12, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
  input: {
    background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 10, padding: "12px 16px", color: "#e2e8f0", fontSize: 15,
    outline: "none", transition: "all 0.2s", width: "100%", boxSizing: "border-box",
  },
  inputFocused: {
    border: "1px solid rgba(99,102,241,0.6)",
    boxShadow: "0 0 0 3px rgba(99,102,241,0.1)",
    background: "rgba(99,102,241,0.05)",
  },
  error: {
    background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)",
    borderRadius: 8, padding: "10px 14px", color: "#f87171", fontSize: 13,
    lineHeight: 1.5,
  },
  btn: {
    padding: "14px 24px", borderRadius: 10, border: "none",
    background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
    color: "#fff", fontWeight: 700, fontSize: 15, cursor: "pointer",
    marginTop: 4, display: "flex", alignItems: "center", justifyContent: "center",
    boxShadow: "0 4px 24px rgba(99,102,241,0.35)", transition: "opacity 0.2s",
    minHeight: 48,
  },
  hint:    { color: "#475569", fontSize: 13, marginTop: 20, textAlign: "center" },
  code:    { color: "#94a3b8", background: "rgba(255,255,255,0.06)", padding: "2px 6px", borderRadius: 4, fontSize: 12 },
  spinner: {
    display: "inline-block", width: 18, height: 18,
    border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff",
    borderRadius: "50%", animation: "spin 0.7s linear infinite",
  },
};