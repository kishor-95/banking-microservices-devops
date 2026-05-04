// /**
//  * Dashboard.test.jsx
//  *
//  * Covers: data loading, account card render, deposit/withdraw form,
//  * transaction validation, logout flow, profile modal toggle, and
//  * "New Account" creation. Modals are mocked to isolate concerns.
//  */
// import {
//   render,
//   screen,
//   fireEvent,
//   waitFor,
//   waitForElementToBeRemoved,
// } from "@testing-library/react";
// import { vi } from "vitest";
// import Dashboard from "../pages/Dashboard";

// // ── Module mocks ──────────────────────────────────────────────────────────────
// vi.mock("../api/client", () => ({
//   api: {
//     getAccounts:    vi.fn(),
//     getAllBalances:  vi.fn(),
//     getHistory:     vi.fn(),
//     deposit:        vi.fn(),
//     withdraw:       vi.fn(),
//     openAccount:    vi.fn(),
//   },
//   parseApiError: vi.fn(() => "Something went wrong. Try again."),
// }));

// vi.mock("../context/AuthContext", () => ({
//   useAuth: vi.fn(),
// }));

// const mockNavigate = vi.hoisted(() => vi.fn());
// vi.mock("react-router-dom", async (importOriginal) => {
//   const mod = await importOriginal();
//   return { ...mod, useNavigate: () => mockNavigate };
// });

// // Isolate modals — tested independently
// vi.mock("../components/AccountDetailsModal", () => ({
//   default: ({ onClose }) => (
//     <div data-testid="account-details-modal">
//       <button onClick={onClose}>CloseModal</button>
//     </div>
//   ),
// }));
// vi.mock("../components/UserProfileModal", () => ({
//   default: ({ onClose }) => (
//     <div data-testid="user-profile-modal">
//       <button onClick={onClose}>CloseModal</button>
//     </div>
//   ),
// }));

// // ── Import after mocks ────────────────────────────────────────────────────────
// import { api, parseApiError } from "../api/client";
// import { useAuth } from "../context/AuthContext";

// // ── Fixtures ──────────────────────────────────────────────────────────────────
// const MOCK_ACCOUNT = {
//   id: "acc-1",
//   account_type: "checking",
//   account_number: "1234567890",
//   is_active: true,
//   created_at: "2024-01-01T00:00:00Z",
// };
// const MOCK_BALANCES  = [{ account_id: "acc-1", balance: 500 }];
// const EMPTY_HISTORY  = { transactions: [], total: 0 };
// const mockLogout     = vi.fn();

// beforeEach(() => {
//   useAuth.mockReturnValue({ user: { username: "alice" }, logout: mockLogout });
//   api.getAccounts.mockResolvedValue({ data: [MOCK_ACCOUNT] });
//   api.getAllBalances.mockResolvedValue({ data: MOCK_BALANCES });
//   api.getHistory.mockResolvedValue({ data: EMPTY_HISTORY });
// });

// const renderDashboard = () => render(<Dashboard />);

// // Wait for the loading screen to disappear
// const waitForLoad = () =>
//   waitForElementToBeRemoved(() => screen.queryByText(/loading your account/i));

// // ── Tests ─────────────────────────────────────────────────────────────────────
// describe("Dashboard — data loading", () => {
//   it("shows loading screen initially then renders account card", async () => {
//     renderDashboard();
//     expect(screen.getByText(/loading your account/i)).toBeInTheDocument();
//     await waitForLoad();
//     // "Flow Account" is the display name for checking accounts
//     expect(screen.getByText(/flow account/i)).toBeInTheDocument();
//   });

//   it("shows account balance from API", async () => {
//     renderDashboard();
//     await waitForLoad();
//     expect(screen.getByText("$500.00")).toBeInTheDocument();
//   });

//   it("shows error banner when account load fails", async () => {
//     api.getAccounts.mockRejectedValue(new Error("Network Error"));
//     renderDashboard();
//     await waitForLoad();
//     expect(screen.getByText(/failed to load account data/i)).toBeInTheDocument();
//   });

//   it("shows empty state when accounts array is empty", async () => {
//     api.getAccounts.mockResolvedValue({ data: [] });
//     api.getAllBalances.mockResolvedValue({ data: [] });
//     renderDashboard();
//     await waitForLoad();
//     expect(screen.getByText(/no accounts found/i)).toBeInTheDocument();
//   });
// });

// describe("Dashboard — transaction form", () => {
//   it("shows error for empty / zero amount on submit", async () => {
//     const { container } = renderDashboard();
//     await waitForLoad();
//     fireEvent.submit(container.querySelector("form"));
//     expect(await screen.findByText(/valid positive amount/i)).toBeInTheDocument();
//   });

//   it("successful deposit shows success message and updated balance feedback", async () => {
//     api.deposit.mockResolvedValue({ data: { balance_after: 600 } });
//     const { container } = renderDashboard();
//     await waitForLoad();
//     fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "100" } });
//     fireEvent.submit(container.querySelector("form"));
//     expect(await screen.findByText(/funds added successfully/i)).toBeInTheDocument();
//   });

