import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { makeDraft, userFor } from "@/tests/msw/fixtures";
import { server } from "@/tests/msw/server";
import { sse, streamHandler } from "@/tests/msw/stream";
import { renderWithProviders } from "@/tests/render";
import { Workspace } from "./Workspace";

function renderWorkspace() {
  const user = userEvent.setup();
  renderWithProviders(<Workspace user={userFor("procurement_manager")} />);
  return user;
}

async function startDraft(user: ReturnType<typeof userEvent.setup>, bodies: unknown[]) {
  server.use(
    streamHandler(
      [
        sse("conversation", { conversation_id: "c-po", title: "PO" }),
        sse("token", { text: "Here is the draft." }),
        sse("po_draft", { draft: makeDraft({ idempotency_key: "idem-9" }) }),
        sse("done", { message_id: "m1" }),
      ],
      (b) => bodies.push(b),
    ),
  );
  await user.type(screen.getByRole("textbox", { name: /message/i }), "raise a PO{Enter}");
  await screen.findByRole("region", { name: /purchase order draft/i });
  await waitFor(() => expect(screen.getByRole("textbox", { name: /message/i })).toBeEnabled());
}

describe("Workspace PO flow", () => {
  it("FE-16 shows the PO card when a draft arrives", async () => {
    const user = renderWorkspace();
    await startDraft(user, []);
    const output = screen.getByRole("region", { name: /results/i });
    expect(within(output).getByRole("region", { name: /purchase order draft/i })).toBeInTheDocument();
  });

  it("FE-17 sends one confirm request with the idempotency key on a double click", async () => {
    const bodies: unknown[] = [];
    const user = renderWorkspace();
    await startDraft(user, bodies);

    server.use(
      streamHandler(
        [
          sse("po_created", { po_number: "PO-2026-0051", po_id: "p1", total_amount: "6000.00", currency: "INR" }),
          sse("done", { message_id: "m2" }),
        ],
        (b) => bodies.push(b),
      ),
    );
    await user.dblClick(screen.getByRole("button", { name: /confirm/i }));

    expect(await screen.findByText(/purchase order PO-2026-0051 created/i)).toBeInTheDocument();
    expect(bodies.slice(1)).toEqual([
      { conversation_id: "c-po", po_action: { type: "confirm", idempotency_key: "idem-9" } },
    ]);
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
  });

  it("FE-18 sends cancel, and Edit focuses the input for a change", async () => {
    const bodies: unknown[] = [];
    const user = renderWorkspace();
    await startDraft(user, bodies);

    await user.click(screen.getByRole("button", { name: /edit/i }));
    const input = screen.getByRole("textbox", { name: /message/i });
    expect(input).toHaveFocus();
    expect(input).toHaveAttribute("placeholder", expect.stringMatching(/change price to/i));
    expect(bodies).toHaveLength(1);

    server.use(
      streamHandler(
        [
          sse("po_draft", { draft: makeDraft({ status: "cancelled" }) }),
          sse("token", { text: "Draft cancelled." }),
          sse("done", { message_id: "m3" }),
        ],
        (b) => bodies.push(b),
      ),
    );
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(await screen.findByText("Draft cancelled.")).toBeInTheDocument();
    expect(bodies[1]).toEqual({ conversation_id: "c-po", po_action: { type: "cancel" } });
  });

  it("sends a chosen option as a choose action", async () => {
    const bodies: unknown[] = [];
    server.use(
      streamHandler(
        [
          sse("conversation", { conversation_id: "c-ch", title: "PO" }),
          sse("token", { text: "Which vendor?" }),
          sse("choices", {
            prompt: "Pick a vendor",
            options: [{ id: "v2", label: "Granite Steels Pvt. Ltd." }],
          }),
          sse("done", { message_id: "m1" }),
        ],
        (b) => bodies.push(b),
      ),
    );
    const user = renderWorkspace();
    await user.type(screen.getByRole("textbox", { name: /message/i }), "PO from steels{Enter}");
    const option = await screen.findByRole("button", { name: "Granite Steels Pvt. Ltd." });
    await waitFor(() => expect(option).toBeEnabled());

    await user.click(option);

    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1]).toEqual({ conversation_id: "c-ch", po_action: { type: "choose", choice: "v2" } });
  });
});
