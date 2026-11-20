import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/tests/msw/server";
import {
  ApiError,
  deleteConversation,
  getCanned,
  getConversation,
  getDemoUsers,
  getMe,
  listConversations,
  login,
  logout,
} from "./api";

describe("API client", () => {
  it("returns parsed JSON on success", async () => {
    const users = await getDemoUsers();
    expect(users).toHaveLength(3);
  });

  it("logs in and returns the user", async () => {
    const user = await login("owner@demo.local", "1234567890");
    expect(user.role).toBe("business_owner");
  });

  it("throws ApiError with the server's message and status on failure", async () => {
    const error = await login("owner@demo.local", "wrong").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 401,
      code: "invalid_credentials",
      message: "Email or password is incorrect.",
      reference: "ref-1",
    });
  });

  it("uses a generic message when the error body is not JSON", async () => {
    server.use(http.get("/api/canned", () => new HttpResponse("boom", { status: 500 })));
    const error = await getCanned().catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 500, code: "http_error" });
    expect((error as ApiError).message).toMatch(/something went wrong/i);
  });

  it("explains a rate limit clearly", async () => {
    server.use(http.get("/api/canned", () => new HttpResponse(null, { status: 429 })));
    const error = (await getCanned().catch((e: unknown) => e)) as ApiError;
    expect(error.message).toMatch(/too many requests/i);
  });

  it("returns undefined for 204 responses", async () => {
    await expect(logout()).resolves.toBeUndefined();
    await expect(deleteConversation("conv-1")).resolves.toBeUndefined();
  });

  it("reads the current user, buttons and conversations", async () => {
    expect((await getMe()).name).toBe("Arjun Rao");
    expect((await getCanned())[0].id).toBe("pm_open_pos");
    expect((await listConversations())[0].id).toBe("conv-1");
    expect((await getConversation("conv-2")).open_po_draft?.status).toBe("open");
  });

  it("sends JSON bodies with credentials", async () => {
    let seen: { body: unknown; credentials: string } | undefined;
    server.use(
      http.post("/api/auth/login", async ({ request }) => {
        seen = { body: await request.json(), credentials: request.credentials };
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await login("owner@demo.local", "pw").catch(() => undefined);
    expect(seen?.body).toEqual({ email: "owner@demo.local", password: "pw" });
    expect(seen?.credentials).toBe("same-origin");
  });
});
