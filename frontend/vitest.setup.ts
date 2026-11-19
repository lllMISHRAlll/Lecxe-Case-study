import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { resetChatStore } from "./stores/chatStore";
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

/**
 * jsdom's AbortSignal is not accepted by Node's Request/fetch. Wrap fetch (outside MSW) so the
 * signal is dropped from the request and an AbortError is raised when it fires, as in a browser.
 */
function bridgeAbortSignals() {
  if (typeof window === "undefined") return;
  const innerFetch = globalThis.fetch;
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const signal = init?.signal;
    if (!signal) return innerFetch(input, init);
    const { signal: _dropped, ...rest } = init;
    void _dropped;
    return new Promise<Response>((resolve, reject) => {
      const abort = () => reject(new DOMException("The operation was aborted.", "AbortError"));
      if (signal.aborted) return abort();
      signal.addEventListener("abort", abort, { once: true });
      innerFetch(input, rest).then(resolve, reject);
    });
  };
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  bridgeAbortSignals();
});
afterEach(() => {
  cleanup();
  // The app mirrors the open conversation into ?c=; never let it leak into the next test.
  if (typeof window !== "undefined") window.history.replaceState(null, "", "/");
  server.resetHandlers();
  mockState.role = "procurement_manager";
  resetChatStore();
});
afterAll(() => server.close());
