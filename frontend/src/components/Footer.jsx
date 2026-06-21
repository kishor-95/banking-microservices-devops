export default function Footer() {
  return (
    <footer style={s.footer}>
      <span style={s.text}>
        © {new Date().getFullYear()} VaultX Banking · Built with{" "}
        <span style={s.name}>Kishor Bhairat</span>
      </span>
    </footer>
  );
}

const s = {
  footer: {
    borderTop: "1px solid rgba(255,255,255,0.06)",
    padding: "18px 32px",
    textAlign: "center",
    background: "#080c14",
  },
  text: { color: "#334155", fontSize: 13 },
  name: { color: "#6366f1", fontWeight: 700 },
};