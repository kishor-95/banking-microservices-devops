/**
 * parseApiError.test.js
 *
 * Tests the error-normalisation utility that converts FastAPI error shapes
 * (string detail, validation array) into a safe render-ready string.
 * Pure function — no mocks, no React, fast.
 */
import { parseApiError } from "../api/client";

describe("parseApiError", () => {
  it("returns string detail as-is", () => {
    const err = { response: { data: { detail: "Invalid credentials" } } };
    expect(parseApiError(err)).toBe("Invalid credentials");
  });

  it("formats FastAPI 422 validation array into readable string", () => {
    const err = {
      response: {
        data: {
          detail: [
            { loc: ["body", "email"], msg: "value is not a valid email address" },
            { loc: ["body", "password"], msg: "field required" },
          ],
        },
      },
    };
    const result = parseApiError(err);
    expect(result).toMatch(/Email/);
    expect(result).toMatch(/Password/);
    expect(result).toContain("·"); // separator between fields
  });

  it("returns default fallback when no detail present", () => {
    expect(parseApiError({ response: { data: {} } })).toBe(
      "Something went wrong. Try again."
    );
  });

  it("returns default fallback when err has no response", () => {
    expect(parseApiError(new Error("Network Error"))).toBe(
      "Something went wrong. Try again."
    );
  });

  it("accepts a custom fallback string", () => {
    expect(parseApiError({}, "Transaction failed. Try again.")).toBe(
      "Transaction failed. Try again."
    );
  });
});