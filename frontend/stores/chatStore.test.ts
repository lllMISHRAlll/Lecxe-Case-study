import { beforeEach, describe, expect, it } from "vitest";
import { conversationDetails, makeDraft } from "@/tests/msw/fixtures";
import { resetChatStore, useChatStore } from "./chatStore";

const store = () => useChatStore.getState();
const lastMessage = () => store().messages.at(-1)!;

describe("chat store", () => {
  beforeEach(() => resetChatStore());

  it("starts a turn with the user's message and an empty streaming answer", () => {
    store().startTurn("Which vendors are late?");

    expect(store().streaming).toBe(true);
    expect(store().messages.map((m) => [m.sender, m.text])).toEqual([
      ["user", "Which vendors are late?"],
      ["assistant", ""],
    ]);
    expect(lastMessage().streaming).toBe(true);
  });

  it("starts a turn without a user message for button clicks and PO actions", () => {
    store().startTurn();
    expect(store().messages.map((m) => m.sender)).toEqual(["assistant"]);
  });

  it("FE-09 appends tokens to the answer as they arrive", () => {
    store().startTurn("q");
    store().applyEvent({ event: "token", data: { text: "Two " } });
    expect(lastMessage().text).toBe("Two ");
    store().applyEvent({ event: "token", data: { text: "vendors." } });
    expect(lastMessage().text).toBe("Two vendors.");
  });

  it("FE-14 replaces the answer text on answer_replace", () => {
    store().startTurn("q");
    store().applyEvent({ event: "token", data: { text: "Spend is 999." } });
    store().applyEvent({ event: "answer_replace", data: { text: "Spend is 120." } });
    expect(lastMessage().text).toBe("Spend is 120.");
  });

  it("records the conversation, steps, SQL, rows and chart", () => {
    store().startTurn("q");
    store().applyEvent({ event: "conversation", data: { conversation_id: "c1", title: "q" } });
    store().applyEvent({ event: "step", data: { node: "route_intent", label: "Understood" } });
    store().applyEvent({ event: "step", data: { node: "execute_sql", label: "Ran query" } });
    store().applyEvent({ event: "sql", data: { sql: "SELECT 1", source: "generated", attempt: 1 } });
    store().applyEvent({
      event: "rows",
      data: { columns: [{ name: "a", type: "int" }], rows: [[1]], row_count: 1, truncated: false },
    });
    store().applyEvent({
      event: "chart",
      data: { type: "bar", title: "t", x: "a", y: ["b"], data: [] },
    });

    expect(store().conversationId).toBe("c1");
    expect(store().title).toBe("q");
    expect(store().output.steps.map((s) => s.label)).toEqual(["Understood", "Ran query"]);
    expect(store().output.sql?.sql).toBe("SELECT 1");
    expect(store().output.rows?.row_count).toBe(1);
    expect(store().output.chart?.type).toBe("bar");
  });

  it("keeps the previous result while a new turn has nothing to show yet", () => {
    store().startTurn("q");
    store().applyEvent({ event: "sql", data: { sql: "SELECT 1", source: "generated", attempt: 1 } });
    store().finishTurn();

    store().startTurn("hi");
    store().applyEvent({ event: "step", data: { node: "preprocess", label: "Read your message" } });
    store().applyEvent({ event: "step", data: { node: "route_intent", label: "Replying" } });

    expect(store().output.sql?.sql).toBe("SELECT 1");
    expect(store().outputLive).toBe(false);
    expect(store().turnSteps.map((s) => s.label)).toEqual(["Read your message", "Replying"]);
  });

  it("replaces the previous result once the new turn starts producing one, keeping the PO draft", () => {
    store().startTurn("q");
    store().applyEvent({ event: "sql", data: { sql: "SELECT 1", source: "generated", attempt: 1 } });
    store().applyEvent({ event: "po_draft", data: { draft: makeDraft() } });
    store().finishTurn();
    const before = store().output.turn;

    store().startTurn("next");
    store().applyEvent({ event: "step", data: { node: "guard_input", label: "Safety checks passed" } });
    expect(store().output.sql?.sql).toBe("SELECT 1");
    store().applyEvent({ event: "step", data: { node: "schema_link", label: "Found the relevant tables" } });

    expect(store().output.sql).toBeNull();
    expect(store().output.poDraft?.status).toBe("open");
    expect(store().output.turn).toBe(before + 1);
    expect(store().outputLive).toBe(true);
    expect(store().output.steps.map((s) => s.node)).toEqual(["guard_input", "schema_link"]);
    expect(store().output.question).toBe("next");

    store().applyEvent({ event: "step", data: { node: "generate_sql", label: "Wrote a query" } });
    expect(store().output.steps).toHaveLength(3);
    expect(store().output.turn).toBe(before + 1);
  });

  it("a result event claims the pane even without a result step first", () => {
    store().startTurn("q");
    store().applyEvent({ event: "step", data: { node: "route_intent", label: "Using a saved query" } });
    store().applyEvent({
      event: "rows",
      data: { columns: [{ name: "a", type: "number" }], rows: [[1]], row_count: 1, truncated: false },
    });
    expect(store().outputLive).toBe(true);
    expect(store().output.steps.map((s) => s.node)).toEqual(["route_intent"]);
  });

  it("a refused PO request does not take over the pane", () => {
    store().startTurn("raise a po");
    store().applyEvent({
      event: "step",
      data: { node: "check_po_permission", label: "Not allowed for this role", status: "error" },
    });
    expect(store().outputLive).toBe(false);
    expect(store().output.steps).toEqual([]);
  });

  it("attaches choices, errors and the server message id to the answer", () => {
    store().startTurn("q");
    store().applyEvent({
      event: "choices",
      data: { prompt: "Which vendor?", options: [{ id: "v1", label: "Zenith" }] },
    });
    store().applyEvent({ event: "error", data: { message: "Failed", reference: "r1" } });
    store().applyEvent({ event: "done", data: { message_id: "m9" } });
    store().finishTurn();

    expect(lastMessage().choices?.options[0].label).toBe("Zenith");
    expect(lastMessage().error).toEqual({ message: "Failed", reference: "r1" });
    expect(lastMessage().id).toBe("m9");
    expect(lastMessage().streaming).toBe(false);
    expect(store().streaming).toBe(false);
  });

  it("marks the draft confirmed when the PO is created", () => {
    store().startTurn();
    store().applyEvent({ event: "po_draft", data: { draft: makeDraft() } });
    store().applyEvent({
      event: "po_created",
      data: { po_number: "PO-2026-0051", po_id: "p", total_amount: "6000.00", currency: "INR" },
    });

    expect(lastMessage().poCreated?.po_number).toBe("PO-2026-0051");
    expect(store().output.poDraft?.status).toBe("confirmed");
  });

  it("ignores po_created when there is no draft", () => {
    store().startTurn();
    store().applyEvent({
      event: "po_created",
      data: { po_number: "PO-2026-0051", po_id: "p", total_amount: "1", currency: "INR" },
    });
    expect(store().output.poDraft).toBeNull();
  });

  it("ignores answer events when there is no assistant message", () => {
    store().applyEvent({ event: "token", data: { text: "stray" } });
    expect(store().messages).toEqual([]);
  });

  it("restores a stored conversation with its last result", () => {
    store().loadConversation(conversationDetails["conv-1"]);

    expect(store().conversationId).toBe("conv-1");
    expect(store().messages.map((m) => m.id)).toEqual(["m1", "m2"]);
    expect(store().output.sql?.sql).toContain("SELECT vendor");
    expect(store().output.rows?.row_count).toBe(2);
    expect(store().output.steps).toHaveLength(1);
    expect(store().output.poDraft).toBeNull();
  });

  it("restores the latest answer that had a result, not a later chat reply", () => {
    const detail = conversationDetails["conv-1"];
    store().loadConversation({
      ...detail,
      messages: [
        ...detail.messages,
        { id: "m7", sender: "user", text: "thanks", payload: null, created_at: "2026-11-19T09:01:00Z" },
        {
          id: "m8",
          sender: "assistant",
          text: "You're welcome.",
          payload: { steps: [{ node: "route_intent", label: "Replying" }] },
          created_at: "2026-11-19T09:01:02Z",
        },
      ],
    });
    expect(store().output.sql?.sql).toContain("SELECT vendor");
    expect(store().output.steps.map((s) => s.label)).toEqual(["Ran the query"]);
    expect(store().output.question).toBe("Which vendors are late?");
  });

  it("restores an open PO draft", () => {
    store().loadConversation(conversationDetails["conv-2"]);
    expect(store().output.poDraft?.status).toBe("open");
  });

  it("starts a new conversation from scratch", () => {
    store().loadConversation(conversationDetails["conv-2"]);
    store().newConversation();
    expect(store().conversationId).toBeNull();
    expect(store().messages).toEqual([]);
    expect(store().output.poDraft).toBeNull();
  });

  it("records feedback on a message", () => {
    store().loadConversation(conversationDetails["conv-1"]);
    store().setFeedback("m2", 1);
    expect(store().messages[1].feedback).toBe(1);
  });

  it("counts edit requests so the input can take focus", () => {
    const before = store().editRequests;
    store().requestEdit();
    expect(store().editRequests).toBe(before + 1);
  });
});