//   it("successful withdraw shows success message", async () => {
//     api.withdraw.mockResolvedValue({ data: { balance_after: 400 } });
//     const { container } = renderDashboard();
//     await waitForLoad();
//     // Switch to withdraw
//     fireEvent.click(screen.getByRole("button", { name: /withdraw/i }));
//     fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "100" } });
//     fireEvent.submit(container.querySelector("form"));
//     expect(await screen.findByText(/funds withdrawn successfully/i)).toBeInTheDocument();
//   });

//   it("API transaction failure shows parsed error", async () => {
//     api.deposit.mockRejectedValue(new Error("fail"));
//     parseApiError.mockReturnValue("Insufficient funds.");
//     const { container } = renderDashboard();
//     await waitForLoad();
//     fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "999" } });
//     fireEvent.submit(container.querySelector("form"));
//     expect(await screen.findByText(/insufficient funds/i)).toBeInTheDocument();
//   });

//   it("quick-amount buttons populate the amount field", async () => {
//     renderDashboard();
//     await waitForLoad();
//     fireEvent.click(screen.getByRole("button", { name: "$100" }));
//     expect(screen.getByPlaceholderText("0.00")).toHaveValue(100);
//   });
// });

// describe("Dashboard — navigation & modals", () => {
//   it("Sign Out calls logout() and navigates to /login", async () => {
//     renderDashboard();
//     await waitForLoad();
//     fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
//     expect(mockLogout).toHaveBeenCalled();
//     expect(mockNavigate).toHaveBeenCalledWith("/login");
//   });

//   it("clicking username opens UserProfileModal", async () => {
//     renderDashboard();
//     await waitForLoad();
//     fireEvent.click(screen.getByRole("button", { name: /alice/i }));
//     expect(screen.getByTestId("user-profile-modal")).toBeInTheDocument();
//   });

//   it("clicking Details opens AccountDetailsModal", async () => {
//     renderDashboard();
//     await waitForLoad();
//     fireEvent.click(screen.getByRole("button", { name: /details/i }));
//     expect(screen.getByTestId("account-details-modal")).toBeInTheDocument();
//   });

//   it("New Account button calls api.openAccount and adds card", async () => {
//     const newAcc = { ...MOCK_ACCOUNT, id: "acc-2", account_type: "savings" };
//     api.openAccount.mockResolvedValue({ data: newAcc });
//     renderDashboard();
//     await waitForLoad();
//     fireEvent.click(screen.getByRole("button", { name: /\+ new account/i }));
//     await waitFor(() => expect(api.openAccount).toHaveBeenCalledWith("savings"));
//   });
// });

/**
 * Dashboard.test.jsx
 */

import {
  render,
  screen,
  fireEvent,
  waitFor,
  waitForElementToBeRemoved,
} from "@testing-library/react";
import { vi } from "vitest";
import Dashboard from "../pages/Dashboard";

