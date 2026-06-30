/**
 * AuthContext.test.jsx
 *
 * Covers: initial state, login/logout mutations, localStorage hydration,
 * and the provider guard that throws outside AuthProvider.
 */
import { render, screen, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../context/AuthContext";

// ── Test consumer ────────────────────────────────────────────────────────────
function TestConsumer() {
  const { isLoggedIn, user, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loggedIn">{String(isLoggedIn)}</span>
      <span data-testid="username">{user?.username ?? "none"}</span>
      <button onClick={() => login("tok-abc", { user_id: 1, username: "alice" })}>
        login
      </button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

const renderWithProvider = () =>
  render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );

// ── Tests ────────────────────────────────────────────────────────────────────
describe("AuthContext", () => {
  it("starts unauthenticated when localStorage is empty", () => {
    renderWithProvider();
    expect(screen.getByTestId("loggedIn")).toHaveTextContent("false");
    expect(screen.getByTestId("username")).toHaveTextContent("none");
  });

  it("login() sets isLoggedIn=true and exposes user", async () => {
    renderWithProvider();
    await act(() => screen.getByText("login").click());
    expect(screen.getByTestId("loggedIn")).toHaveTextContent("true");
    expect(screen.getByTestId("username")).toHaveTextContent("alice");
  });

  it("login() persists token to localStorage", async () => {
    renderWithProvider();
    await act(() => screen.getByText("login").click());
    expect(localStorage.getItem("token")).toBe("tok-abc");
  });

  it("logout() clears isLoggedIn and user", async () => {
    renderWithProvider();
    await act(() => screen.getByText("login").click());
    await act(() => screen.getByText("logout").click());
    expect(screen.getByTestId("loggedIn")).toHaveTextContent("false");
    expect(screen.getByTestId("username")).toHaveTextContent("none");
  });

  it("logout() removes token from localStorage", async () => {
    renderWithProvider();
    await act(() => screen.getByText("login").click());
    await act(() => screen.getByText("logout").click());
    expect(localStorage.getItem("token")).toBeNull();
  });

  it("hydrates auth state from existing localStorage on mount", () => {
    localStorage.setItem("token", "pre-existing-token");
    localStorage.setItem("user", JSON.stringify({ user_id: 2, username: "bob" }));
    renderWithProvider();
    expect(screen.getByTestId("loggedIn")).toHaveTextContent("true");
    expect(screen.getByTestId("username")).toHaveTextContent("bob");
  });

  it("useAuth() throws when used outside AuthProvider", () => {
    expect(() => render(<TestConsumer />)).toThrow(/AuthProvider/);
  });
});