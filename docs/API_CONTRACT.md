# API Contract

All routes live under `/api`. The Next.js app rewrites `/api/*` to FastAPI, so the browser only
ever talks to one origin and the session cookie (`pa_session`, httpOnly) is sent automatically.

Errors always use this shape:

```json
{ "error": { "code": "invalid_credentials", "message": "Email or password is incorrect.", "reference": "a1b2c3d4" } }
```

## Auth

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/api/auth/demo-users` | | `200 [{ "email", "name", "role", "role_label", "password" }]` (password only outside prod) | |
| POST | `/api/auth/login` | `{ "email", "password" }` | `200 { "user": User }` and sets the cookie | `401`, `422`, `429` |
| GET | `/api/auth/me` | | `200 { "user": User }` | `401` |
| POST | `/api/auth/logout` | | `204`, clears the cookie | |

`User` is `{ "id", "name", "email", "role", "role_label" }`.
`role` is one of `procurement_manager`, `business_owner`, `warehouse_manager`.
`role_label` is `Procurement Manager`, `Business Owner` or `Warehouse Manager`.

## Query buttons

| Method | Path | Success |
|---|---|---|
| GET | `/api/canned` | `200 [{ "id", "label", "description" }]` for the caller's role |

## Chat (streaming)

`POST /api/chat/stream` with one of:

```json
{ "conversation_id": "optional-uuid", "message": "Which vendors are late?" }
{ "conversation_id": "optional-uuid", "button_id": "pm_open_pos" }
{ "conversation_id": "uuid", "po_action": { "type": "confirm", "idempotency_key": "uuid" } }
{ "conversation_id": "uuid", "po_action": { "type": "cancel" } }
{ "conversation_id": "uuid", "po_action": { "type": "choose", "choice": "option-id" } }
```

Exactly one of `message`, `button_id` or `po_action` is allowed, and unknown fields are rejected
with `422`. Option ids come from the `choices` event and look like `kind:value`, for example
`vendor:<id>`, `item:<id>` or `payment_terms:30 Days Credit`.

Response: `text/event-stream`. Each event is `event: <type>` then `data: <json>` then a blank line.

| Event | Data | UI |
|---|---|---|
| `conversation` | `{ "conversation_id", "title" }` | First event of every stream |
| `step` | `{ "node", "label" }` | Step tracker ticks |
| `sql` | `{ "sql", "source": "button" \| "generated" \| "fixed", "attempt" }` | SQL panel |
| `rows` | `{ "columns": [{ "name", "type" }], "rows": [[...]], "row_count", "truncated" }` | Data table |
| `chart` | `ChartSpec` | Chart |
| `token` | `{ "text" }` | Appended to the assistant message |
| `answer_replace` | `{ "text" }` | Replaces the assistant message text |
| `choices` | `{ "prompt", "options": [{ "id", "label" }] }` | Buttons under the message |
| `po_draft` | `{ "draft": PODraft }` | PO confirmation card |
| `po_created` | `{ "po_number", "po_id", "total_amount", "currency" }` | Success message |
| `error` | `{ "message", "reference" }` | Error message, input re-enabled |
| `done` | `{ "message_id" }` | Stream finished |

`ChartSpec`:

```json
{ "type": "bar | horizontal_bar | line | pie | scatter | table",
  "title": "Spend by vendor",
  "x": "vendor", "y": ["spend_inr"],
  "data": [{ "vendor": "Zenith Steels Pvt. Ltd.", "spend_inr": 12650.0 }] }
```

`type: "table"` means no chart, the data table is enough.

`PODraft`:

```json
{ "status": "open | confirmed | cancelled",
  "idempotency_key": "uuid",
  "vendor": { "id", "name" } ,
  "currency": "INR",
  "payment_terms": "30 Days Credit",
  "placed_on": "2026-11-19",
  "delivery_location": { "id", "name" },
  "expected_delivery_date": "2026-11-30",
  "lines": [{ "position": 1, "item": { "id", "code", "name", "unit" }, "quantity": "50",
              "unit": "kg", "unit_price": "120.00", "tax_percentage": "0",
              "line_total": "6000.00", "warnings": ["Unit differs from stock unit"] }],
  "subtotal": "6000.00", "tax_amount": "0.00", "total_amount": "6000.00",
  "missing": ["payment_terms"], "warnings": [] }
```

`vendor`, `delivery_location` and `expected_delivery_date` may be `null`. Money and quantities
are strings, to keep decimals exact. The draft also carries `po_number` once it is confirmed.
Numeric cells in `rows` are JSON numbers or decimal strings; chart `data` values are numbers.

## History

| Method | Path | Success |
|---|---|---|
| GET | `/api/conversations` | `200 [{ "id", "title", "updated_at" }]`, newest first, own only |
| GET | `/api/conversations/{id}` | `200 { "id", "title", "messages": [Message], "open_po_draft": PODraft \| null }` |
| DELETE | `/api/conversations/{id}` | `204` |

`Message` is `{ "id", "sender": "user" | "assistant", "text", "payload", "created_at" }`.
`payload` for assistant messages holds `{ "sql", "rows", "chart", "steps", "po_draft", "po_created" }`,
each optional, in the same shapes as the stream events.

## Feedback

| Method | Path | Body | Success |
|---|---|---|---|
| POST | `/api/feedback` | `{ "message_id", "score": 1 \| -1 }` | `204` |

## Health

`GET /api/health` returns `200 { "status": "ok" }` without auth.
