import { useState, useEffect } from "react";
import { api } from "../api/client";

const money   = (n) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
const fmtDate = (d) => new Date(d).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

export default function UserProfileModal({ onClose, accounts, balances }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProfile()
      .then((res) => setProfile(res.data))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  const totalBalance = Object.values(balances).reduce((s, b) => s + b, 0);
  const initials = profile
    ? (profile.full_name || profile.username)
        .split(" ").slice(0, 2).map((w) => w[0].toUpperCase()).join("")
    : "?";

  const handleBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div style={p.backdrop} onClick={handleBackdrop}>
      <div style={p.modal}>

        {/* ── Header ──────────────────────────────────────────────── */}
        <div style={p.header}>
          <span style={p.title}>My Profile</span>
          <button style={p.closeBtn} onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div style={p.loading}>Loading profile…</div>
        ) : profile ? (
          <>
            {/* ── Avatar + name block ─────────────────────────────── */}
            <div style={p.hero}>
              <div style={p.avatar}>{initials}</div>
              <div>
                <p style={p.fullName}>{profile.full_name || profile.username}</p>
                <p style={p.subLine}>@{profile.username}</p>
              </div>
            </div>

            {/* ── Profile details ─────────────────────────────────── */}
            <div style={p.section}>
              <p style={p.sectionTitle}>Account Info</p>
              <Row label="Username"    value={`@${profile.username}`} />
              <Row label="Email"       value={profile.email} />
              <Row label="Full Name"   value={profile.full_name || "—"} />
              <Row label="Member Since" value={fmtDate(profile.created_at)} />
            </div>

            {/* ── Portfolio summary ───────────────────────────────── */}
            <div style={p.section}>
              <p style={p.sectionTitle}>Portfolio</p>

              <div style={p.totalRow}>
                <span style={p.totalLabel}>Total Balance</span>
                <span style={p.totalValue}>{money(totalBalance)}</span>
              </div>

              <div style={p.accountsList}>
                {accounts.map((acc) => (
                  <div key={acc.id} style={p.accRow}>
                    <div style={p.accLeft}>
                      <div style={{
                        ...p.accDot,
                        background: acc.account_type === "checking"
                          ? "rgba(99,102,241,0.2)" : "rgba(16,185,129,0.2)",
                        color: acc.account_type === "checking" ? "#a5b4fc" : "#6ee7b7",
                      }}>
                        {acc.account_type === "checking" ? "C" : "S"}
                      </div>
                      <div>
                        <p style={p.accType}>
                          {acc.account_type === "checking" ? "Current" : "Savings"}
                        </p>
                        <p style={p.accNum}>
                          •••• {acc.account_number?.slice(-4)}
                        </p>
                      </div>
                    </div>
                    <span style={p.accBal}>{money(balances[acc.id] ?? 0)}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div style={p.loading}>Could not load profile.</div>
        )}

        <button style={p.doneBtn} onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={p.row}>
      <span style={p.rowLabel}>{label}</span>
      <span style={p.rowValue}>{value}</span>
    </div>
  );
}

const p = {
  backdrop:    { position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 },
  modal:       { background: "#0f1623", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, width: "100%", maxWidth: 420, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 40px 100px rgba(0,0,0,0.6)", fontFamily: "'DM Sans','Segoe UI',sans-serif" },
  header:      { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 24px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)" },
  title:       { color: "#e2e8f0", fontSize: 16, fontWeight: 700 },
  closeBtn:    { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#64748b", width: 32, height: 32, cursor: "pointer", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center" },
  loading:     { color: "#475569", textAlign: "center", padding: "40px 24px", fontSize: 14 },

  hero:        { display: "flex", alignItems: "center", gap: 16, padding: "24px 24px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)" },
  avatar:      { width: 56, height: 56, borderRadius: "50%", background: "linear-gradient(135deg,#6366f1,#4f46e5)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 800, color: "#fff", flexShrink: 0, boxShadow: "0 4px 20px rgba(99,102,241,0.4)" },
  fullName:    { color: "#e2e8f0", fontSize: 18, fontWeight: 800, margin: 0, marginBottom: 4 },
  subLine:     { color: "#64748b", fontSize: 13, margin: 0 },

  section:     { padding: "20px 24px 0" },
  sectionTitle:{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em", color: "#475569", marginBottom: 12, marginTop: 0 },
  row:         { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" },
  rowLabel:    { color: "#64748b", fontSize: 13 },
  rowValue:    { color: "#cbd5e1", fontSize: 13, fontWeight: 600, textAlign: "right", maxWidth: "60%", wordBreak: "break-all" },

  totalRow:    { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.15)", borderRadius: 10, marginBottom: 12 },
  totalLabel:  { color: "#94a3b8", fontSize: 13, fontWeight: 600 },
  totalValue:  { fontSize: 18, fontWeight: 800, background: "linear-gradient(135deg,#e2e8f0,#a5b4fc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },

  accountsList:{ display: "flex", flexDirection: "column", gap: 8, paddingBottom: 4 },
  accRow:      { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10 },
  accLeft:     { display: "flex", alignItems: "center", gap: 10 },
  accDot:      { width: 32, height: 32, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 13 },
  accType:     { color: "#cbd5e1", fontSize: 13, fontWeight: 700, margin: 0, marginBottom: 2 },
  accNum:      { color: "#475569", fontSize: 11, margin: 0, letterSpacing: "0.08em" },
  accBal:      { color: "#e2e8f0", fontSize: 14, fontWeight: 800 },

  doneBtn:     { display: "block", width: "calc(100% - 48px)", margin: "20px 24px 24px", padding: "13px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#6366f1,#4f46e5)", color: "#fff", fontWeight: 700, fontSize: 15, cursor: "pointer", boxShadow: "0 4px 20px rgba(99,102,241,0.3)" },
};
