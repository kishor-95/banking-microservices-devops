/**
 * AccountDetailsModal.test.jsx
 *
 * Covers: account info render, profile load, danger zone visibility,
 * close-account confirmation flow (with and without remaining balance),
 * and successful account closure.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import AccountDetailsModal from "../components/AccountDetailsModal";

// ── Module mocks ──────────────────────────────────────────────────────────────
vi.mock("../api/client", () => ({
  api: {
    getProfile:   vi.fn(),
    closeAccount: vi.fn(),
  },
  parseApiError: vi.fn(() => "Failed to close account."),
}));

import { api } from "../api/client";

// ── Fixtures ──────────────────────────────────────────────────────────────────
const MOCK_ACCOUNT = {
  id: "acc-1",
  account_type: "checking",
  account_number: "1234567890",
  is_active: true,
  created_at: "2024-01-01T00:00:00Z",
};
const MOCK_PROFILE = {
  full_name:   "Alice Smith",
  username:    "alice",
  email:       "alice@example.com",
  created_at:  "2024-01-01T00:00:00Z",
};

const onClose          = vi.fn();
const onAccountClosed  = vi.fn();

const renderModal = (balance = 0, history = []) =>
  render(
    <AccountDetailsModal
      account={MOCK_ACCOUNT}
      balance={balance}
      history={history}
      onClose={onClose}
      onAccountClosed={onAccountClosed}
    />
  );

beforeEach(() => {
  api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
});

// ── Tests ─────────────────────────────────────────────────────────────────────
describe("AccountDetailsModal — render", () => {
  it("displays account type chip and balance", async () => {
    renderModal(1500);
    expect(screen.getByText(/checking/i)).toBeInTheDocument();
    expect(await screen.findByText("$1,500.00")).toBeInTheDocument();
  });

  it("loads and displays owner profile", async () => {
    renderModal();
    expect(await screen.findByText("Alice Smith")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("shows 'Loading…' while profile is pending", () => {
    // Never resolve
    api.getProfile.mockReturnValue(new Promise(() => {}));
    renderModal();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("Done button calls onClose", async () => {
    renderModal();
    await screen.findByText("Alice Smith"); // wait for render
    fireEvent.click(screen.getByRole("button", { name: /done/i }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("AccountDetailsModal — close account flow", () => {
  it("shows Danger Zone for active accounts", async () => {
    renderModal();
    await screen.findByText("Alice Smith");
    expect(screen.getByText(/danger zone/i)).toBeInTheDocument();
  });

  it("clicking Close Account reveals confirm panel", async () => {
    renderModal();
    await screen.findByText("Alice Smith");
    fireEvent.click(screen.getAllByRole("button", { name: /close account/i })[0]);
    expect(screen.getByText(/close this account/i)).toBeInTheDocument();
  });

  it("shows balance blocker when account has remaining funds", async () => {
    renderModal(250); // non-zero balance
    await screen.findByText("Alice Smith");
    fireEvent.click(screen.getAllByRole("button", { name: /close account/i })[0]);
    expect(await screen.findByText(/withdraw/i)).toBeInTheDocument();
    // Confirm button should NOT be visible
    expect(screen.queryByRole("button", { name: /^close account$/i })).not.toBeInTheDocument();
  });

  it("requires typing CLOSE before confirm button activates", async () => {
    renderModal(0);
    await screen.findByText("Alice Smith");
    fireEvent.click(screen.getAllByRole("button", { name: /close account/i })[0]);
    const confirmBtn = await screen.findByRole("button", { name: /^close account$/i });
    expect(confirmBtn).toBeDisabled();
  });

  it("typing CLOSE enables confirm and calls api.closeAccount", async () => {
    api.closeAccount.mockResolvedValue({});
    renderModal(0);
    await screen.findByText("Alice Smith");
    fireEvent.click(screen.getAllByRole("button", { name: /close account/i })[0]);
    const input = await screen.findByPlaceholderText("CLOSE");
    await userEvent.type(input, "CLOSE");
    const confirmBtn = screen.getByRole("button", { name: /^close account$/i });
    expect(confirmBtn).not.toBeDisabled();
    fireEvent.click(confirmBtn);
    await waitFor(() => expect(api.closeAccount).toHaveBeenCalledWith("acc-1"));
    expect(onAccountClosed).toHaveBeenCalledWith("acc-1");
  });

  it("Cancel button returns to main view", async () => {
    renderModal(0);
    await screen.findByText("Alice Smith");
    fireEvent.click(screen.getAllByRole("button", { name: /close account/i })[0]);
    await screen.findByPlaceholderText("CLOSE");
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByPlaceholderText("CLOSE")).not.toBeInTheDocument();
  });
});