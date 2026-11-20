import { create } from "zustand";
import type {
  ChartSpec,
  ChoicesPayload,
  ConversationDetail,
  MessagePayload,
  PODraft,
  POCreated,
  RowsPayload,
  SqlPayload,
  StepPayload,
  StreamEvent,
} from "@/lib/types";

export interface ChatMessage {
  /** Stable key for rendering. */
  localId: string;
  /** Server message id, known once the stream sends `done` (or from history). */
  id?: string;
  sender: "user" | "assistant";
  text: string;
  streaming?: boolean;
  error?: { message: string; reference?: string };
  choices?: ChoicesPayload;
  poCreated?: POCreated;
}

export interface OutputState {
  /** Increments each time a turn takes over the results pane (keys its animations). */
  turn: number;
  /** The question behind this result, used to name exported files. */
  question: string | null;
  steps: StepPayload[];
  sql: SqlPayload | null;
  rows: RowsPayload | null;
  chart: ChartSpec | null;
  poDraft: PODraft | null;
}

interface ChatState {
  conversationId: string | null;
  title: string | null;
  messages: ChatMessage[];
  /** What the results pane shows: the latest turn that produced a result. */
  output: OutputState;
  /** Every step of the current turn, for the status line in the chat. */
  turnSteps: StepPayload[];
  /** True once the current turn has taken over the results pane. */
  outputLive: boolean;
  streaming: boolean;

  startTurn: (userText?: string) => void;
  applyEvent: (event: StreamEvent) => void;
  finishTurn: () => void;
  loadConversation: (detail: ConversationDetail) => void;
  newConversation: () => void;
}

const emptyOutput = (): OutputState => ({
  turn: 0,
  question: null,
  steps: [],
  sql: null,
  rows: null,
  chart: null,
  poDraft: null,
});

const initialData = () => ({
  conversationId: null,
  title: null,
  messages: [] as ChatMessage[],
  output: emptyOutput(),
  turnSteps: [] as StepPayload[],
  outputLive: false,
  streaming: false,
});

/**
 * Steps that happen on every turn, before we know whether it will produce a result. A chat
 * reply or a refused request only ever emits these, so it leaves the results pane alone.
 */
const PRELUDE_NODES = new Set(["preprocess", "guard_input", "route_intent", "check_po_permission"]);

type Patch = Partial<Pick<ChatState, "output" | "turnSteps" | "outputLive">>;

/** The output with the current turn in charge of it, claiming the pane on first use. */
function liveOutput(state: ChatState): OutputState {
  if (state.outputLive) return state.output;
  return {
    ...emptyOutput(),
    turn: state.output.turn + 1,
    question: state.messages.findLast((m) => m.sender === "user")?.text ?? null,
    steps: state.turnSteps,
    poDraft: state.output.poDraft,
  };
}

function withResult(state: ChatState, change: Partial<OutputState>): Patch {
  return { output: { ...liveOutput(state), ...change }, outputLive: true };
}

const hasResult = (payload: MessagePayload | null | undefined) =>
  Boolean(payload && (payload.sql || payload.rows || payload.chart));

let counter = 0;
const nextLocalId = () => `local-${++counter}`;

/** Applies `change` to the last assistant message, if there is one. */
function updateLastAssistant(
  messages: ChatMessage[],
  change: (message: ChatMessage) => ChatMessage,
): ChatMessage[] {
  const index = messages.findLastIndex((m) => m.sender === "assistant");
  if (index === -1) return messages;
  const next = messages.slice();
  next[index] = change(messages[index]);
  return next;
}

export const useChatStore = create<ChatState>()((set) => ({
  ...initialData(),

  startTurn: (userText) =>
    set((state) => {
      const added: ChatMessage[] = [];
      if (userText) added.push({ localId: nextLocalId(), sender: "user", text: userText });
      added.push({ localId: nextLocalId(), sender: "assistant", text: "", streaming: true });
      // The previous result stays on screen until this turn has one of its own.
      return {
        streaming: true,
        messages: [...state.messages, ...added],
        turnSteps: [],
        outputLive: false,
      };
    }),

  applyEvent: (event) =>
    set((state) => {
      switch (event.event) {
        case "conversation":
          return { conversationId: event.data.conversation_id, title: event.data.title };
        case "step": {
          const turnSteps = [...state.turnSteps, event.data];
          if (!state.outputLive && PRELUDE_NODES.has(event.data.node)) return { turnSteps };
          return { turnSteps, ...withResult({ ...state, turnSteps }, { steps: turnSteps }) };
        }
        case "sql":
          return withResult(state, { sql: event.data });
        case "rows":
          return withResult(state, { rows: event.data });
        case "chart":
          return withResult(state, { chart: event.data });
        case "po_draft":
          return withResult(state, { poDraft: event.data.draft });
        case "token":
          return {
            messages: updateLastAssistant(state.messages, (m) => ({
              ...m,
              text: m.text + event.data.text,
            })),
          };
        case "answer_replace":
          return {
            messages: updateLastAssistant(state.messages, (m) => ({ ...m, text: event.data.text })),
          };
        case "choices":
          return {
            messages: updateLastAssistant(state.messages, (m) => ({ ...m, choices: event.data })),
          };
        case "error":
          return {
            messages: updateLastAssistant(state.messages, (m) => ({ ...m, error: event.data })),
          };
        case "done":
          return {
            messages: updateLastAssistant(state.messages, (m) => ({
              ...m,
              id: event.data.message_id,
            })),
          };
        case "po_created": {
          const draft = state.output.poDraft;
          return {
            messages: updateLastAssistant(state.messages, (m) => ({ ...m, poCreated: event.data })),
            output: {
              ...state.output,
              poDraft: draft ? { ...draft, status: "confirmed" } : null,
            },
          };
        }
      }
    }),

  finishTurn: () =>
    set((state) => ({
      streaming: false,
      messages: updateLastAssistant(state.messages, (m) => ({ ...m, streaming: false })),
    })),

  loadConversation: (detail) =>
    set(() => {
      // The pane shows the latest answer that had a result, not a later chat reply.
      const resultAt = detail.messages.findLastIndex(
        (m) => m.sender === "assistant" && hasResult(m.payload),
      );
      const lastPayload = detail.messages[resultAt]?.payload;
      const question = detail.messages
        .slice(0, Math.max(resultAt, 0))
        .findLast((m) => m.sender === "user")?.text;
      return {
        ...initialData(),
        conversationId: detail.id,
        title: detail.title,
        messages: detail.messages.map((m) => ({
          localId: m.id,
          id: m.id,
          sender: m.sender,
          text: m.text,
          poCreated: m.payload?.po_created,
        })),
        output: {
          turn: 0,
          question: question ?? null,
          steps: lastPayload?.steps ?? [],
          sql: lastPayload?.sql ?? null,
          rows: lastPayload?.rows ?? null,
          chart: lastPayload?.chart ?? null,
          poDraft: detail.open_po_draft,
        },
      };
    }),

  newConversation: () => set(initialData()),

}));

export function resetChatStore() {
  useChatStore.setState(initialData());
}
