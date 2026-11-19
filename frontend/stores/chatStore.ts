import { create } from "zustand";
import type {
  ChartSpec,
  ChoicesPayload,
  ConversationDetail,
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
  feedback?: 1 | -1;
}

export interface OutputState {
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
  output: OutputState;
  streaming: boolean;
  /** Increments when the user asks to edit a PO draft, so the input can take focus. */
  editRequests: number;

  startTurn: (userText?: string) => void;
  applyEvent: (event: StreamEvent) => void;
  finishTurn: () => void;
  loadConversation: (detail: ConversationDetail) => void;
  newConversation: () => void;
  setFeedback: (messageId: string, score: 1 | -1) => void;
  requestEdit: () => void;
}

const emptyOutput = (): OutputState => ({
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
  streaming: false,
  editRequests: 0,
});

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
      return {
        streaming: true,
        messages: [...state.messages, ...added],
        output: { ...emptyOutput(), poDraft: state.output.poDraft },
      };
    }),

  applyEvent: (event) =>
    set((state) => {
      switch (event.event) {
        case "conversation":
          return { conversationId: event.data.conversation_id, title: event.data.title };
        case "step":
          return { output: { ...state.output, steps: [...state.output.steps, event.data] } };
        case "sql":
          return { output: { ...state.output, sql: event.data } };
        case "rows":
          return { output: { ...state.output, rows: event.data } };
        case "chart":
          return { output: { ...state.output, chart: event.data } };
        case "po_draft":
          return { output: { ...state.output, poDraft: event.data.draft } };
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
      const lastPayload = detail.messages.findLast((m) => m.sender === "assistant")?.payload;
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
          steps: lastPayload?.steps ?? [],
          sql: lastPayload?.sql ?? null,
          rows: lastPayload?.rows ?? null,
          chart: lastPayload?.chart ?? null,
          poDraft: detail.open_po_draft,
        },
      };
    }),

  newConversation: () => set(initialData()),

  setFeedback: (messageId, score) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === messageId ? { ...m, feedback: score } : m)),
    })),

  requestEdit: () => set((state) => ({ editRequests: state.editRequests + 1 })),
}));

export function resetChatStore() {
  useChatStore.setState(initialData());
}
