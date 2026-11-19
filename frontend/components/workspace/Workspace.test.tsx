import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { userFor } from "@/tests/msw/fixtures";
import { server } from "@/tests/msw/server";
import { sse, streamHandler } from "@/tests/msw/stream";
import { renderWithProviders } from "@/tests/render";
import { resetChatStore } from "@/stores/chatStore";
import { Workspace } from "./Workspace";

function deferred() {
  let resolve: () => void = () => {};
  const promise = new Promise<void>((r) => (resolve = r));
  return { promise, resolve };
}

function renderWorkspace() {
  const user = userEvent.setup();
  renderWithProviders(<Workspace user={userFor("procurement_manager")} />);
  return user;
}

async function ask(user: ReturnType<typeof userEvent.setup>, text: string) {
  await user.type(screen.getByRole("textbox", { name: /message/i }), text);
  await user.click(screen.getByRole("button", { name: /^send$/i }));
}

describe("Workspace streaming", () => {
  beforeEach(() => resetChatStore());

  it("FE-09 shows tokens as they arrive, before the stream ends", async () => {
    const gate = deferred();
    server.use(
      http.post("/api/chat/stream", () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream<Uint8Array>({
          async start(controller) {
            controller.enqueue(encoder.encode(sse("token", { text: "Two vendors " })));
            await gate.promise;
            controller.enqueue(encoder.encode(sse("token", { text: "are late." })));
            controller.enqueue(encoder.encode(sse("done", { message_id: "m1" })));
            controller.close();
          },
        });
        return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    const user = renderWorkspace();

    await ask(user, "Which vendors are late?");

    const chat = screen.getByRole("log", { name: /conversation/i });
    expect(within(chat).getByText("Which vendors are late?")).toBeInTheDocument();
    expect(await within(chat).findByText("Two vendors")).toBeInTheDocument();
    expect(within(chat).queryByText("Two vendors are late.")).not.toBeInTheDocument();

    gate.resolve();
    expect(await within(chat).findByText("Two vendors are late.")).toBeInTheDocument();
  });

  it("FE-10 to FE-13 fills the output pane as events arrive", async () => {
    server.use(
      streamHandler([
        sse("conversation", { conversation_id: "c1", title: "Spend" }),
        sse("step", { node: "route_intent", label: "Understood the question" }),
        sse("sql", { sql: "SELECT vendor, spend_inr FROM v LIMIT 500", source: "generated", attempt: 1 }),
        sse("step", { node: "execute_sql", label: "Ran the query" }),
        sse("rows", {
          columns: [
            { name: "vendor", type: "text" },
            { name: "spend_inr", type: "numeric" },
          ],
          rows: [["Zenith", 12650]],
          row_count: 1,
          truncated: false,
        }),
        sse("chart", {
          type: "bar",
          title: "Spend by vendor",
          x: "vendor",
          y: ["spend_inr"],
          data: [{ vendor: "Zenith", spend_inr: 12650 }],
        }),
        sse("token", { text: "Zenith leads spend." }),
        sse("done", { message_id: "m1" }),
      ]),
    );
    const user = renderWorkspace();

    await ask(user, "Spend by vendor");

    expect(await screen.findByText("Zenith leads spend.")).toBeInTheDocument();
    const output = screen.getByRole("region", { name: /results/i });
    expect(await within(output).findByText("Ran the query")).toBeInTheDocument();
    expect(within(output).getByText("Understood the question")).toBeInTheDocument();
    expect(within(output).getByText(/SELECT/)).toBeInTheDocument();
    expect(within(output).getByRole("table")).toBeInTheDocument();
    expect(within(output).getByTestId("chart-bar")).toBeInTheDocument();
  });

  it("FE-14 swaps the answer text on answer_replace", async () => {
    server.use(
      streamHandler([
        sse("token", { text: "Spend is 999." }),
        sse("answer_replace", { text: "Spend is 120." }),
        sse("done", { message_id: "m1" }),
      ]),
    );
    const user = renderWorkspace();

    await ask(user, "spend?");

    const chat = screen.getByRole("log", { name: /conversation/i });
    expect(await within(chat).findByText("Spend is 120.")).toBeInTheDocument();
    expect(within(chat).queryByText("Spend is 999.")).not.toBeInTheDocument();
  });

  it("FE-15 shows an error event and re-enables the input", async () => {
    server.use(
      streamHandler([
        sse("error", { message: "The query timed out.", reference: "ref-42" }),
        sse("done", { message_id: "m1" }),
      ]),
    );
    const user = renderWorkspace();

    await ask(user, "slow question");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The query timed out.");
    expect(alert).toHaveTextContent("ref-42");
    await waitFor(() => expect(screen.getByRole("textbox", { name: /message/i })).toBeEnabled());
  });

  it("FE-15 shows a refused request as an error too", async () => {
    server.use(http.post("/api/chat/stream", () => new HttpResponse(null, { status: 429 })));
    const user = renderWorkspace();

    await ask(user, "again");

    expect(await screen.findByRole("alert")).toHaveTextContent(/too many requests/i);
    expect(screen.getByRole("textbox", { name: /message/i })).toBeEnabled();
  });

  it("shows a network failure as an error", async () => {
    server.use(http.post("/api/chat/stream", () => HttpResponse.error()));
    const user = renderWorkspace();

    await ask(user, "again");

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach the server/i);
  });

  it("sends a button click as button_id and the follow-up with the conversation id", async () => {
    const bodies: unknown[] = [];
    server.use(
      streamHandler(
        [
          sse("conversation", { conversation_id: "c7", title: "Open POs" }),
          sse("token", { text: "Seven open POs." }),
          sse("done", { message_id: "m1" }),
        ],
        (b) => bodies.push(b),
      ),
    );
    const user = renderWorkspace();

    await user.click(await screen.findByRole("button", { name: "Open POs" }));
    expect(await screen.findByText("Seven open POs.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("textbox", { name: /message/i })).toBeEnabled());
    await ask(user, "and the oldest?");

    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[0]).toEqual({ button_id: "pm_open_pos" });
    expect(bodies[1]).toEqual({ conversation_id: "c7", message: "and the oldest?" });
  });

  it("sends with Enter and keeps Shift+Enter for new lines", async () => {
    const bodies: unknown[] = [];
    server.use(streamHandler([sse("done", { message_id: "m" })], (b) => bodies.push(b)));
    const user = renderWorkspace();
    const box = screen.getByRole("textbox", { name: /message/i });

    await user.type(box, "line one{Shift>}{Enter}{/Shift}line two{Enter}");

    await waitFor(() => expect(bodies).toEqual([{ message: "line one\nline two" }]));
  });

  it("does not send an empty message", async () => {
    const user = renderWorkspace();
    expect(screen.getByRole("button", { name: /^send$/i })).toBeDisabled();
    await user.type(screen.getByRole("textbox", { name: /message/i }), "   {Enter}");
    expect(screen.queryByRole("log", { name: /conversation/i })?.textContent ?? "").not.toContain("   ");
  });

  it("hides the results pane until there is a result to show", () => {
    renderWorkspace();
    expect(screen.queryByRole("region", { name: /results/i })).not.toBeInTheDocument();
    expect(screen.getByText(/what would you like to know/i)).toBeInTheDocument();
  });

  it("keeps the pane hidden for a chat-only reply", async () => {
    server.use(
      streamHandler([
        sse("step", { node: "preprocess", label: "Read your message", status: "done" }),
        sse("step", { node: "route_intent", label: "Replying", status: "done" }),
        sse("token", { text: "Hello there." }),
        sse("done", { message_id: "m1" }),
      ]),
    );
    const user = renderWorkspace();
    await ask(user, "hi");
    expect(await screen.findByText("Hello there.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /results/i })).not.toBeInTheDocument();
  });

  it("opens the pane as soon as the turn starts working on a result", async () => {
    const gate = deferred();
    server.use(
      http.post("/api/chat/stream", () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream<Uint8Array>({
          async start(controller) {
            controller.enqueue(encoder.encode(sse("step", { node: "route_intent", label: "Answering from the data" })));
            controller.enqueue(encoder.encode(sse("step", { node: "schema_link", label: "Found the relevant tables" })));
            await gate.promise;
            controller.enqueue(encoder.encode(sse("done", { message_id: "m1" })));
            controller.close();
          },
        });
        return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    const user = renderWorkspace();
    await ask(user, "Which vendors are late?");

    const output = await screen.findByRole("region", { name: /results/i });
    expect(within(output).getByText(/working/i)).toBeInTheDocument();
    expect(await within(output).findByText("Found the relevant tables")).toBeInTheDocument();
    gate.resolve();
    await waitFor(() => expect(within(output).queryByText(/working/i)).not.toBeInTheDocument());
  });
});
