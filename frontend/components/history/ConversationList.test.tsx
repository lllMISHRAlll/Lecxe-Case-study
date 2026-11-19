import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { conversations } from "@/tests/msw/fixtures";
import { server } from "@/tests/msw/server";
import { renderWithProviders } from "@/tests/render";
import { ConversationList } from "./ConversationList";

function setup(activeId: string | null = null) {
  const onOpen = vi.fn();
  const onDeleted = vi.fn();
  const user = userEvent.setup();
  renderWithProviders(<ConversationList activeId={activeId} onOpen={onOpen} onDeleted={onDeleted} />);
  return { user, onOpen, onDeleted };
}

describe("ConversationList", () => {
  it("FE-19 lists the user's conversations, newest first", async () => {
    setup();
    const items = await screen.findAllByRole("button", { name: /^open conversation/i });
    expect(items.map((i) => i.textContent)).toEqual(
      expect.arrayContaining([expect.stringContaining("Which vendors are late?")]),
    );
    expect(items[0]).toHaveTextContent("Which vendors are late?");
    expect(items[1]).toHaveTextContent("Raise a PO");
  });

  it("FE-19 opens the clicked conversation", async () => {
    const { user, onOpen } = setup();
    await user.click(await screen.findByRole("button", { name: /open conversation raise a po/i }));
    expect(onOpen).toHaveBeenCalledWith("conv-2");
  });

  it("marks the active conversation", async () => {
    setup("conv-2");
    const active = await screen.findByRole("button", { name: /open conversation raise a po/i });
    expect(active).toHaveAttribute("aria-current", "true");
  });

  it("FE-19 deletes a conversation and refreshes the list", async () => {
    let deleted = "";
    server.use(
      http.delete("/api/conversations/:id", ({ params }) => {
        deleted = params.id as string;
        server.use(http.get("/api/conversations", () => HttpResponse.json([conversations[1]])));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user, onDeleted } = setup();

    await user.click(await screen.findByRole("button", { name: /delete conversation which vendors are late/i }));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledWith("conv-1"));
    expect(deleted).toBe("conv-1");
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /open conversation which vendors/i })).not.toBeInTheDocument(),
    );
  });

  it("shows an empty state", async () => {
    server.use(http.get("/api/conversations", () => HttpResponse.json([])));
    setup();
    expect(await screen.findByText(/no conversations yet/i)).toBeInTheDocument();
  });

  it("shows an error when the list cannot load", async () => {
    server.use(http.get("/api/conversations", () => new HttpResponse(null, { status: 500 })));
    setup();
    expect(await screen.findByText(/couldn't load your conversations/i)).toBeInTheDocument();
  });
});
