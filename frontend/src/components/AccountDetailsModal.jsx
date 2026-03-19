import { useState, useEffect } from "react";
import { api, parseApiError } from "../api/client";

const money   = (n) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
const fmtDate = (d) => new Date(d).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

export default function AccountDetailsModal({ account, balance, history = [], onClose, onAccountClosed }) {
  const [profile,      setProfile]      = useState(null);
  const [confirmStep,  setConfirmStep]  = useState(false);
  const [confirmInput, setConfirmInput] = useState("");
  const [closing,      setClosing]      = useState(false);
  const [closeError,   setCloseError]   = useState("");

  useEffect(() => {
    api.getProfile()
      .then((res) => setProfile(res.data))
      .catch(() => setProfile(null));
  }, []);

  const totalDeposits    = history.filter((t) => t.type === "DEPOSIT").reduce((s, t) => s + t.amount, 0);
  const totalWithdrawals = history.filter((t) => t.type === "WITHDRAW").reduce((s, t) => s + t.amount, 0);
  const txnCount         = history.length;
  const isChecking       = account.account_type === "checking";
  const hasBalance       = balance > 0;

  const handleBackdrop = (e) => {
    if (e.target === e.currentTarget && !confirmStep) onClose();
  };

  const handleCloseAccount = async () => {
    if (confirmInput !== "CLOSE") return;
    setClosing(true);
    setCloseError("");
    try {
      await api.closeAccount(account.id);
      onAccountClosed(account.id);
      onClose();
    } catch (err) {
      setCloseError(parseApiError(err, "Failed to close account."));
      setClosing(false);
    }
  };

  return (
    <div style={m.backdrop} onClick={handleBackdrop}>
      <div style={m.modal}>

        {/* Header */}
        <div style={m.header}>
          <div style={m.headerLeft}>
            <div style={{ ...m.typeChip, background: isChecking ? "rgba(99,102,241,0.15)" : "rgba(16,185,129,0.15)", color: isChecking ? "#a5b4fc" : "#6ee7b7" }}>
              {account.account_type.toUpperCase()}
            </div>
            <span style={m.title}>Account Details</span>
          </div>
          {!confirmStep && (
            <button style={m.closeBtn} onClick={onClose}>✕</button>
          )}
        </div>

        {/* Confirm close panel */}
        {confirmStep ? (
          <div style={m.confirmPanel}>
            <div style={m.warnIcon}>⚠️</div>
            <h3 style={m.confirmTitle}>Close this account?</h3>
            <p style={m.confirmDesc}>
              This permanently deactivates account ending in{" "}
              <strong style={{ color: "#e2e8f0" }}>
                ••••&nbsp;{account.account_number?.slice(-4)}
              </strong>
              . Your transaction history is preserved but the account can't be used again.
            </p>

            {hasBalance && (
              <div style={m.blocker}>
                <span style={m.blockerIcon}>💰</span>
                <span>Withdraw your remaining <strong>{money(balance)}</strong> balance first</span>
              </div>
            )}

            {!hasBalance && (
              <>
                <p style={m.confirmPrompt}>
                  Type <strong style={{ color: "#f87171" }}>CLOSE</strong> to confirm
                </p>
                <input
                  value={confirmInput}
                  onChange={(e) => { setConfirmInput(e.target.value.toUpperCase()); setCloseError(""); }}
                  placeholder="CLOSE"
                  style={m.confirmInput}
                  autoFocus
                />
                {closeError && <div style={m.closeErrBox}>{closeError}</div>}
              </>
            )}

            <div style={m.confirmBtns}>
              <button
                style={m.cancelBtn}
                onClick={() => { setConfirmStep(false); setConfirmInput(""); setCloseError(""); }}
              >
                Cancel
              </button>
              {!hasBalance && (
                <button
                  style={{
                    ...m.destructBtn,
                    opacity: confirmInput === "CLOSE" && !closing ? 1 : 0.4,
                    cursor: confirmInput === "CLOSE" && !closing ? "pointer" : "not-allowed",
                  }}
                  disabled={confirmInput !== "CLOSE" || closing}
                  onClick={handleCloseAccount}
                >
                  {closing ? "Closing…" : "Close Account"}
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Balance hero */}
            <div style={{ ...m.balanceBlock, background: isChecking ? "linear-gradient(135deg,#1e1b4b,#312e81)" : "linear-gradient(135deg,#064e3b,#065f46)" }}>
              <p style={m.balLabel}>Current Balance</p>
              <p style={m.balAmount}>{money(balance)}</p>
              <p style={m.balAccNum}>{account.account_number?.replace(/(.{4})/g, "$1 ").trim()}</p>
            </div>

            {/* Account info */}
            <div style={m.section}>
              <p style={m.sectionTitle}>Account Info</p>
              <DetailRow label="Account ID"   value={`#${account.id}`} />
              <DetailRow label="Account Type" value={account.account_type === "checking" ? "Current" : "Savings"} />
              <DetailRow
                label="Status"
                value={account.is_active ? "Active" : "Inactive"}
                valueStyle={{ color: account.is_active ? "#10b981" : "#f87171", fontWeight: 700 }}
              />
              <DetailRow label="Opened" value={fmtDate(account.created_at)} />
            </div>

            {/* Owner profile */}
            <div style={m.section}>
              <p style={m.sectionTitle}>Account Owner</p>
              {profile ? (
                <>
                  <DetailRow label="Full Name"    value={profile.full_name || "—"} />
                  <DetailRow label="Username"     value={`@${profile.username}`} />
                  <DetailRow label="Email"        value={profile.email} />
                  <DetailRow label="Member Since" value={fmtDate(profile.created_at)} />
                </>
              ) : (
                <p style={m.loading}>Loading…</p>
              )}
            </div>

            {/* Mini stats */}
            <div style={m.section}>
              <p style={m.sectionTitle}>Activity Summary <span style={m.histNote}>(current page)</span></p>
              <div style={m.statsRow}>
                <StatBox label="Deposits"     value={money(totalDeposits)}    color="#10b981" />
                <StatBox label="Withdrawals"  value={money(totalWithdrawals)} color="#f59e0b" />
                <StatBox label="Transactions" value={String(txnCount)}        color="#6366f1" />
              </div>
            </div>

            {/* Danger zone */}
            {account.is_active && (
              <div style={m.dangerZone}>
                <div style={m.dangerHeader}>
                  <span style={m.dangerTitle}>⚠ Danger Zone</span>
                </div>
                <div style={m.dangerBody}>
                  <div>
                    <p style={m.dangerLabel}>Close Account</p>
                    <p style={m.dangerHint}>
                      {hasBalance
                        ? `Withdraw ${money(balance)} before closing.`
                        : "Permanently deactivate this account."}
                    </p>
                  </div>
                  <button style={m.dangerBtn} onClick={() => setConfirmStep(true)}>
                    Close Account
                  </button>
                </div>
              </div>
            )}

            <button style={m.doneBtn} onClick={onClose}>Done</button>
          </>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value, valueStyle = {} }) {
  return (
    <div style={m.row}>
      <span style={m.rowLabel}>{label}</span>
      <span style={{ ...m.rowValue, ...valueStyle }}>{value}</span>
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div style={m.statBox}>
      <span style={{ ...m.statValue, color }}>{value}</span>
      <span style={m.statLabel}>{label}</span>
    </div>
  );
}

const m = {
  backdrop:     { position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 },
  modal:        { background: "#0f1623", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, width: "100%", maxWidth: 460, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 40px 100px rgba(0,0,0,0.6)", fontFamily: "'DM Sans','Segoe UI',sans-serif" },
  header:       { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 24px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)" },
  headerLeft:   { display: "flex", alignItems: "center", gap: 10 },
  typeChip:     { fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", padding: "4px 10px", borderRadius: 20 },
  title:        { color: "#e2e8f0", fontSize: 16, fontWeight: 700 },
  closeBtn:     { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#64748b", width: 32, height: 32, cursor: "pointer", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center" },
  balanceBlock: { padding: "28px 24px", margin: "20px 24px 4px", borderRadius: 14 },
  balLabel:     { color: "rgba(255,255,255,0.5)", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 6 },
  balAmount:    { fontSize: 34, fontWeight: 800, color: "#fff", marginBottom: 10 },
  balAccNum:    { fontSize: 13, color: "rgba(255,255,255,0.5)", letterSpacing: "0.2em", fontFamily: "monospace" },
  section:      { padding: "20px 24px 0" },
  sectionTitle: { fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em", color: "#475569", marginBottom: 12, marginTop: 0 },
  row:          { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" },
  rowLabel:     { color: "#64748b", fontSize: 13 },
  rowValue:     { color: "#cbd5e1", fontSize: 13, fontWeight: 600, textAlign: "right", maxWidth: "60%" },
  statsRow:     { display: "flex", gap: 12, marginBottom: 4 },
  statBox:      { flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "14px 12px", display: "flex", flexDirection: "column", alignItems: "center", gap: 4 },
  statValue:    { fontSize: 15, fontWeight: 800 },
  statLabel:    { fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#475569" },
  histNote:     { color: "#334155", fontWeight: 400, textTransform: "none", letterSpacing: 0, fontSize: 10 },
  loading:      { color: "#475569", fontSize: 13, padding: "8px 0" },
  dangerZone:   { margin: "20px 24px 0", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 12, overflow: "hidden" },
  dangerHeader: { background: "rgba(239,68,68,0.07)", padding: "8px 16px", borderBottom: "1px solid rgba(239,68,68,0.15)" },
  dangerTitle:  { fontSize: 11, fontWeight: 800, color: "#f87171", textTransform: "uppercase", letterSpacing: "0.08em" },
  dangerBody:   { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 16px", gap: 12 },
  dangerLabel:  { fontSize: 13, fontWeight: 700, color: "#e2e8f0", marginBottom: 2 },
  dangerHint:   { fontSize: 12, color: "#64748b", margin: 0 },
  dangerBtn:    { background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#f87171", fontWeight: 700, fontSize: 13, padding: "9px 16px", cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0 },
  confirmPanel: { padding: "32px 24px 24px", display: "flex", flexDirection: "column", alignItems: "center" },
  warnIcon:     { fontSize: 40, marginBottom: 16 },
  confirmTitle: { color: "#f87171", fontSize: 18, fontWeight: 800, marginBottom: 10, textAlign: "center" },
  confirmDesc:  { color: "#64748b", fontSize: 13, lineHeight: 1.6, textAlign: "center", marginBottom: 20 },
  blocker:      { display: "flex", alignItems: "center", gap: 10, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: 10, padding: "12px 16px", color: "#fbbf24", fontSize: 13, marginBottom: 20, width: "100%", boxSizing: "border-box" },
  blockerIcon:  { fontSize: 18 },
  confirmPrompt:{ color: "#94a3b8", fontSize: 13, marginBottom: 10, alignSelf: "flex-start" },
  confirmInput: { width: "100%", boxSizing: "border-box", background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "12px 16px", color: "#f87171", fontSize: 16, fontWeight: 800, letterSpacing: "0.15em", outline: "none", textAlign: "center", marginBottom: 12 },
  closeErrBox:  { background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, padding: "10px 14px", color: "#f87171", fontSize: 13, marginBottom: 12, width: "100%", boxSizing: "border-box", lineHeight: 1.5 },
  confirmBtns:  { display: "flex", gap: 10, width: "100%", marginTop: 4 },
  cancelBtn:    { flex: 1, padding: "12px", borderRadius: 10, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", fontWeight: 700, fontSize: 14, cursor: "pointer" },
  destructBtn:  { flex: 1, padding: "12px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#dc2626,#b91c1c)", color: "#fff", fontWeight: 700, fontSize: 14, boxShadow: "0 4px 16px rgba(220,38,38,0.3)", transition: "opacity 0.2s" },
  doneBtn:      { display: "block", width: "calc(100% - 48px)", margin: "20px 24px 24px", padding: "13px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#6366f1,#4f46e5)", color: "#fff", fontWeight: 700, fontSize: 15, cursor: "pointer", boxShadow: "0 4px 20px rgba(99,102,241,0.3)" },
};