// ── Module mocks ──────────────────────────────────────────────────────────────
vi.mock("../api/client", () => ({
  api: {
    getAccounts: vi.fn(),
    getAllBalances: vi.fn(),
    getHistory: vi.fn(),
    deposit: vi.fn(),
    withdraw: vi.fn(),
    openAccount: vi.fn(),
  },
  parseApiError: vi.fn(() => "Something went wrong. Try again."),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock("react-router-dom", async (importOriginal) => {
  const mod = await importOriginal();
  return { ...mod, useNavigate: () => mockNavigate };
});

// Mock modals
vi.mock("../components/AccountDetailsModal", () => ({
  default: ({ onClose }) => (
    <div data-testid="account-details-modal">
      <button onClick={onClose}>CloseModal</button>
    </div>
  ),
}));

vi.mock("../components/UserProfileModal", () => ({
  default: ({ onClose }) => (
    <div data-testid="user-profile-modal">
      <button onClick={onClose}>CloseModal</button>
    </div>
  ),
}));

// ── Imports after mocks ───────────────────────────────────────────────────────
import { api, parseApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

// ── Fixtures ──────────────────────────────────────────────────────────────────
const MOCK_ACCOUNT = {
  id: "acc-1",
  account_type: "checking",
  account_number: "1234567890",
  is_active: true,
  created_at: "2024-01-01T00:00:00Z",
};

const MOCK_BALANCES = [{ account_id: "acc-1", balance: 500 }];
const EMPTY_HISTORY = { transactions: [], total: 0 };

const mockLogout = vi.fn();

// ── Setup ─────────────────────────────────────────────────────────────────────
beforeEach(() => {
  useAuth.mockReturnValue({
    user: { username: "alice" },
    logout: mockLogout,
  });

  api.getAccounts.mockResolvedValue({ data: [MOCK_ACCOUNT] });
  api.getAllBalances.mockResolvedValue({ data: MOCK_BALANCES });
  api.getHistory.mockResolvedValue({ data: EMPTY_HISTORY });
});

const renderDashboard = () => render(<Dashboard />);

const waitForLoad = () =>
  waitForElementToBeRemoved(() =>
    screen.queryByText(/loading your account/i)
  );

// ── Tests ─────────────────────────────────────────────────────────────────────
describe("Dashboard — data loading", () => {
  it("shows loading screen initially then renders account card", async () => {
    renderDashboard();
    expect(
      screen.getByText(/loading your account/i)
    ).toBeInTheDocument();

    await waitForLoad();

    expect(screen.getByText(/flow account/i)).toBeInTheDocument();
  });

  // ✅ FIXED TEST
  it("shows account balance from API", async () => {
    renderDashboard();
    await waitForLoad();

    const balances = screen.getAllByText("$500.00");
    expect(balances.length).toBeGreaterThan(0);
  });

  it("shows error banner when account load fails", async () => {
    api.getAccounts.mockRejectedValue(new Error("Network Error"));

    renderDashboard();
    await waitForLoad();

    expect(
      screen.getByText(/failed to load account data/i)
    ).toBeInTheDocument();
  });

  it("shows empty state when accounts array is empty", async () => {
    api.getAccounts.mockResolvedValue({ data: [] });
    api.getAllBalances.mockResolvedValue({ data: [] });

    renderDashboard();
    await waitForLoad();

    expect(
      screen.getByText(/no accounts found/i)
    ).toBeInTheDocument();
  });
});

describe("Dashboard — transaction form", () => {
  it("shows error for empty / zero amount on submit", async () => {
    const { container } = renderDashboard();
    await waitForLoad();

    fireEvent.submit(container.querySelector("form"));

    expect(
      await screen.findByText(/valid positive amount/i)
    ).toBeInTheDocument();
  });

  it("successful deposit shows success message", async () => {
    api.deposit.mockResolvedValue({ data: { balance_after: 600 } });

    const { container } = renderDashboard();
    await waitForLoad();

    fireEvent.change(screen.getByPlaceholderText("0.00"), {
      target: { value: "100" },
    });

    fireEvent.submit(container.querySelector("form"));

    expect(
      await screen.findByText(/funds added successfully/i)
    ).toBeInTheDocument();
  });

  it("successful withdraw shows success message", async () => {
    api.withdraw.mockResolvedValue({ data: { balance_after: 400 } });

    const { container } = renderDashboard();
    await waitForLoad();

    fireEvent.click(
      screen.getByRole("button", { name: /withdraw/i })
    );

    fireEvent.change(screen.getByPlaceholderText("0.00"), {
      target: { value: "100" },
    });

    fireEvent.submit(container.querySelector("form"));

    expect(
      await screen.findByText(/funds withdrawn successfully/i)
    ).toBeInTheDocument();
  });

  it("API transaction failure shows parsed error", async () => {
    api.deposit.mockRejectedValue(new Error("fail"));
    parseApiError.mockReturnValue("Insufficient funds.");

    const { container } = renderDashboard();
    await waitForLoad();

    fireEvent.change(screen.getByPlaceholderText("0.00"), {
      target: { value: "999" },
    });

    fireEvent.submit(container.querySelector("form"));

    expect(
      await screen.findByText(/insufficient funds/i)
    ).toBeInTheDocument();
  });

  it("quick-amount buttons populate the amount field", async () => {
    renderDashboard();
    await waitForLoad();

    fireEvent.click(screen.getByRole("button", { name: "$100" }));

    expect(screen.getByPlaceholderText("0.00")).toHaveValue(100);
  });
});

describe("Dashboard — navigation & modals", () => {
  it("Sign Out calls logout() and navigates to /login", async () => {
    renderDashboard();
    await waitForLoad();

    fireEvent.click(
      screen.getByRole("button", { name: /sign out/i })
    );

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/login");
  });

  it("clicking username opens UserProfileModal", async () => {
    renderDashboard();
    await waitForLoad();

    fireEvent.click(
      screen.getByRole("button", { name: /alice/i })
    );

    expect(
      screen.getByTestId("user-profile-modal")
    ).toBeInTheDocument();
  });

  it("clicking Details opens AccountDetailsModal", async () => {
    renderDashboard();
    await waitForLoad();

    fireEvent.click(
      screen.getByRole("button", { name: /details/i })
    );

    expect(
      screen.getByTestId("account-details-modal")
    ).toBeInTheDocument();
  });

  it("New Account button calls api.openAccount", async () => {
    const newAcc = {
      ...MOCK_ACCOUNT,
      id: "acc-2",
      account_type: "savings",
    };

    api.openAccount.mockResolvedValue({ data: newAcc });

    renderDashboard();
    await waitForLoad();

    fireEvent.click(
      screen.getByRole("button", { name: /\+ new account/i })
    );

    await waitFor(() =>
      expect(api.openAccount).toHaveBeenCalledWith("savings")
    );
  });
});