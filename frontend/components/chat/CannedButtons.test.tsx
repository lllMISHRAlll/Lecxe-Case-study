import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { cannedByRole } from "@/tests/msw/fixtures";
import { mockState } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { renderWithProviders } from "@/tests/render";
import type { Role } from "@/lib/types";
import { CannedButtons } from "./CannedButtons";

describe("CannedButtons", () => {
  it.each<Role>(["procurement_manager", "business_owner", "warehouse_manager"])(
    "FE-07 shows exactly the %s's buttons",
    async (role) => {
      mockState.role = role;
      renderWithProviders(<CannedButtons onRun={vi.fn()} />);

      const expected = cannedByRole[role].map((q) => q.label);
      await screen.findByRole("button", { name: expected[0] });
      const labels = screen.getAllByRole("button").map((b) => b.textContent);
      expect(labels).toEqual(expected);
    },
  );

  it("runs the clicked button's query", async () => {
    const onRun = vi.fn();
    renderWithProviders(<CannedButtons onRun={onRun} />);

    await userEvent.click(await screen.findByRole("button", { name: "Overdue deliveries" }));
    expect(onRun).toHaveBeenCalledWith({
      id: "pm_overdue",
      label: "Overdue deliveries",
      description: "Expected date passed",
    });
  });

  it("disables the buttons while an answer is streaming", async () => {
    renderWithProviders(<CannedButtons onRun={vi.fn()} disabled />);
    expect(await screen.findByRole("button", { name: "Open POs" })).toBeDisabled();
  });

  it("says so when the buttons cannot be loaded", async () => {
    server.use(http.get("/api/canned", () => new HttpResponse(null, { status: 500 })));
    renderWithProviders(<CannedButtons onRun={vi.fn()} />);
    expect(await screen.findByText(/couldn't load suggested questions/i)).toBeInTheDocument();
  });

  it("grid variant shows uniform cards with label and description", async () => {
    renderWithProviders(<CannedButtons onRun={vi.fn()} variant="grid" />);
    const card = await screen.findByRole("button", { name: /Overdue deliveries/ });
    expect(card).toHaveTextContent("Expected date passed");

    const buttons = screen.getAllByRole("button");
    const classes = new Set(buttons.map((b) => b.className));
    expect(classes.size).toBe(1);
    expect(screen.getByLabelText("Suggested questions")).toHaveClass("grid");
  });

  it("row variant gives every chip the same size", async () => {
    renderWithProviders(<CannedButtons onRun={vi.fn()} />);
    await screen.findByRole("button", { name: "Open POs" });
    const classes = new Set(screen.getAllByRole("button").map((b) => b.className));
    expect(classes.size).toBe(1);
  });
});
