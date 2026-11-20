// Types mirroring docs/API_CONTRACT.md. Keep in sync with the backend.

export type Role = "procurement_manager" | "business_owner" | "warehouse_manager";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  role_label: string;
}

export interface DemoUser {
  email: string;
  name: string;
  role: Role;
  role_label: string;
  password?: string;
}

export interface CannedQuery {
  id: string;
  label: string;
  description: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; reference?: string };
}

export type ChartType = "bar" | "horizontal_bar" | "line" | "pie" | "scatter" | "table";

export interface ChartSpec {
  type: ChartType;
  title: string;
  x: string;
  y: string[];
  data: Record<string, string | number | null>[];
}

export interface Column {
  name: string;
  type: string;
}

export interface RowsPayload {
  columns: Column[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  truncated: boolean;
}

export interface SqlPayload {
  sql: string;
  source: "button" | "generated" | "fixed";
  attempt: number;
}

export type StepStatus = "done" | "warn" | "error";

export interface StepPayload {
  node: string;
  label: string;
  /** `warn`: needed a retry. `error`: failed. Older stored steps have no status (done). */
  status?: StepStatus;
}

export interface Choice {
  id: string;
  label: string;
}

export interface ChoicesPayload {
  prompt: string;
  options: Choice[];
  /** True when the user may tick several options and submit them together. */
  multiple?: boolean;
}

export interface Ref {
  id: string;
  name: string;
}

export interface PODraftLine {
  position: number;
  item: { id: string; code: string; name: string; unit: string };
  quantity: string;
  unit: string;
  unit_price: string;
  tax_percentage: string;
  line_total: string;
  warnings: string[];
}

export interface PODraft {
  status: "open" | "confirmed" | "cancelled";
  idempotency_key: string;
  vendor: Ref | null;
  currency: string;
  payment_terms: string | null;
  placed_on: string;
  delivery_location: Ref | null;
  expected_delivery_date: string | null;
  lines: PODraftLine[];
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  missing: string[];
  warnings: string[];
}

export interface POCreated {
  po_number: string;
  po_id: string;
  total_amount: string;
  currency: string;
}

export type StreamEvent =
  | { event: "conversation"; data: { conversation_id: string; title: string } }
  | { event: "step"; data: StepPayload }
  | { event: "sql"; data: SqlPayload }
  | { event: "rows"; data: RowsPayload }
  | { event: "chart"; data: ChartSpec }
  | { event: "token"; data: { text: string } }
  | { event: "answer_replace"; data: { text: string } }
  | { event: "choices"; data: ChoicesPayload }
  | { event: "po_draft"; data: { draft: PODraft } }
  | { event: "po_created"; data: POCreated }
  | { event: "error"; data: { message: string; reference?: string } }
  | { event: "done"; data: { message_id: string } };

export type POAction =
  | { type: "confirm"; idempotency_key: string }
  | { type: "cancel" }
  | { type: "choose"; choice: string }
  | { type: "choose"; choices: string[] };

export interface ChatRequest {
  conversation_id?: string;
  message?: string;
  button_id?: string;
  po_action?: POAction;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface MessagePayload {
  sql?: SqlPayload;
  rows?: RowsPayload;
  chart?: ChartSpec;
  steps?: StepPayload[];
  po_draft?: PODraft;
  po_created?: POCreated;
}

export interface StoredMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  payload: MessagePayload | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  messages: StoredMessage[];
  open_po_draft: PODraft | null;
}
