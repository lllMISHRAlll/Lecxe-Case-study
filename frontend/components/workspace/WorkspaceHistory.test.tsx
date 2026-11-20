import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";
import { userFor } from "@/tests/msw/fixtures";
import { server } from "@/tests/msw/server";
import { sse, streamHandler } from "@/tests/msw/stream";
import { renderWithProviders } from "@/tests/render";
import { Workspace } from "./Workspace";

function renderWorkspace() {
  const user = userEvent.setup();
  renderWithProviders(<Workspace user={userFor("procurement_manager")} />);
  return user;
}

describe("Workspace history and restore", () => {
  afterEach(() => window.history.replaceState(null, "", "/"));

  it("FE-19 opens a past conversation with its messages and open PO draft", async () => {
    const user = renderWorkspace();

    await user.click(screen.getByRole("button", { name: /history/i }));
    await user.click(await screen.findByRole("button", { name: /open conversation raise a po/i }));

    const chat = screen.getByRole("log", { name: /conversation/i });
    expect(await within(chat).findByText("Here is the draft. Please confirm.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /purchase order draft/i })).toBeInTheDocument();
    expect(window.location.search).toBe("?c=conv-2");
  });

  it("restores the conversation named in the URL after a refresh", async () => {
    window.history.replaceState(null, "", "/chat?c=conv-1");
    renderWorkspace();

    expect(await screen.findByText("Two vendors have overdue deliveries.")).toBeInTheDocument();
    const output = screen.getByRole("region", { name: /results/i });
    expect(within(output).getByRole("table")).toBeInTheDocument();
  });

  it("starts fresh when the conversation in the URL no longer exists", async () => {
    window.history.replaceState(null, "", "/chat?c=missing");
    renderWorkspace();

    expect(await screen.findByText(/couldn't open that conversation/i)).toBeInTheDocument();
    await waitFor(() => expect(window.location.search).toBe(""));
  });

  it("records a new conversation id in the URL as soon as the stream names it", async () => {
    server.use(
      streamHandler([
        sse("conversation", { conversation_id: "c-new", title: "Q" }),
        sse("token", { text: "Answer" }),
        sse("done", { message_id: "m1" }),
      ]),
    );
    const user = renderWorkspace();

    await user.type(screen.getByRole("textbox", { name: /message/i }), "Q{Enter}");

    await waitFor(() => expect(window.location.search).toBe("?c=c-new"));
  });

  it("New chat clears the screen and the URL", async () => {
    window.history.replaceState(null, "", "/chat?c=conv-1");
    const user = renderWorkspace();
    await screen.findByText("Two vendors have overdue deliveries.");

    await user.click(screen.getByRole("button", { name: /new chat/i }));

    expect(screen.queryByText("Two vendors have overdue deliveries.")).not.toBeInTheDocument();
    expect(window.location.search).toBe("");
  });

  it("deleting the open conversation starts a new one", async () => {
    window.history.replaceState(null, "", "/chat?c=conv-1");
    const user = renderWorkspace();
    await screen.findByText("Two vendors have overdue deliveries.");

    await user.click(screen.getByRole("button", { name: /history/i }));
    await user.click(await screen.findByRole("button", { name: /delete conversation which vendors are late/i }));

    await waitFor(() =>
      expect(screen.queryByText("Two vendors have overdue deliveries.")).not.toBeInTheDocument(),
    );
  });

  it("opens history as an overlay without moving the chat", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Workspace user={userFor("procurement_manager")} />);
    const log = screen.getByRole("log", { name: /conversation/i });
    const before = log.previousElementSibling;

    await user.click(screen.getByRole("button", { name: /history/i }));

    expect(screen.getByRole("dialog", { name: "Conversations" })).toBeInTheDocument();
    expect(log.previousElementSibling).toBe(before);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows skeletons, not the empty screens, while a reload restores the conversation", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    server.use(
      http.get("/api/conversations/:id", async () => {
        await gate;
        return HttpResponse.json({
          id: "conv-slow", title: "Overdue check", open_po_draft: null,
          messages: [
            { id: "u1", sender: "user", text: "Which deliveries are late?", payload: {}, created_at: null },
            { id: "a1", sender: "assistant", text: "Two are late.", payload: {}, created_at: null },
          ],
        });
      }),
    );
    window.history.replaceState(null, "", "/chat?c=conv-slow");
    renderWorkspace();

    expect(screen.getByRole("status", { name: "Loading conversation" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Loading results" })).toBeInTheDocument();
    expect(screen.queryByText(/what would you like to know/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/results appear here/i)).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /message/i })).toBeDisabled();

    release();
    expect(await screen.findByText("Two are late.")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading conversation" })).not.toBeInTheDocument();
  });

  it("shows the skeleton while opening a conversation from history", async () => {
    server.use(
      http.get("/api/conversations/:id", async () => {
        await delay(150);
        return HttpResponse.json({
          id: "conv-1", title: "Late deliveries", open_po_draft: null,
          messages: [{ id: "a1", sender: "assistant", text: "Loaded.", payload: {}, created_at: null }],
        });
      }),
    );
    const user = renderWorkspace();
    await user.click(screen.getByRole("button", { name: /history/i }));
    const [first] = await screen.findAllByRole("button", { name: /open conversation/i });
    await user.click(first);

    expect(screen.getByRole("status", { name: "Loading conversation" })).toBeInTheDocument();
    expect(await screen.findByText("Loaded.")).toBeInTheDocument();
  });
});
