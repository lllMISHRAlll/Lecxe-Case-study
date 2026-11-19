import { screen } from "@testing-library/react";
import axe from "axe-core";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatPage from "@/app/chat/page";
import LoginPage from "@/app/login/page";
import { renderWithProviders } from "@/tests/render";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

async function violations(container: HTMLElement) {
  const results = await axe.run(container, {
    // jsdom has no layout engine, so contrast cannot be measured here.
    rules: { "color-contrast": { enabled: false } },
  });
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

describe("FE-21 accessibility", () => {
  afterEach(() => window.history.replaceState(null, "", "/"));

  it("the check does detect violations (control)", async () => {
    const { container } = renderWithProviders(
      <main>
        <button type="button">
          <svg aria-hidden="true" />
        </button>
        <input type="text" />
      </main>,
    );
    const found = await violations(container);
    expect(found.some((v) => v.startsWith("button-name"))).toBe(true);
    expect(found.some((v) => v.startsWith("label"))).toBe(true);
  });

  it("login page has no axe violations", async () => {
    const { container } = renderWithProviders(<LoginPage />);
    await screen.findAllByRole("button", { name: /log in as/i });

    expect(await violations(container)).toEqual([]);
  });

  it("chat page with a restored answer and table has no axe violations", async () => {
    window.history.replaceState(null, "", "/chat?c=conv-1");
    const { container } = renderWithProviders(<ChatPage />);
    await screen.findByText("Two vendors have overdue deliveries.");
    await screen.findByRole("button", { name: "Open POs" });

    expect(await violations(container)).toEqual([]);
  });

  it("chat page with an open PO draft has no axe violations", async () => {
    window.history.replaceState(null, "", "/chat?c=conv-2");
    const { container } = renderWithProviders(<ChatPage />);
    await screen.findByRole("region", { name: /purchase order draft/i });

    expect(await violations(container)).toEqual([]);
  });
});
