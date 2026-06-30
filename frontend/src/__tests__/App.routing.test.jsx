/**
 * App.routing.test.jsx
 *
 * Tests PrivateRoute (unauthenticated → /login redirect) and
 * PublicRoute (authenticated → /dashboard redirect) guards.
 * Pages are mocked to avoid API calls; only routing behavior is asserted.
 */
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

// ── Stable mocks ─────────────────────────────────────────────────────────────
vi.mock("../pages/Login",     () => ({ default: () => <div>Login Page</div> }));
vi.mock("../pages/Dashboard", () => ({ default: () => <div>Dashboard Page</div> }));
vi.mock("../components/Footer", () => ({ default: () => null }));

// AuthContext mock — controlled per-test via useAuth
const mockUseAuth = vi.fn();
vi.mock("../context/AuthContext", () => ({
  AuthProvider: ({ children }) => <>{children}</>,
  useAuth: () => mockUseAuth(),
}));

import App from "../App";

// ── Helpers ───────────────────────────────────────────────────────────────────
// BrowserRouter (used in App) reads window.location; we push history directly.
const setPath = (path) => window.history.pushState({}, "", path);

describe("App routing", () => {
  it("unauthenticated user at /dashboard is redirected to /login", () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: false });
    setPath("/dashboard");
    render(<App />);
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("authenticated user at /login is redirected to /dashboard", () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: true });
    setPath("/login");
    render(<App />);
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });

  it("authenticated user at / is redirected to /dashboard", () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: true });
    setPath("/");
    render(<App />);
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });

  it("unauthenticated user at / is redirected to /login", () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: false });
    setPath("/");
    render(<App />);
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("unknown route falls back to /dashboard (and then /login if unauthed)", () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: false });
    setPath("/some/random/path");
    render(<App />);
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });
});