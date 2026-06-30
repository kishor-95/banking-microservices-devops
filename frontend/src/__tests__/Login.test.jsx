/**
 * Login.test.jsx
 *
 * Covers: default render, mode switching, client-side validation,
 * successful login/register flows, and API error display.
 *
 * NOTE: The Field component renders <label> without htmlFor/id linkage,
 * so getByLabelText is not usable — inputs are targeted by placeholder.
 * Recommend adding htmlFor/id pairs to Field for a11y compliance.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import Login from "../pages/Login";

// ── Module mocks ─────────────────────────────────────────────────────────────
vi.mock("../api/client", () => ({
  api: {
    login:       vi.fn(),
    register:    vi.fn(),
    openAccount: vi.fn(),
  },
  parseApiError: vi.fn(() => "Invalid credentials"),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockNavigate = vi.hoisted(() => vi.fn());
vi.mock("react-router-dom", async (importOriginal) => {
  const mod = await importOriginal();
  return { ...mod, useNavigate: () => mockNavigate };
});

// ── Import after mocks ────────────────────────────────────────────────────────
import { api, parseApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

// ── Fixtures ──────────────────────────────────────────────────────────────────
const mockAuthLogin = vi.fn();
const SUCCESS_RESPONSE = {
  data: { access_token: "tok-123", user_id: 1, username: "alice" },
};

beforeEach(() => {
  useAuth.mockReturnValue({ login: mockAuthLogin });
  parseApiError.mockReturnValue("Invalid credentials");
});

const renderLogin = () =>
  render(<MemoryRouter><Login /></MemoryRouter>);

// Submits the form element directly — avoids ambiguous button name collisions
// (tab "Sign In" vs submit "Sign In")
const submitForm = (container) =>
  fireEvent.submit(container.querySelector("form"));

// ── Tests ─────────────────────────────────────────────────────────────────────
describe("Login page — render", () => {
  it("renders sign-in mode by default with no email field", () => {
    renderLogin();
    // Submit button is present in form
    expect(screen.getByPlaceholderText(/your_username/i)).toBeInTheDocument();
    // Email field only shows in register mode
    expect(screen.queryByPlaceholderText(/jane@example\.com/i)).not.toBeInTheDocument();
  });

  it("switching to register reveals email and full-name fields", async () => {
    renderLogin();
    await userEvent.click(screen.getByRole("button", { name: /register/i }));
    expect(screen.getByPlaceholderText(/jane@example\.com/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/jane smith/i)).toBeInTheDocument();
  });
});

describe("Login page — client-side validation", () => {
  it("rejects missing username", async () => {
    const { container } = renderLogin();
    submitForm(container);
    expect(await screen.findByText(/username is required/i)).toBeInTheDocument();
  });

  it("rejects username shorter than 3 chars", async () => {
    const { container } = renderLogin();
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "ab");
    submitForm(container);
    expect(await screen.findByText(/at least 3 characters/i)).toBeInTheDocument();
  });

  it("rejects password shorter than 8 chars", async () => {
    const { container } = renderLogin();
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "alice");
    await userEvent.type(screen.getByPlaceholderText(/min 8 chars/i), "short");
    submitForm(container);
    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
  });

  it("rejects invalid email format in register mode", async () => {
    const { container } = renderLogin();
    await userEvent.click(screen.getByRole("button", { name: /register/i }));
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "alice");
    await userEvent.type(screen.getByPlaceholderText(/min 8 chars/i), "password123");
    await userEvent.type(screen.getByPlaceholderText(/jane@example\.com/i), "notanemail");
    submitForm(container);
    expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
  });
});

describe("Login page — API flows", () => {
  it("successful login calls api.login, sets auth, and navigates to dashboard", async () => {
    api.login.mockResolvedValue(SUCCESS_RESPONSE);
    const { container } = renderLogin();
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "alice");
    await userEvent.type(screen.getByPlaceholderText(/min 8 chars/i), "password123");
    submitForm(container);
    await waitFor(() =>
      expect(mockAuthLogin).toHaveBeenCalledWith("tok-123", { user_id: 1, username: "alice" })
    );
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
  });

  it("API login failure displays parsed error message", async () => {
    api.login.mockRejectedValue(new Error("fail"));
    parseApiError.mockReturnValue("Invalid credentials");
    const { container } = renderLogin();
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "alice");
    await userEvent.type(screen.getByPlaceholderText(/min 8 chars/i), "password123");
    submitForm(container);
    expect(await screen.findByText(/invalid credentials/i)).toBeInTheDocument();
  });

  it("successful register calls api.register, auto-opens account, and navigates", async () => {
    api.register.mockResolvedValue(SUCCESS_RESPONSE);
    api.openAccount.mockResolvedValue({ data: { id: "acc-1" } });
    const { container } = renderLogin();
    await userEvent.click(screen.getByRole("button", { name: /register/i }));
    await userEvent.type(screen.getByPlaceholderText(/jane@example\.com/i), "alice@test.com");
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "alice");
    await userEvent.type(screen.getByPlaceholderText(/min 8 chars/i), "password123");
    submitForm(container);
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/dashboard"));
    expect(api.openAccount).toHaveBeenCalledWith("checking");
  });

  it("submit button is disabled while request is in-flight", async () => {
    // Never resolves — keeps loading state active
    api.login.mockReturnValue(new Promise(() => {}));
    const { container } = renderLogin();
    await userEvent.type(screen.getByPlaceholderText(/your_username/i), "alice");
    await userEvent.type(screen.getByPlaceholderText(/min 8 chars/i), "password123");
    submitForm(container);
    await waitFor(() =>
      expect(container.querySelector("button[type='submit']")).toBeDisabled()
    );
  });
});