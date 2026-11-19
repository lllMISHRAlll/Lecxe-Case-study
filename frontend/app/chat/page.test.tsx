import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockState } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { renderWithProviders } from "@/tests/render";
import ChatPage from "./page";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: replace, replace }) }));

describe("Chat page", () => {
  beforeEach(() => replace.mockClear());

  it("greets the signed-in user and shows the chat, with no results pane until there is a result", async () => {
    mockState.role = "warehouse_manager";
    renderWithProviders(<ChatPage />);

    expect(await screen.findByText("Hey Kabir Shah, Warehouse Manager welcome")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Chat" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /results/i })).not.toBeInTheDocument();
  });

  it("sends visitors with an expired session to /login", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ error: { code: "unauthorised", message: "Please sign in." } }, { status: 401 }),
      ),
    );
    renderWithProviders(<ChatPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("shows a retry message when the user cannot be loaded for another reason", async () => {
    server.use(http.get("/api/auth/me", () => new HttpResponse(null, { status: 500 })));
    renderWithProviders(<ChatPage />);
    expect(await screen.findByText(/couldn't load your session/i)).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("FE-06 returns to /login after logging out", async () => {
    renderWithProviders(<ChatPage />);
    await userEvent.click(await screen.findByRole("button", { name: /log out/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("shows the app layout as a skeleton while the session loads", async () => {
    renderWithProviders(<ChatPage />);
    expect(screen.getByRole("status", { name: "Loading your workspace" })).toBeInTheDocument();
    expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
    expect(await screen.findByText("Hey Arjun Rao, Procurement Manager welcome")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading your workspace" })).not.toBeInTheDocument();
  });
});
