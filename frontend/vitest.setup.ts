import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { mockState } from "./tests/msw/handlers";
import { server } from "./tests/msw/server";

// Recharts and responsive layouts need these browser APIs, which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
if (typeof Element !== "undefined") {
  Element.prototype.scrollIntoView ??= function scrollIntoView() {};
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  mockState.role = "procurement_manager";
});
afterAll(() => server.close());
