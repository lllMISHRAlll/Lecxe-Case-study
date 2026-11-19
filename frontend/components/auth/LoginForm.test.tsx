import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/tests/msw/server";
import { renderWithProviders } from "@/tests/render";
import { LoginForm } from "./LoginForm";

function setup() {
  const onSuccess = vi.fn();
  const user = userEvent.setup();
  renderWithProviders(<LoginForm onSuccess={onSuccess} />);
  return { onSuccess, user };
}

describe("LoginForm", () => {
  it("FE-01 shows three quick-login buttons that fill email and password", async () => {
    const { user } = setup();

    const buttons = await screen.findAllByRole("button", { name: /log in as/i });
    expect(buttons).toHaveLength(3);
    expect(buttons.map((b) => b.textContent)).toEqual([
      expect.stringContaining("Procurement Manager"),
      expect.stringContaining("Business Owner"),
      expect.stringContaining("Warehouse Manager"),
    ]);

    await user.click(screen.getByRole("button", { name: /log in as meera iyer/i }));
    expect(screen.getByLabelText(/email/i)).toHaveValue("owner@demo.local");
    expect(screen.getByLabelText(/password/i)).toHaveValue("1234567890");
  });

  it("FE-02 submits to the login API and reports the signed-in user", async () => {
    const { user, onSuccess } = setup();

    await user.type(screen.getByLabelText(/email/i), "warehouse@demo.local");
    await user.type(screen.getByLabelText(/password/i), "1234567890");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledOnce());
    expect(onSuccess.mock.calls[0][0]).toMatchObject({ name: "Kabir Shah" });
  });

  it("FE-03 shows the server's message when credentials are wrong", async () => {
    const { user, onSuccess } = setup();

    await user.type(screen.getByLabelText(/email/i), "owner@demo.local");
    await user.type(screen.getByLabelText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("shows a generic message when the network fails", async () => {
    server.use(http.post("/api/auth/login", () => HttpResponse.error()));
    const { user } = setup();

    await user.type(screen.getByLabelText(/email/i), "owner@demo.local");
    await user.type(screen.getByLabelText(/password/i), "1234567890");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach the server/i);
  });

  it("disables the submit button while signing in", async () => {
    let release: () => void = () => {};
    server.use(
      http.post("/api/auth/login", async () => {
        await new Promise<void>((resolve) => (release = resolve));
        return HttpResponse.json({ user: { id: "u", name: "A", email: "a", role: "business_owner", role_label: "Business Owner" } });
      }),
    );
    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), "owner@demo.local");
    await user.type(screen.getByLabelText(/password/i), "1234567890");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("button", { name: /signing in/i })).toBeDisabled();
    release();
  });

  it("still allows typed login when demo users cannot be loaded", async () => {
    server.use(http.get("/api/auth/demo-users", () => new HttpResponse(null, { status: 500 })));
    setup();

    expect(await screen.findByText(/quick login is unavailable/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeEnabled();
  });

  it("fills only the email when the server does not share a demo password", async () => {
    server.use(
      http.get("/api/auth/demo-users", () =>
        HttpResponse.json([
          { email: "owner@demo.local", name: "Meera Iyer", role: "business_owner", role_label: "Business Owner" },
        ]),
      ),
    );
    const { user } = setup();

    await user.click(await screen.findByRole("button", { name: /log in as meera iyer/i }));
    expect(screen.getByLabelText(/email/i)).toHaveValue("owner@demo.local");
    expect(screen.getByLabelText(/password/i)).toHaveValue("");
  });
});
