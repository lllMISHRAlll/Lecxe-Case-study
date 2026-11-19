// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { config, middleware } from "./middleware";

function requestFor(path: string, cookie?: string) {
  const headers = cookie ? { cookie } : undefined;
  return new NextRequest(new URL(path, "http://localhost:3000"), { headers });
}

describe("FE-04 middleware", () => {
  it("sends visitors without a session to /login", () => {
    const response = middleware(requestFor("/chat"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("lets visitors with a session cookie through", () => {
    const response = middleware(requestFor("/chat", "pa_session=token"));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });

  it("always lets the login page through", () => {
    const response = middleware(requestFor("/login"));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });

  it("does not run for API calls or static assets", () => {
    expect(config.matcher[0]).toContain("api");
    expect(config.matcher[0]).toContain("_next");
  });
});
