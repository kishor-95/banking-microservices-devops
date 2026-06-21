/**
 * pages/Dashboard.jsx
 * Main banking dashboard:
 *   - Balance cards for all accounts
 *   - Deposit / Withdraw form
 *   - Paginated transaction history
 */
import { 
  ArrowDown, 
  ArrowUp, 
  Landmark, 
  Shield, 
  ArrowDownLeft, 
  ArrowUpRight 
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api, parseApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AccountDetailsModal from "../components/AccountDetailsModal";
import UserProfileModal    from "../components/UserProfileModal";

// ── Formatters ────────────────────────────────────────────────────────────────
const money  = (n)  => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
const fmtDate = (d) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });

// ── Dashboard ─────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { user, logout }       = useAuth();
  const navigate               = useNavigate();
  const [accounts,  setAccounts]  = useState([]);
  const [selected,  setSelected]  = useState(null); // active account id
  const [balances,  setBalances]  = useState({});   // { [accountId]: balance }
  const [history,   setHistory]   = useState([]);
  const [histTotal, setHistTotal] = useState(0);
  const [histPage,  setHistPage]  = useState(0);
  const [loading,   setLoading]   = useState(true);
  const [txnLoading, setTxnLoading] = useState(false);
  const [histLoading, setHistLoading] = useState(false);
  const [error,     setError]     = useState("");
  const [txnError,  setTxnError]  = useState("");
  const [txnSuccess, setTxnSuccess] = useState("");
  const [form, setForm] = useState({ type: "deposit", amount: "", description: "" });
  const [detailOpen,  setDetailOpen]  = useState(false);  // account details modal
  const [profileOpen, setProfileOpen] = useState(false);  // user profile modal
  const LIMIT = 8;

  // Load accounts + balances
  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [accRes, balRes] = await Promise.all([api.getAccounts(), api.getAllBalances()]);
        const accs  = accRes.data;
        const bals  = {};
        balRes.data.forEach((b) => { bals[b.account_id] = b.balance; });
        setAccounts(accs);
        setBalances(bals);
        if (accs.length > 0) setSelected(accs[0].id);
      } catch (err) {
        setError("Failed to load account data.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Load transaction history when selected account or page changes
  const loadHistory = useCallback(async (accountId, page) => {
    if (!accountId) return;
    setHistLoading(true);
    try {
      const res = await api.getHistory(accountId, LIMIT, page * LIMIT);
      setHistory(res.data.transactions);
      setHistTotal(res.data.total);
    } catch (_) {
      setHistory([]);
    } finally {
      setHistLoading(false);
    }
  }, []);

  useEffect(() => {
    setHistPage(0);
    loadHistory(selected, 0);
  }, [selected, loadHistory]);

  useEffect(() => {
    loadHistory(selected, histPage);
  }, [histPage, loadHistory, selected]);

  // Handle deposit / withdraw
  const handleTransaction = async (e) => {
    e.preventDefault();
    setTxnError(""); setTxnSuccess("");
    const amount = parseFloat(form.amount);
    if (!amount || amount <= 0) { setTxnError("Enter a valid positive amount."); return; }

    setTxnLoading(true);
    try {
      const payload = { account_id: selected, amount, description: form.description || undefined };
      const res = form.type === "deposit"
        ? await api.deposit(payload)
        : await api.withdraw(payload);

      const newBalance = res.data.balance_after;
      setBalances((b) => ({ ...b, [selected]: newBalance }));
      setTxnSuccess(`${form.type === "deposit" ? "Funds added successfully" : "Funds withdrawn successfully"} — ${money(amount)}`);
      setForm((f) => ({ ...f, amount: "", description: "" }));
      // Refresh history
      setHistPage(0);
      loadHistory(selected, 0);
    } catch (err) {
      setTxnError(parseApiError(err, "Transaction failed. Try again."));
    } finally {
      setTxnLoading(false);
    }
  };

  const handleLogout = () => { logout(); navigate("/login"); };

  if (loading) return <LoadingScreen />;

  const selectedAccount = accounts.find((a) => a.id === selected);
  const totalBalance    = Object.values(balances).reduce((s, b) => s + b, 0);
  const totalPages      = Math.ceil(histTotal / LIMIT);

  return (
    <div style={s.page}>
      {/* ── Header ────────────────────────────────────────────────── */}
      <header style={s.header}>
        <div style={s.headerLeft}>
          <Shield size={22} color="#6366f1" style={s.iconGlow} />
          <span style={s.logoText}>VAULTX</span>
        </div>
        <div style={s.headerRight}>
          <button onClick={() => setProfileOpen(true)} style={s.profileBtn}>
             {user?.username}
          </button>
          <button onClick={handleLogout} style={s.logoutBtn}>Sign Out</button>
        </div>
      </header>

      {/* ── User Profile Modal ─────────────────────────────────────── */}
      {profileOpen && (
        <UserProfileModal
          accounts={accounts}
          balances={balances}
          onClose={() => setProfileOpen(false)}
        />
      )}

      <main style={s.main}>
        {error && <div style={s.bannerError}>{error}</div>}

        {/* ── Net Worth Banner ──────────────────────────────────────── */}
        <div style={s.netWorth}>
          <div style={s.nwOrb} />
          <div>
            <p style={s.nwLabel}>Total Portfolio Value</p>
            <p style={s.nwAmount}>{money(totalBalance)}</p>
          </div>
          <button
            style={s.newAccBtn}
            onClick={async () => {
              try {
                const res = await api.openAccount("savings");
                const acc = res.data;
                setAccounts((a) => [...a, acc]);
                setBalances((b) => ({ ...b, [acc.id]: 0 }));
              } catch (_) { setError("Could not open new account."); }
            }}
          >
            + New Account
          </button>
        </div>

        {/* ── Account Cards ─────────────────────────────────────────── */}
        <div style={s.cardRow}>
          {accounts.map((acc) => (
            <AccountCard
              key={acc.id}
              account={acc}
              balance={balances[acc.id] ?? 0}
              active={acc.id === selected}
              onClick={() => setSelected(acc.id)}
              onDetails={(e) => { e.stopPropagation(); setSelected(acc.id); setDetailOpen(true); }}
            />
          ))}
        </div>

        {/* ── Account Details Modal ─────────────────────────────────── */}
        {detailOpen && selectedAccount && (
          <AccountDetailsModal
            account={selectedAccount}
            balance={balances[selectedAccount.id] ?? 0}
            history={history}
            onClose={() => setDetailOpen(false)}
            onAccountClosed={(closedId) => {
              setAccounts((prev) => prev.filter((a) => a.id !== closedId));
              setBalances((prev) => { const b = { ...prev }; delete b[closedId]; return b; });
              // Select next available account
              const remaining = accounts.filter((a) => a.id !== closedId);
              setSelected(remaining.length > 0 ? remaining[0].id : null);
            }}
          />
        )}

        {accounts.length === 0 && (
          <div style={s.empty}>No accounts found. Something went wrong during registration.</div>
        )}

        {selected && (
          <div style={s.grid}>
            {/* ── Transaction Form ───────────────────────────────────── */}
            <div style={s.panel}>
              <h2 style={s.panelTitle}>Move Money</h2>

              {/* Type selector */}
              <div style={s.typeRow}>
                {["deposit", "withdraw"].map((t) => (
                  <button
                    key={t}
                    onClick={() => { setForm((f) => ({ ...f, type: t })); setTxnError(""); setTxnSuccess(""); }}
                    style={{ ...s.typeBtn, ...(form.type === t ? (t === "deposit" ? s.typeBtnDepositActive : s.typeBtnWithdrawActive) : {}) }}
                  >
                    {t === "deposit" ? (
                      <>
                      <ArrowDownLeft size={16} /> Deposit
                      </>
                    ) : (
                      <>
                       <ArrowUpRight size={16} /> Withdraw
                      </>
                    )}
                  </button>
                ))}
              </div>

              <form onSubmit={handleTransaction} style={s.txnForm}>
                <label style={s.label}>Amount (USD)</label>
                <div style={s.amountWrap}>
                  <span style={s.dollar}>$</span>
                  <input
                    type="number" min="0.01" step="0.01"
                    value={form.amount}
                    onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                    placeholder="0.00"
                    style={s.amountInput}
                    required
                  />
                </div>

                <label style={{ ...s.label, marginTop: 16 }}>Note (optional)</label>
                <input
                  type="text" value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="e.g. Rent, Groceries..."
                  style={s.noteInput}
                />

                {txnError   && <div style={s.txnError}>{txnError}</div>}
                {txnSuccess  && <div style={s.txnSuccess}>{txnSuccess}</div>}

                <button
                  type="submit"
                  disabled={txnLoading}
                  style={{
                    ...s.txnBtn,
                    background: form.type === "deposit"
                      ? "linear-gradient(135deg, #10b981 0%, #059669 100%)"
                      : "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
                  }}
                >
                  {txnLoading ? "Processing…" : (form.type === "deposit" ? "Add Funds" : "Withdraw Funds")}
                </button>
              </form>

              {/* Quick amounts */}
              <div style={s.quickRow}>
                {[50, 100, 250, 500].map((amt) => (
                  <button key={amt} style={s.quickBtn}
                    onClick={() => setForm((f) => ({ ...f, amount: String(amt) }))}>
                    ${amt}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Transaction History ────────────────────────────────── */}
            <div style={s.panel}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <h2 style={s.panelTitle}>Transaction History</h2>
                <span style={s.acctNum}>
                  {selectedAccount?.account_number?.replace(/(.{4})/g, "$1 ").trim()}
                </span>
              </div>

              {histLoading ? (
                <div style={s.histLoading}>Loading…</div>
              ) : history.length === 0 ? (
                <div style={s.histEmpty}>No activity yet — your transactions will appear here.</div>
              ) : (
                <>
                  <div style={s.histList}>
                    {history.map((txn) => (
                      <TxnRow key={txn.id} txn={txn} />
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div style={s.paginationRow}>
                      <button
                        disabled={histPage === 0}
                        onClick={() => setHistPage((p) => p - 1)}
                        style={s.pageBtn}
                      >← Prev</button>
                      <span style={s.pageInfo}>Page {histPage + 1} / {totalPages}</span>
                      <button
                        disabled={histPage >= totalPages - 1}
                        onClick={() => setHistPage((p) => p + 1)}
                        style={s.pageBtn}
                      >Next →</button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function AccountCard({ account, balance, active, onClick, onDetails }) {
  const isChecking = account.account_type === "checking";
  return (
    <div onClick={onClick} style={{
      ...s.accCard,
      ...(active ? s.accCardActive : {}),
      background: active
        ? (isChecking
            ? "linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)"
            : "linear-gradient(135deg, #064e3b 0%, #065f46 100%)")
        : "rgba(255,255,255,0.04)",
    }}>
      <div style={s.accCardTop}>
        <span style={s.accType}>{account.account_type === "checking" 
          ? "Flow Account"
          : "Vault Savings"
        }</span>
        <span style={s.accDot}>{active ? "●" : "○"}</span>
      </div>
      <div style={s.accBalance}>{money(balance)}</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={s.accNum}>•••• {account.account_number?.slice(-4)}</div>
        <button
          onClick={onDetails}
          style={{
            background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: 6, color: "rgba(255,255,255,0.7)", fontSize: 11,
            fontWeight: 700, padding: "4px 10px", cursor: "pointer", letterSpacing: "0.05em",
          }}
        >
          Details
        </button>
      </div>
    </div>
  );
}

function TxnRow({ txn }) {
  const isDeposit = txn.type === "DEPOSIT";
  return (
    <div style={s.txnRow}>
      <div style={{ ...s.txnIcon, background: isDeposit ? "rgba(16,185,129,0.12)" : "rgba(245,158,11,0.12)" }}>
        {isDeposit 
        ? <ArrowDown size={16} color="#10b981" />
        : <ArrowUp size={16} color="#f59e0b" />}
      </div>
      <div style={s.txnMeta}>
        <span style={s.txnDesc}>{txn.description || (isDeposit ? "Funds Added" : "Withdraw Funds")}</span>
        <span style={s.txnDate}>{fmtDate(txn.created_at)}</span>
      </div>
      <div style={s.txnRight}>
        <span style={{ ...s.txnAmt, color: isDeposit ? "#10b981" : "#f59e0b" }}>
          {isDeposit ? "+" : "-"}{money(txn.amount)}
        </span>
        <span style={s.txnBal}>{money(txn.balance_after)}</span>
      </div>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div style={{ ...s.page, alignItems: "center", justifyContent: "center" }}>
      <div style={{ color: "#6366f1", fontSize: 32 }}>⬡</div>
      <p style={{ color: "#475569", marginTop: 12 }}>Loading your account…</p>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  page:       { minHeight: "100vh", background: "#080c14", fontFamily: "'DM Sans','Segoe UI',sans-serif", color: "#e2e8f0" },
  header:     { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 32px", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(8,12,20,0.9)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 100 },
  headerLeft: { display: "flex", alignItems: "center", gap: 10 },
  logoIcon:   { fontSize: 24, color: "#6366f1" },
  iconGlow:   {filter: "drop-shadow(0 0 6px rgba(99,102,241,0.6))"},
  logoText:   { fontSize: 18, fontWeight: 800, letterSpacing: "0.12em", background: "linear-gradient(135deg,#e2e8f0,#94a3b8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },
  headerRight:{ display: "flex", alignItems: "center", gap: 16 },
  greeting:   { color: "#64748b", fontSize: 14 },
  profileBtn: { background: "none", border: "none", color: "#64748b", fontSize: 14, cursor: "pointer", padding: "4px 8px", borderRadius: 8, transition: "color 0.2s" },
  logoutBtn:  { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#94a3b8", padding: "7px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600 },
  main:       { maxWidth: 1100, margin: "0 auto", padding: "32px 24px" },
  bannerError:{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 10, padding: "12px 16px", color: "#f87171", marginBottom: 24 },

  netWorth:   { position: "relative", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.15)", borderRadius: 16, padding: "28px 32px", marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "center", overflow: "hidden" },
  nwOrb:      { position: "absolute", width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle,rgba(99,102,241,0.12) 0%,transparent 70%)", right: -80, top: -80, pointerEvents: "none" },
  nwLabel:    { color: "#64748b", fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 },
  nwAmount:   { fontSize: 38, fontWeight: 800, background: "linear-gradient(135deg,#e2e8f0,#a5b4fc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },
  newAccBtn:  { background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: 10, color: "#a5b4fc", padding: "10px 20px", cursor: "pointer", fontSize: 14, fontWeight: 700 },

  cardRow:    { display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" },
  accCard:    { flex: "1 1 220px", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "20px 24px", cursor: "pointer", transition: "all 0.2s", minWidth: 200 },
  accCardActive: { border: "1px solid rgba(99,102,241,0.4)", boxShadow: "0 8px 32px rgba(99,102,241,0.15)" },
  accCardTop: { display: "flex", justifyContent: "space-between", marginBottom: 16 },
  accType:    { fontSize: 11, fontWeight: 800, letterSpacing: "0.1em", color: "#94a3b8" },
  accDot:     { color: "#6366f1", fontSize: 12 },
  accBalance: { fontSize: 24, fontWeight: 800, color: "#e2e8f0", marginBottom: 8 },
  accNum:     { fontSize: 13, color: "#475569", letterSpacing: "0.08em" },

  grid:       { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 },
  panel:      { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: "28px 24px" },
  panelTitle: { fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginBottom: 20, marginTop: 0 },
  label:      { color: "#94a3b8", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", display: "block", marginBottom: 8 },
  typeRow:    { display: "flex", gap: 8, marginBottom: 24 },
  typeBtn:    { flex: 1, padding: "10px", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 10, background: "transparent", color: "#64748b", fontWeight: 700, fontSize: 14, cursor: "pointer" },
  typeBtnDepositActive:  { background: "rgba(16,185,129,0.12)", border: "1px solid rgba(16,185,129,0.25)", color: "#10b981" },
  typeBtnWithdrawActive: { background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.25)", color: "#f59e0b" },
  txnForm:    { display: "flex", flexDirection: "column" },
  amountWrap: { display: "flex", alignItems: "center", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10 },
  dollar:     { color: "#64748b", fontSize: 20, fontWeight: 700, paddingLeft: 14 },
  amountInput:{ flex: 1, background: "transparent", border: "none", outline: "none", padding: "13px 14px", color: "#e2e8f0", fontSize: 22, fontWeight: 800, width: "100%" },
  noteInput:  { background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: "11px 14px", color: "#e2e8f0", fontSize: 14, outline: "none" },
  txnError:   { background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, padding: "10px 14px", color: "#f87171", fontSize: 13, marginTop: 14 },
  txnSuccess: { background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 8, padding: "10px 14px", color: "#10b981", fontSize: 13, marginTop: 14 },
  txnBtn:     { marginTop: 20, padding: "14px", borderRadius: 10, border: "none", color: "#fff", fontWeight: 800, fontSize: 15, cursor: "pointer", boxShadow: "0 4px 20px rgba(0,0,0,0.2)" },
  quickRow:   { display: "flex", gap: 8, marginTop: 16 },
  quickBtn:   { flex: 1, padding: "8px", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, background: "transparent", color: "#94a3b8", fontSize: 13, fontWeight: 600, cursor: "pointer" },

  acctNum:    { fontSize: 12, color: "#475569", letterSpacing: "0.15em", fontFamily: "monospace" },
  histList:   { display: "flex", flexDirection: "column", gap: 4 },
  histLoading:{ color: "#475569", textAlign: "center", padding: "40px 0", fontSize: 14 },
  histEmpty:  { color: "#475569", textAlign: "center", padding: "40px 0", fontSize: 14 },
  txnRow:     { display: "flex", alignItems: "center", gap: 12, padding: "12px 8px", borderRadius: 10, borderBottom: "1px solid rgba(255,255,255,0.04)" },
  txnIcon:    { width: 36, height: 36, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 },
  txnMeta:    { flex: 1, display: "flex", flexDirection: "column", gap: 2 },
  txnDesc:    { fontSize: 14, fontWeight: 600, color: "#cbd5e1" },
  txnDate:    { fontSize: 11, color: "#475569" },
  txnRight:   { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 2 },
  txnAmt:     { fontSize: 14, fontWeight: 800 },
  txnBal:     { fontSize: 11, color: "#475569" },
  paginationRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, paddingTop: 16, borderTop: "1px solid rgba(255,255,255,0.06)" },
  pageBtn:    { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#94a3b8", padding: "7px 14px", cursor: "pointer", fontSize: 13 },
  pageInfo:   { color: "#475569", fontSize: 13 },
  empty:      { color: "#475569", textAlign: "center", padding: 40 },
};
