import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeDraft } from "@/tests/msw/fixtures";
import type { PODraft } from "@/lib/types";
import { POCard } from "./POCard";

function setup(draft: PODraft, busy = false) {
  const handlers = { onConfirm: vi.fn(), onCancel: vi.fn() };
  const user = userEvent.setup();
  render(<POCard draft={draft} busy={busy} {...handlers} />);
  return { user, ...handlers };
}

describe("POCard", () => {
  it("FE-16 shows the header, lines and totals", () => {
    setup(makeDraft());
    const card = screen.getByRole("region", { name: /purchase order draft/i });

    expect(within(card).getByText("Zenith Steels Pvt. Ltd.")).toBeInTheDocument();
    expect(within(card).getByText("30 Days Credit")).toBeInTheDocument();
    expect(within(card).getByText("132-1")).toBeInTheDocument();
    expect(within(card).getByText("2026-11-30")).toBeInTheDocument();
    expect(within(card).getByText("2026-11-19")).toBeInTheDocument();

    const line = within(card).getAllByRole("row")[1];
    expect(line).toHaveTextContent("RM-MT-0001");
    expect(line).toHaveTextContent("MS Tube – 25×40×2mm");
    expect(line).toHaveTextContent("50 kg");
    expect(line).toHaveTextContent("120.00");
    expect(line).toHaveTextContent("6,000.00");

    expect(within(card).getByText("Subtotal").nextSibling).toHaveTextContent("INR 6,000.00");
    expect(within(card).getByText("Tax").nextSibling).toHaveTextContent("INR 0.00");
    expect(within(card).getByText("Total").nextSibling).toHaveTextContent("INR 6,000.00");
  });

  it("shows placeholders for details not chosen yet", () => {
    setup(
      makeDraft({
        vendor: null,
        payment_terms: null,
        delivery_location: null,
        expected_delivery_date: null,
        lines: [],
      }),
    );
    expect(screen.getByText("Vendor not chosen yet")).toBeInTheDocument();
    expect(screen.getAllByText("Not set")).toHaveLength(3);
    expect(screen.getByText(/no items yet/i)).toBeInTheDocument();
  });

  it("lists missing details and blocks Confirm until they are filled", () => {
    setup(makeDraft({ missing: ["payment_terms", "unit_price"] }));
    expect(screen.getByText(/still needed: payment terms, unit price/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
  });

  it("shows draft and line warnings", () => {
    const draft = makeDraft({ warnings: ["Vendor has no payment terms on file"] });
    draft.lines[0].warnings = ["Unit differs from stock unit"];
    setup(draft);
    expect(screen.getByText("Vendor has no payment terms on file")).toBeInTheDocument();
    expect(screen.getByText("Unit differs from stock unit")).toBeInTheDocument();
  });

  it("FE-17 confirms once with the draft's idempotency key, even on a double click", async () => {
    const { user, onConfirm } = setup(makeDraft({ idempotency_key: "idem-77" }));

    await user.dblClick(screen.getByRole("button", { name: /confirm/i }));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith("idem-77");
    expect(screen.getByRole("button", { name: /confirming/i })).toBeDisabled();
  });

  it("FE-18 offers only Confirm and Cancel, and sends Cancel to its handler", async () => {
    const { user, onCancel } = setup(makeDraft());

    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("disables every action while a reply is streaming", () => {
    setup(makeDraft(), true);
    for (const name of [/confirm/i, /cancel/i]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
  });

  it.each([
    ["confirmed", "Confirmed"],
    ["cancelled", "Cancelled"],
  ] as const)("shows a %s draft without actions", (status, label) => {
    setup(makeDraft({ status }));
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
