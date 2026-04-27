// /**
//  * UserProfileModal.test.jsx
//  *
//  * Covers: loading state, successful profile render, portfolio summary,
//  * API failure fallback, and close button behaviour.
//  */
// import { render, screen, fireEvent } from "@testing-library/react";
// import { vi } from "vitest";
// import UserProfileModal from "../components/UserProfileModal";

// // ── Module mocks ──────────────────────────────────────────────────────────────
// vi.mock("../api/client", () => ({
//   api: { getProfile: vi.fn() },
// }));

// import { api } from "../api/client";

// // ── Fixtures ──────────────────────────────────────────────────────────────────
// const MOCK_PROFILE = {
//   full_name:  "Alice Smith",
//   username:   "alice",
//   email:      "alice@test.com",
//   created_at: "2024-01-01T00:00:00Z",
// };
// const MOCK_ACCOUNTS = [
//   { id: "acc-1", account_type: "checking", account_number: "1234000001" },
//   { id: "acc-2", account_type: "savings",  account_number: "1234000002" },
// ];
// const MOCK_BALANCES = { "acc-1": 1000, "acc-2": 500 };

// const onClose = vi.fn();

// const renderModal = () =>
//   render(
//     <UserProfileModal
//       onClose={onClose}
//       accounts={MOCK_ACCOUNTS}
//       balances={MOCK_BALANCES}
//     />
//   );

// // ── Tests ─────────────────────────────────────────────────────────────────────
// describe("UserProfileModal", () => {
//   it("shows loading state while profile is fetching", () => {
//     api.getProfile.mockReturnValue(new Promise(() => {}));
//     renderModal();
//     expect(screen.getByText(/loading profile/i)).toBeInTheDocument();
//   });

//   it("renders full name, username, and email after load", async () => {
//     api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
//     renderModal();
//     expect(await screen.findByText("Alice Smith")).toBeInTheDocument();
//     expect(screen.getByText("alice@test.com")).toBeInTheDocument();
//     expect(screen.getByText(/@alice/i)).toBeInTheDocument();
//   });

//   it("displays aggregated total balance across all accounts", async () => {
//     api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
//     renderModal();
//     await screen.findByText("Alice Smith");
//     // $1,000 + $500 = $1,500
//     expect(screen.getByText("$1,500.00")).toBeInTheDocument();
//   });

//   it("shows fallback when API fails", async () => {
//     api.getProfile.mockRejectedValue(new Error("fail"));
//     renderModal();
//     expect(await screen.findByText(/could not load profile/i)).toBeInTheDocument();
//   });

//   it("Close button calls onClose", async () => {
//     api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
//     renderModal();
//     await screen.findByText("Alice Smith");
//     fireEvent.click(screen.getByRole("button", { name: /close/i }));
//     expect(onClose).toHaveBeenCalled();
//   });
// });

/**
 * UserProfileModal.test.jsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import UserProfileModal from "../components/UserProfileModal";

// ── Module mocks ─────────────────────────────────────────────
vi.mock("../api/client", () => ({
  api: { getProfile: vi.fn() },
}));

import { api } from "../api/client";

// ── Fixtures ─────────────────────────────────────────────────
const MOCK_PROFILE = {
  full_name: "Alice Smith",
  username: "alice",
  email: "alice@test.com",
  created_at: "2024-01-01T00:00:00Z",
};

const MOCK_ACCOUNTS = [
  { id: "acc-1", account_type: "checking", account_number: "1234000001" },
  { id: "acc-2", account_type: "savings", account_number: "1234000002" },
];

const MOCK_BALANCES = { "acc-1": 1000, "acc-2": 500 };

const onClose = vi.fn();

const renderModal = () =>
  render(
    <UserProfileModal
      onClose={onClose}
      accounts={MOCK_ACCOUNTS}
      balances={MOCK_BALANCES}
    />
  );

// ── Tests ────────────────────────────────────────────────────
describe("UserProfileModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state while profile is fetching", () => {
    api.getProfile.mockReturnValue(new Promise(() => {}));
    renderModal();

    expect(screen.getByText(/loading profile/i)).toBeInTheDocument();
  });

  it("renders full name, username, and email after load", async () => {
    api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
    renderModal();

    // handle duplicate "Alice Smith"
    const names = await screen.findAllByText("Alice Smith");
    expect(names.length).toBeGreaterThan(0);

    expect(screen.getByText("alice@test.com")).toBeInTheDocument();

    // ✅ FIXED (duplicate-safe)
    const usernames = screen.getAllByText(/@alice/i);
    expect(usernames.length).toBeGreaterThan(0);
  });

  it("displays aggregated total balance across all accounts", async () => {
    api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
    renderModal();

    await screen.findAllByText("Alice Smith");

    expect(screen.getByText("$1,500.00")).toBeInTheDocument();
  });

  it("shows fallback when API fails", async () => {
    api.getProfile.mockRejectedValue(new Error("fail"));
    renderModal();

    expect(
      await screen.findByText(/could not load profile/i)
    ).toBeInTheDocument();
  });

  it("Close button calls onClose", async () => {
    api.getProfile.mockResolvedValue({ data: MOCK_PROFILE });
    renderModal();

    await screen.findAllByText("Alice Smith");

    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});