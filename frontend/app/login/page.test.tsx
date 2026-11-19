import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/render";
import LoginPage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: push }) }));

describe("Login page", () => {
  it("FE-02 moves to /chat after a successful login", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    expect(screen.getByRole("heading", { name: /procurement assistant/i })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /log in as arjun rao/i }));
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/chat"));
  });
});
