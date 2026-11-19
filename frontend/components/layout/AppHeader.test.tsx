import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { userFor } from "@/tests/msw/fixtures";
import { server } from "@/tests/msw/server";
import { renderWithProviders } from "@/tests/render";
import type { Role } from "@/lib/types";
import { AppHeader } from "./AppHeader";

describe("AppHeader", () => {
  it.each<[Role, string]>([
    ["procurement_manager", "Hey Arjun Rao, Procurement Manager welcome"],
    ["business_owner", "Hey Meera Iyer, Business Owner welcome"],
    ["warehouse_manager", "Hey Kabir Shah, Warehouse Manager welcome"],
  ])("FE-05 greets the %s by name and role", (role, greeting) => {
    renderWithProviders(<AppHeader user={userFor(role)} onLoggedOut={vi.fn()} />);
    expect(screen.getByText(greeting)).toBeInTheDocument();
  });

  it("FE-06 logs out through the API and then reports it", async () => {
    let called = false;
    server.use(
      http.post("/api/auth/logout", () => {
        called = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const onLoggedOut = vi.fn();
    renderWithProviders(<AppHeader user={userFor("business_owner")} onLoggedOut={onLoggedOut} />);

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => expect(onLoggedOut).toHaveBeenCalledOnce());
    expect(called).toBe(true);
  });

  it("still leaves the app when the logout call fails", async () => {
    server.use(http.post("/api/auth/logout", () => HttpResponse.error()));
    const onLoggedOut = vi.fn();
    renderWithProviders(<AppHeader user={userFor("business_owner")} onLoggedOut={onLoggedOut} />);

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => expect(onLoggedOut).toHaveBeenCalledOnce());
  });
});
