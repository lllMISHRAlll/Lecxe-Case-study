import type {
  CannedQuery,
  ConversationDetail,
  ConversationSummary,
  DemoUser,
  PODraft,
  Role,
  User,
} from "@/lib/types";

export const demoUsers: DemoUser[] = [
  {
    email: "procurement@demo.local",
    name: "Arjun Rao",
    role: "procurement_manager",
    role_label: "Procurement Manager",
    password: "1234567890",
  },
  {
    email: "owner@demo.local",
    name: "Meera Iyer",
    role: "business_owner",
    role_label: "Business Owner",
    password: "1234567890",
  },
  {
    email: "warehouse@demo.local",
    name: "Kabir Shah",
    role: "warehouse_manager",
    role_label: "Warehouse Manager",
    password: "1234567890",
  },
];

export function userFor(role: Role): User {
  const demo = demoUsers.find((u) => u.role === role)!;
  return {
    id: `user-${role}`,
    name: demo.name,
    email: demo.email,
    role,
    role_label: demo.role_label,
  };
}

export const cannedByRole: Record<Role, CannedQuery[]> = {
  procurement_manager: [
    { id: "pm_open_pos", label: "Open POs", description: "Open POs with value and age" },
    { id: "pm_overdue", label: "Overdue deliveries", description: "Expected date passed" },
  ],
  business_owner: [
    { id: "bo_top_vendors", label: "Top vendors by spend", description: "Spend per vendor" },
  ],
  warehouse_manager: [
    { id: "wm_stock", label: "Current stock by warehouse", description: "Stock per location" },
    { id: "wm_inbound", label: "Expected inbound", description: "Open PO lines" },
  ],
};

export const conversations: ConversationSummary[] = [
  { id: "conv-1", title: "Which vendors are late?", updated_at: "2026-11-19T09:00:00Z" },
  { id: "conv-2", title: "Raise a PO", updated_at: "2026-11-18T09:00:00Z" },
];

export function makeDraft(overrides: Partial<PODraft> = {}): PODraft {
  return {
    status: "open",
    idempotency_key: "idem-1",
    vendor: { id: "v1", name: "Zenith Steels Pvt. Ltd." },
    currency: "INR",
    payment_terms: "30 Days Credit",
    placed_on: "2026-11-19",
    delivery_location: { id: "l1", name: "132-1" },
    expected_delivery_date: "2026-11-30",
    lines: [
      {
        position: 1,
        item: { id: "i1", code: "RM-MT-0001", name: "MS Tube – 25×40×2mm", unit: "kg" },
        quantity: "50",
        unit: "kg",
        unit_price: "120.00",
        tax_percentage: "0",
        line_total: "6000.00",
        warnings: [],
      },
    ],
    subtotal: "6000.00",
    tax_amount: "0.00",
    total_amount: "6000.00",
    missing: [],
    warnings: [],
    ...overrides,
  };
}

export const conversationDetails: Record<string, ConversationDetail> = {
  "conv-1": {
    id: "conv-1",
    title: "Which vendors are late?",
    open_po_draft: null,
    messages: [
      {
        id: "m1",
        sender: "user",
        text: "Which vendors are late?",
        payload: null,
        created_at: "2026-11-19T09:00:00Z",
      },
      {
        id: "m2",
        sender: "assistant",
        text: "Two vendors have overdue deliveries.",
        payload: {
          sql: { sql: "SELECT vendor FROM late LIMIT 500", source: "generated", attempt: 1 },
          rows: {
            columns: [{ name: "vendor", type: "text" }],
            rows: [["Zenith Steels Pvt. Ltd."], ["Anand Engineering Pvt. Ltd."]],
            row_count: 2,
            truncated: false,
          },
          steps: [{ node: "execute_sql", label: "Ran the query" }],
        },
        created_at: "2026-11-19T09:00:05Z",
      },
    ],
  },
  "conv-2": {
    id: "conv-2",
    title: "Raise a PO",
    open_po_draft: makeDraft(),
    messages: [
      {
        id: "m3",
        sender: "user",
        text: "Raise a PO for 50 MS tubes from Zenith at 120",
        payload: null,
        created_at: "2026-11-18T09:00:00Z",
      },
      {
        id: "m4",
        sender: "assistant",
        text: "Here is the draft. Please confirm.",
        payload: { po_draft: makeDraft() },
        created_at: "2026-11-18T09:00:03Z",
      },
    ],
  },
};

/** Builds an SSE body from a list of [event, data] pairs. */
export function sseBody(events: [string, unknown][]): string {
  return events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join("");
}
