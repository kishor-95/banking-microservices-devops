import "@testing-library/jest-dom";

// Suppress noisy console.error from React's expected throws (e.g. missing Provider)
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    if (typeof args[0] === "string" && args[0].includes("The above error occurred")) return;
    originalError(...args);
  };
});
afterAll(() => { console.error = originalError; });

// Reset localStorage between every test
beforeEach(() => localStorage.clear());