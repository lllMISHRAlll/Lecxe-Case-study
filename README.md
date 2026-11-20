<div align="center">
  <h1>
    <b>Procurement Assistant</b>
  </h1>
</div>

Procurement Assistant is an RBAC-aware AI assistant for a manufacturer's purchasing and inventory data. People sign in as one of three roles, ask questions in plain English or click suggested questions, and get answers with tables, charts and a short explanation streamed into a split screen. The Procurement Manager can also raise real purchase orders by describing them in chat.

Built test-first with FastAPI, LangGraph, a switchable LLM provider (OpenAI or Anthropic) and Next.js.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.13)
- Node 24
- Git

### Clone Project

```bash
git clone <your-repository-url>
cd <project-folder>
```

### 🔐 Environment Setup

1. Create your environment file in the project root:
```bash
cp .env.example .env
```

2. Configure the following variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL of the company database (SSL required) | "postgresql://user:password@host:port/dbname" |
| `DATABASE_SSLMODE` | SSL mode for the company database | "require" |
| `LLM_PROVIDER` | Which AI provider to use: `openai` or `anthropic` | "anthropic" |
| `OPENAI_API_KEY` | OpenAI key, used when `LLM_PROVIDER=openai` | "sk-..." |
| `ANTHROPIC_API_KEY` | Anthropic key, used when `LLM_PROVIDER=anthropic` | "sk-ant-..." |
| `JWT_SECRET` | Secret used to sign the session cookie | "a-long-random-string" |
| `DEMO_LOGIN_PASSWORD` | Password for the three demo users | "..." |
| `APP_ENV` | `dev`, `test` or `prod` (prod hides the demo password) | "dev" |
| `FX_USD_INR` | USD to INR rate used in answers | "88" |
| `LANGSMITH_API_KEY` | LangSmith key for tracing (optional) | "lsv2_..." |
| `LANGSMITH_PROJECT` | LangSmith project name (optional) | "procurement-assistant" |

### Notes:
- Only the selected provider's key is needed. Without it the app falls back to an offline rule-based stand-in (`FAKE_LLM`) so it still runs end to end for demos and tests. The backend log warns when that happens.
- Tracing turns on only when `LANGSMITH_TRACING=true` and a LangSmith key is set.
- Never commit `.env`.

### Start the app

```bash
make install        # backend and frontend dependencies
make testdb         # local Postgres for tests (port 55432)
make migrate        # creates the `assistant` schema in the company DB (once)
make dev-backend    # http://localhost:8000
make dev-frontend   # http://localhost:3000
```

Or run everything in containers:

```bash
make up             # builds and starts backend + frontend
make down           # stops and removes containers
```

## 🔌 Local Development URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | `http://localhost:3000` | Next.js application |
| Backend | `http://localhost:8000` | FastAPI server |
| API Docs | `http://localhost:8000/api/docs` | Swagger API documentation |
| Health | `http://localhost:8000/api/health` | Liveness check |

### Demo users

| Login | Role | Can do |
|-------|------|--------|
| `procurement@demo.local` | Procurement Manager | Questions on purchasing and stock, 7 suggested questions, **raise POs** |
| `owner@demo.local` | Business Owner | Questions on everything, 6 suggested questions on spend and vendor performance |
| `warehouse@demo.local` | Warehouse Manager | Questions on stock and deliveries, 7 suggested questions, no payment schedules |

Users and permissions live in code (`backend/app/auth`, `backend/app/rbac`) and are enforced on the server for every request.

## ⚡ Features

- 🔐 **Role-based access:** each role sees only its tables, suggested questions and actions. Checked in the schema shown to the model, in the SQL validator and again on every PO action.
- 🤖 **Natural language to SQL:** a SQL agent links tables, writes one query, validates it and repairs it up to three times.
- ⚡ **Saved questions:** one-click, pre-reviewed queries per role. No SQL is generated for them.
- 📊 **Smart visualisations:** chart type chosen by saved hint, then fixed rules on the result shape, and only then by a model.
- 🧾 **Raise purchase orders in chat:** extracts vendor, items, quantities and prices, matches them to the catalogue, asks only for what is missing, shows a confirmation card, then inserts in one transaction. Several items can be pasted at once, and ambiguous items are offered as tick boxes.
- 🛡️ **Guardrails:** input cleaning and masking, prompt-injection rules plus a classifier, SQL parser checks, read-only sessions, and a check that every number in an answer exists in the data.
- 🔄 **Switchable LLM provider:** OpenAI or Anthropic behind one interface, with a fast tier and a strong tier.
- 📡 **Streaming UI:** steps, SQL, rows, chart, tokens and the PO card arrive as server-sent events.
- 🕘 **Chat history:** conversations, messages and open PO drafts are stored and restored on reload.
- 🔭 **Observability:** one LangSmith trace per turn, with agents, tools and LLM calls labelled, masked before upload.
- 📥 **Export:** copy the SQL, download results as CSV or Excel.
- 🌗 **Dark mode.**

## 🛠️ Tech Stack

### Frontend Modules

| Module | Description |
|--------|-------------|
| `next` | React framework (App Router) |
| `react` / `react-dom` | UI library |
| `@tanstack/react-query` | Server-state fetching and caching |
| `zustand` | Lightweight client state for the chat stream |
| `recharts` | Charts |
| `fflate` | Client-side Excel (XLSX) export |
| `tailwindcss` | Utility-first CSS |

### Backend Modules

| Module | Description |
|--------|-------------|
| `fastapi` / `uvicorn` | API framework and server |
| `langgraph` | Orchestration of the agent graph and its subgraphs |
| `langchain-core` / `langchain-openai` | Runnable interfaces and the OpenAI adapter |
| `anthropic` | Official SDK for the Anthropic adapter |
| `langsmith` | Tracing, masking and feedback |
| `sqlglot` | Parser-based SQL validation |
| `sqlalchemy` / `psycopg` | Database access (read-only and write engines) |
| `alembic` | Migrations for the `assistant` schema |
| `rapidfuzz` | Fuzzy matching of vendors, items and locations |
| `pydantic` / `pydantic-settings` | Typed requests, LLM outputs and settings |
| `pyjwt` / `bcrypt` | Session cookie and password hashing |

### Development Tools

| Tool | Purpose |
|------|---------|
| `pytest` / `pytest-cov` | Backend tests and coverage gates |
| `ruff` / `mypy` | Linting and type checking |
| `vitest` / React Testing Library / `msw` | Frontend tests |
| `typescript` / `eslint` | Frontend types and linting |
| `docker compose` | Local Postgres for tests and containerised run |

## 🔄 Workflow Architecture

### High level flow

```mermaid
flowchart TD
    Start([User message or button]) --> Clean[Clean and mask the input]
    Clean --> Guard{Safe?}
    Guard -->|No| Refuse[Fixed refusal]
    Guard -->|Yes| Rewrite[Rewrite follow-up into a full question]
    Rewrite --> Route{Route}

    Route -->|Saved question| Canned[(Pre-written SQL for the role)]
    Route -->|Data question| SqlAgent[SQL agent: link, write, validate, fix]
    Route -->|Raise PO| Perm{Role allowed?}
    Route -->|Small talk| Chat[Friendly reply]
    Route -->|Unclear| Clarify[Ask for detail]

    Perm -->|No| Denied[Fixed refusal]
    Perm -->|Yes| PoFlow[PO flow: extract, match, ask, confirm]

    Canned --> Run[Run read-only]
    SqlAgent --> Run
    Run --> Reduce[Summarise rows]
    Reduce --> Chart[Choose chart]
    Reduce --> Answer[Write answer]
    Answer --> Check[Check numbers against data]

    PoFlow --> Reply[Reply]
    Chat --> Reply
    Clarify --> Reply
    Denied --> Reply
    Refuse --> Reply

    Chart --> Save[(Save to history)]
    Check --> Save
    Reply --> Save
    Save --> End([Stream finished])

    classDef db fill:#f9f,stroke:#333,stroke-width:2px
    class Canned,Save db
```

### LangGraph flow (main graph)

The main graph is one LangGraph `StateGraph`. `sql_agent` and `po_flow` are compiled subgraphs added as nodes. One user message or button click is one graph run. A PO conversation spans several runs, with the draft saved in the database between them.

```mermaid
flowchart TD
    START([START]) --> preprocess[preprocess]
    preprocess --> guard_input[guard_input]
    guard_input -->|blocked: reply already set| reply
    guard_input -->|allowed| rewrite_followup[rewrite_followup]
    rewrite_followup --> route_intent{route_intent}

    route_intent -->|canned| load_canned_sql[load_canned_sql]
    route_intent -->|analytics| sql_agent[[sql_agent subgraph]]
    route_intent -->|raise_po| check_po_permission[check_po_permission]
    route_intent -->|chit_chat| chat[chat]
    route_intent -->|clarify| ask_clarify[ask_clarify]

    load_canned_sql --> execute_sql[execute_sql]
    sql_agent -->|query ready| execute_sql
    sql_agent -->|gave up or not answerable| reply
    execute_sql -->|rows| reduce_results[reduce_results]
    execute_sql -->|runtime error, attempts left| sql_agent
    execute_sql -->|error, no retry| reply

    reduce_results --> choose_chart[choose_chart]
    reduce_results --> write_answer[write_answer]
    write_answer --> check_answer[check_answer]

    check_po_permission -->|denied| reply
    check_po_permission -->|allowed| po_flow[[po_flow subgraph]]
    po_flow --> reply
    chat --> reply
    ask_clarify --> reply

    choose_chart --> save_history
    check_answer --> save_history
    reply[reply] --> save_history[save_history]
    save_history --> END([END])

    classDef cond fill:#f9f,stroke:#333,stroke-width:2px
    classDef agent fill:#ece8fb,stroke:#5a3dcc,stroke-width:2px
    class route_intent cond
    class sql_agent,po_flow agent
```

`choose_chart` and `write_answer` run in parallel. `save_history` waits for both.

### SQL agent subgraph

```mermaid
flowchart TD
    S([START]) -->|first attempt| schema_link[schema_link<br/>LLM: pick tables]
    S -->|returning after a runtime error| fix_sql
    schema_link -->|answerable| generate_sql[generate_sql<br/>LLM: write SQL]
    schema_link -->|not answerable| E([END])
    generate_sql --> validate_sql[validate_sql<br/>parser, role tables, LIMIT, EXPLAIN]
    validate_sql -->|valid| E
    validate_sql -->|rejected, attempts left| fix_sql[fix_sql<br/>LLM: repair with the error]
    validate_sql -->|rejected 3 times| E
    fix_sql --> validate_sql
```

Total budget: 3 SQL attempts, shared between validation failures and runtime failures.

### PO flow subgraph

```mermaid
flowchart TD
    S([START]) --> load_draft[load_draft<br/>read draft from DB]
    load_draft -->|typed message| extract_slots[extract_slots<br/>LLM + catalogue matching]
    load_draft -->|option picked| choose[choose<br/>apply picks, load next question]
    load_draft -->|Confirm| insert_po[insert_po<br/>the only write to company tables]
    load_draft -->|Cancel| cancel[cancel]
    load_draft -->|no open draft| no_draft[no_draft]

    extract_slots --> review_draft[review_draft<br/>defaults, last paid price, what is missing]
    choose --> review_draft
    review_draft -->|something ambiguous| ask_choice[ask_choice<br/>buttons or tick boxes]
    review_draft -->|field missing| ask_next_slot[ask_next_slot]
    review_draft -->|complete| show_confirmation[show_confirmation<br/>PO card]

    ask_choice --> save_draft[save_draft]
    ask_next_slot --> save_draft
    show_confirmation --> save_draft
    save_draft --> E([END])
    insert_po --> E
    cancel --> E
    no_draft --> E
```

### Node reference

| Type | Nodes |
|------|-------|
| **Agent** (subgraph) | `sql_agent`, `po_flow` (the root run is `chat_turn`) |
| **LLM call** | `schema_link`, `generate_sql`, `fix_sql` (strong tier), `write_answer` (strong tier), `extract_slots` (fast tier) |
| **Rules, then LLM only if needed** | `guard_input`, `rewrite_followup`, `route_intent`, `choose_chart`, `reply` |
| **Tool** (database or business-rule code) | `load_canned_sql`, `validate_sql`, `execute_sql`, `reduce_results`, `check_po_permission`, `load_draft`, `review_draft`, `save_draft`, `insert_po`, `cancel`, `save_history` |
| **Code** (pure logic or guardrail) | `preprocess`, `check_answer`, `choose`, `ask_choice`, `ask_next_slot`, `show_confirmation`, `no_draft`, `chat`, `ask_clarify` |

Routers (conditional edges) are not traced, so LangSmith shows only real steps. See [docs/agent-flows.html](docs/agent-flows.html) for every node on every kind of message.

### Sequence diagrams

#### A typed data question, end to end

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Next.js frontend
    participant API as FastAPI
    participant G as LangGraph run
    participant L as LLM provider
    participant CDB as Company DB (read-only)
    participant ADB as assistant schema (write)
    participant LS as LangSmith

    U->>FE: Types a question
    FE->>API: POST /api/chat/stream (session cookie)
    API->>API: Verify cookie, apply rate limit
    API->>ADB: Open or create conversation, store user message
    API->>G: Start graph run (one trace per turn)
    G-->>FE: SSE step "Read your message"
    G->>G: preprocess (clean, mask)
    G->>G: guard_input regex rules
    G->>L: llm.guard (fast tier)
    L-->>G: allowed
    G->>G: rewrite_followup (model only if a follow-up with history)
    G->>G: route_intent rules, then llm.route if rules cannot decide
    G->>L: llm.schema_link (strong tier, role's tables only)
    L-->>G: tables
    G->>L: llm.generate_sql (strong tier)
    L-->>G: SQL

    loop up to 3 attempts in total
        G->>G: validate_sql (parser, role tables, LIMIT 500)
        G->>CDB: EXPLAIN (cost check)
        alt SQL accepted
            G-->>FE: SSE sql
        else rejected
            G->>L: llm.fix_sql (SQL plus exact error)
            L-->>G: corrected SQL
        end
    end

    G->>CDB: execute_sql (read-only, 5 s timeout, 500 rows)
    CDB-->>G: rows
    G-->>FE: SSE rows
    G->>G: reduce_results (top rows and counts only)

    par Chart
        G->>G: choose_chart (hint, then rules, then llm.chart if needed)
        G-->>FE: SSE chart
    and Answer
        G->>L: llm.answer (strong tier, summary only)
        L-->>G: tokens
        G-->>FE: SSE token (streamed)
        G->>G: check_answer (every number must be in the data)
    end

    G->>ADB: save_history (message, SQL, rows, steps, run id)
    G-->>FE: SSE done (message id)
    G-->>LS: Masked trace (rows removed, personal data masked)
    FE-->>U: Table, chart and streamed answer
    U->>FE: Thumbs up or down
    FE->>API: POST /api/feedback
    API->>LS: Score on the turn's run id
```

#### Raising a purchase order across turns

```mermaid
sequenceDiagram
    autonumber
    actor U as Procurement Manager
    participant FE as Next.js frontend
    participant G as LangGraph run
    participant L as LLM provider
    participant ADB as assistant schema (po_drafts)
    participant CDB as Company DB
    participant R as PORepository

    Note over U,R: Turn 1: describe the order
    U->>FE: "Raise a PO for Zenith Steels" plus item lines
    FE->>G: message
    G->>G: preprocess, guard_input (rules and llm.guard)
    G->>G: route_intent rule matches a PO request (no model call)
    G->>G: check_po_permission (PO-create capability)
    G->>ADB: load_draft (none, start a new one)
    G->>L: llm.po_extract (fast tier, one entry per item)
    L-->>G: vendor, items, quantities
    G->>CDB: Match names to active catalogue (rapidfuzz)
    G->>G: review_draft (defaults, last paid price, what is missing)
    alt Something is ambiguous
        G-->>FE: SSE choices (tick boxes for items, Submit)
    else A field is missing
        G-->>FE: SSE tokens (one grouped question)
    end
    G->>ADB: save_draft (draft and queue of open questions)

    Note over U,R: Turn 2: answer
    U->>FE: Picks options or types "10 pcs"
    FE->>G: po_action choose, or short message kept in the PO flow
    G->>G: check_po_permission
    G->>ADB: load_draft
    G->>G: choose (code, no model) or extract_slots (llm.po_extract)
    G->>G: review_draft
    G->>ADB: save_draft
    G-->>FE: Next question, or SSE po_draft (confirmation card)

    Note over U,R: Final turn: confirm
    U->>FE: Presses Confirm
    FE->>G: po_action confirm
    G->>G: check_po_permission (checked again)
    G->>ADB: load_draft
    G->>R: insert_po (fixed parameterised SQL, idempotency key)
    R->>CDB: Insert PO header, lines and payment tranches in one transaction
    CDB-->>R: PO number (PO-YYYY-NNNN)
    G->>ADB: Close draft as confirmed
    G-->>FE: SSE po_created and "Done. PO is raised"
```

## Database Schema

The company data lives in `inv_*` (inventory) and `proc_*` (procurement) tables. The assistant's own tables are in a separate `assistant` schema, created by `make migrate`.

### Company tables

The 15 tables the assistant may read. Solid lines are foreign keys declared in the database; dashed lines are links the database does not enforce (for example `proc_po_lines.inv_item_id` has no foreign key, so the PO flow rechecks the item inside the insert transaction). Only key columns are shown; the full column list with business meanings is in `backend/app/sql/dictionary.py`. `inv_field_definitions` is app configuration and is left out of the assistant's schema.

```mermaid
erDiagram
    proc_vendors ||--o{ proc_purchase_orders : "vendor_id"
    proc_purchase_orders ||--|{ proc_po_lines : "po_id"
    proc_purchase_orders ||--o{ proc_po_payment_tranches : "po_id (not enforced)"
    proc_purchase_orders ||--o{ proc_po_line_regularisations : "po_id"
    proc_po_lines ||--o{ proc_po_line_regularisations : "po_line_id"
    proc_po_lines ||--o{ proc_po_receipts : "po_line_id"
    proc_purchase_orders |o--o{ proc_unexpected_receipts : "resolved_po_id"
    proc_unexpected_receipt_headers ||--o{ proc_unexpected_receipts : "header_id"

    inv_categories ||--o{ inv_sub_categories : "category_id"
    inv_sub_categories ||--o{ inv_sub_categories_2 : "sub_category_id"
    inv_categories |o--o{ inv_items : "category_id"
    inv_sub_categories |o--o{ inv_items : "sub_category_id"
    inv_sub_categories_2 |o--o{ inv_items : "sub_category_2_id"
    inv_items ||--o{ inv_current_stock : "item_id (not enforced)"
    inv_locations ||--o{ inv_current_stock : "location_id"
    inv_items ||--o{ inv_transactions : "item_id (not enforced)"
    inv_locations |o--o{ inv_transactions : "location_id"
    inv_issued_to_targets |o--o{ inv_transactions : "issued_to_id (not enforced)"

    inv_items |o..o{ proc_po_lines : "inv_item_id (not enforced)"
    inv_items ||..o{ proc_unexpected_receipts : "inv_item_id (not enforced)"
    inv_locations |o..o{ proc_purchase_orders : "delivery_location_id (not enforced)"
    inv_locations |o..o{ proc_po_receipts : "location_id (not enforced)"
    inv_transactions |o..o{ proc_po_receipts : "inv_transaction_id (not enforced)"

    proc_vendors {
        varchar id PK
        varchar name
        varchar city
        varchar payment_terms
        boolean is_active
    }
    proc_purchase_orders {
        varchar id PK
        varchar po_number
        varchar vendor_id FK
        varchar status
        date placed_on
        varchar currency
        numeric subtotal
        numeric tax_amount
        numeric total_amount
        varchar payment_terms
        varchar delivery_location_id FK
        json expected_delivery_date
    }
    proc_po_lines {
        varchar id PK
        varchar po_id FK
        varchar inv_item_id FK
        numeric quantity_ordered
        numeric quantity_received
        varchar unit
        numeric unit_price
        numeric tax_percentage
        numeric line_total
        int position
    }
    proc_po_payment_tranches {
        varchar id PK
        varchar po_id FK
        int sequence
        varchar stage
        numeric percentage
        numeric amount
        boolean is_advance
        varchar source
    }
    proc_po_receipts {
        varchar id PK
        varchar po_line_id FK
        numeric quantity
        varchar location_id FK
        varchar inv_transaction_id FK
        timestamp received_at
    }
    proc_po_line_regularisations {
        varchar id PK
        varchar po_id FK
        varchar po_line_id FK
        numeric ordered_qty
        numeric regularised_qty
        numeric qty_variance
        numeric amount_variance
    }
    proc_unexpected_receipt_headers {
        varchar id PK
        varchar vendor_name
        timestamp received_at
    }
    proc_unexpected_receipts {
        varchar id PK
        varchar header_id FK
        varchar inv_item_id FK
        numeric quantity
        varchar resolved_po_id FK
    }

    inv_categories {
        varchar id PK
        varchar name
        varchar short_code
    }
    inv_sub_categories {
        varchar id PK
        varchar name
        varchar category_id FK
    }
    inv_sub_categories_2 {
        varchar id PK
        varchar name
        varchar sub_category_id FK
    }
    inv_items {
        varchar id PK
        varchar item_code
        varchar name
        varchar category_id FK
        varchar sub_category_id FK
        varchar sub_category_2_id FK
        varchar status
        varchar unit
    }
    inv_locations {
        varchar id PK
        varchar name
        boolean is_active
    }
    inv_current_stock {
        varchar id PK
        varchar item_id FK
        varchar location_id FK
        float quantity
        float min_stock_level
        float max_stock_level
    }
    inv_transactions {
        varchar id PK
        varchar item_id FK
        varchar location_id FK
        varchar transaction_type
        float quantity
        float unit_cost
        varchar issued_to_id FK
        timestamp created_at
    }
    inv_issued_to_targets {
        varchar id PK
        varchar name
        boolean is_active
    }
```

### Assistant schema

Chat history and PO drafts, created and written only by the app.

```mermaid
erDiagram
    conversations ||--o{ messages : contains
    conversations ||--o| po_drafts : "has at most one open"

    conversations {
        text id PK
        text user_id
        text title
        timestamptz created_at
        timestamptz updated_at
        bool is_deleted
    }

    messages {
        text id PK
        bigint seq
        text conversation_id FK
        text sender
        text text
        jsonb payload
        text langsmith_run_id
        smallint feedback
        timestamptz created_at
    }

    po_drafts {
        text id PK
        text conversation_id FK
        jsonb draft
        text status
        text idempotency_key
        text created_po_id
        timestamptz updated_at
    }
```

| Company tables the assistant can read (by role) | |
|---|---|
| Procurement | `proc_vendors`, `proc_purchase_orders`, `proc_po_lines`, `proc_po_payment_tranches` (not for the Warehouse Manager), `proc_po_receipts`, `proc_unexpected_receipts`, `proc_unexpected_receipt_headers`, `proc_po_line_regularisations` |
| Inventory | `inv_items`, `inv_categories`, `inv_sub_categories`, `inv_sub_categories_2`, `inv_current_stock`, `inv_locations`, `inv_transactions`, `inv_issued_to_targets` |

## 📐 From Business Requirements to Technical Architecture

### BRD: business requirements

| ID | Requirement |
|----|-------------|
| BR-1 | Staff get answers about purchasing and stock without writing SQL or asking an analyst. |
| BR-2 | Each person sees only what their role is allowed to see. |
| BR-3 | The Procurement Manager can raise a purchase order without opening the ERP screens. |
| BR-4 | Answers must be trustworthy: no invented numbers, and the data behind an answer is visible. |
| BR-5 | The company database must not be damaged or leaked by the assistant. |
| BR-6 | The team can see what the assistant did and why, and measure its quality. |

### PRD: product requirements

| Area | Requirement |
|------|-------------|
| Users | Procurement Manager, Business Owner, Warehouse Manager |
| Interaction | Chat on the left; steps, SQL, table, chart and PO card on the right; suggested questions per role |
| Answers | Streamed, with the SQL and the rows available, plus a chart where it helps |
| POs | Guided conversation, one grouped question for missing fields, confirmation card, one-click Confirm, PO numbers continue the company format `PO-YYYY-NNNN` |
| History | Conversations and open PO drafts survive a reload |
| Feedback | Thumbs up / down on every answer, linked to the trace |
| Out of scope | Editing or deleting company data through chat, NoSQL sources, document (PDF) analysis |

### FRD / SRS: functional requirements

| ID | Functional requirement |
|----|------------------------|
| FR-1 | Authenticate users and put the role in a signed session cookie. |
| FR-2 | Clean input, mask personal data and secrets, reject empty or over-long input (1000 characters). |
| FR-3 | Block prompt injection, destructive requests and raw SQL before any model sees the text. |
| FR-4 | Route each message to a saved query, the SQL agent, the PO flow, small talk or a clarifying question. |
| FR-5 | Generate SQL for the role's tables only, validate it, run it read-only, and repair failures up to 3 times. |
| FR-6 | Choose a chart and write an answer; replace any answer containing numbers that are not in the data. |
| FR-7 | Build a PO draft over several turns, store it, show a card, and insert it once on Confirm. |
| FR-8 | Stream steps, SQL, rows, chart, tokens and PO events to the browser. |
| FR-9 | Store history and PO drafts; restore them on reload. |

### HLD: high-level design

- One **FastAPI** service exposes REST endpoints plus a streaming chat endpoint (server-sent events).
- One **LangGraph** graph per message does all orchestration. Its nodes call small, single-purpose model tasks, or plain code.
- The **LLM** is behind a port (`structured`, `text`, `stream`) with OpenAI and Anthropic adapters, a fast tier and a strong tier.
- **PostgreSQL** holds the company data (read through a read-only engine) and the `assistant` schema (written through a separate write engine).
- **Next.js** renders the split screen and consumes the event stream.
- **LangSmith** receives one masked trace per turn.

### LLD: low-level design

| Concern | Where | Notes |
|---------|-------|-------|
| Graph state | `backend/app/agents/state.py` | One typed state shared by the main graph and both subgraphs |
| Main graph and nodes | `backend/app/agents/graph.py`, `nodes/main.py` | Routing functions are untraced wrappers (`agents/untraced.py`) |
| SQL agent | `backend/app/agents/sql_agent/` | Nodes, hints (value hints, examples), prompts |
| PO flow | `backend/app/agents/po_flow/`, `backend/app/po/` | Slots, resolver, rules, totals, repository |
| Routing | `backend/app/agents/routing/` | Rules first, model second |
| Guardrails | `backend/app/guardrails/` | Pre-processing, injection rules and classifier, masking, answer check |
| SQL safety | `backend/app/sql/` | Validator (sqlglot), EXPLAIN check, read-only executor, saved queries per role |
| RBAC | `backend/app/rbac/` | Capabilities, role-scoped schema, table scope |
| LLM adapters | `backend/app/llm/` | Port, OpenAI, Anthropic, scripted fake for tests, offline heuristic |
| History | `backend/app/history/` | Conversations, messages, PO drafts |
| Tracing | `backend/app/observability/` | Masking, run config, agent/tool/LLM labelling |
| API | `backend/app/api/` | Routes, SSE schema, rate limiter, error handling |

### ADR: architecture decision records

| # | Decision | Why |
|---|----------|-----|
| ADR-1 | LangGraph for orchestration | Explicit nodes, conditional edges, retries, parallel branches and subgraphs; every step is traceable. |
| ADR-2 | Rules before models in the guard, router, rewriter and chart picker | Faster, cheaper and not talk-roundable; the model handles only what rules cannot. |
| ADR-3 | Two model tiers | A small model for guard, routing and extraction; a stronger one for SQL and answers. |
| ADR-4 | The LLM sits behind a port | Switch provider with one setting; tests use a scripted fake; nodes never import a vendor SDK (enforced by an architecture test). |
| ADR-5 | Validate AI-written SQL with a parser, then EXPLAIN, then run read-only | The model proposes, code decides. No single layer is trusted. |
| ADR-6 | Writes only through fixed, parameterised code | POs, history and data cleaning never use model-written SQL. |
| ADR-7 | The PO flow is a state machine over a database-backed draft | Several turns, resumable after a reload, nothing dropped (questions are queued). |
| ADR-8 | Users and permissions defined in code | Small fixed set of roles; easy to test with 100% branch coverage. |
| ADR-9 | Separate `assistant` schema in the company database | App tables are kept apart from company data. |
| ADR-10 | Company data cleaned in place with numbered scripts, backups and rollbacks | No new tables or views; every change is reversible. |
| ADR-11 | Server-sent events for streaming | One-way stream of steps, SQL, rows, chart and tokens; simple and proxy-friendly. |
| ADR-12 | Mask before upload to LangSmith, drop result rows | Traces are useful without exposing business data. |

## 🧭 C4 Model

### C1: system context

```mermaid
flowchart LR
    PM["Procurement Manager<br/>(person)"]
    BO["Business Owner<br/>(person)"]
    WM["Warehouse Manager<br/>(person)"]
    PA["Procurement Assistant<br/>(this system)"]
    DB[("Company PostgreSQL<br/>inv_* and proc_* tables")]
    LLM["LLM provider<br/>OpenAI or Anthropic"]
    LS["LangSmith<br/>tracing and feedback"]

    PM -->|ask questions, raise POs| PA
    BO -->|ask questions| PA
    WM -->|ask questions| PA
    PA -->|read-only SQL, fixed PO inserts| DB
    PA -->|masked prompts| LLM
    PA -->|masked traces| LS
```

### C2: containers

```mermaid
flowchart TB
    User["User's browser"]

    subgraph App["Procurement Assistant"]
        FE["Frontend<br/>Next.js, React, Zustand, Recharts"]
        API["Backend API<br/>FastAPI, server-sent events"]
        AG["Agent runtime<br/>LangGraph graph and subgraphs"]
        LLMGW["LLM port<br/>OpenAI and Anthropic adapters"]
    end

    DBR[("Company tables<br/>read-only engine")]
    DBW[("assistant schema<br/>history and PO drafts, write engine")]
    LLMX["LLM provider API"]
    LSX["LangSmith"]

    User --> FE
    FE -->|REST and SSE| API
    API --> AG
    AG --> LLMGW
    LLMGW --> LLMX
    AG -->|AI-written SQL, validated| DBR
    AG -->|fixed statements| DBW
    AG -.->|masked traces| LSX
```

## 🧠 AI Application Reference Architecture

```mermaid
flowchart TB
    subgraph L1["API gateway and application layer"]
        A1["FastAPI routes, signed session cookie, rate limits, SSE"]
    end
    subgraph L2["AI orchestration and model gateway"]
        A2["LangGraph main graph and subgraphs"]
        A3["LLM port: provider switch, fast and strong tiers, retries, refusal fallback"]
    end
    subgraph L3["Retrieval and data services"]
        A4["Role-scoped schema, value hints, saved-query examples"]
        A5["Catalogue matching: rapidfuzz over vendors, items, locations"]
    end
    subgraph L4["Memory and state"]
        A6["Conversation history, last turns for follow-ups"]
        A7["PO draft in the database, queue of open questions"]
    end
    subgraph L5["Tools and business systems"]
        A8["Read-only SQL executor"]
        A9["PO repository: fixed, parameterised, idempotent insert"]
    end
    subgraph L6["Guardrails and observability"]
        A10["Input cleaning, injection rules, SQL validator, answer check, RBAC"]
        A11["LangSmith traces: masked, labelled agent / tool / LLM"]
    end
    L1 --> L2 --> L3
    L2 --> L4
    L2 --> L5
    L6 -.-> L1
    L6 -.-> L2
    L6 -.-> L5
```

| Layer | In this project |
|-------|-----------------|
| API gateway and application | FastAPI app, auth cookie, per-user rate limit (20 per minute, 300 per day), SSE stream |
| AI orchestration and model gateway | LangGraph; `LLM` port with OpenAI and Anthropic adapters; strong-tier calls on Anthropic use server-side refusal fallback |
| Retrieval services | No vector database. Retrieval is structured: role-filtered schema, real value hints from the catalogue, examples from saved queries, fuzzy catalogue matching |
| Memory and state | `assistant.conversations`, `messages`, `po_drafts`; the last three turns feed follow-up rewriting |
| Tool integration and business systems | Read-only executor on company tables; `PORepository` is the single write path |
| Guardrails | Pre-processing and masking, injection rules plus classifier, role-scoped schema, SQL parser, EXPLAIN, answer-number check, permission re-check on Confirm |
| Observability | One LangSmith trace per turn grouped by conversation, thumbs up / down attached to the trace |

## 🔌 API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login` | Sign in, sets the session cookie |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/logout` | Sign out |
| GET | `/api/canned` | Suggested questions for the caller's role |
| POST | `/api/chat/stream` | One turn as a stream of events: `message`, `button_id` or `po_action` |
| GET | `/api/conversations` | History list |
| GET | `/api/conversations/{id}` | One conversation with messages and open PO draft |
| DELETE | `/api/conversations/{id}` | Delete a conversation |
| POST | `/api/feedback` | Thumbs up / down on a message |
| GET | `/api/health` | Liveness |

Stream events: `conversation`, `step`, `sql`, `rows`, `chart`, `token`, `answer_replace`, `choices`, `po_draft`, `po_created`, `error`, `done`. Full contract: [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## 🔐 Security

- AI-written SQL runs only in read-only sessions with a 5-second timeout and a 500-row cap, after a parser check: one SELECT, the role's tables only, allowlisted functions, no comments, no `SELECT *`, no bind parameters, then an `EXPLAIN` dry run.
- Writes (POs, history, data cleaning) use fixed, parameterised statements. The model never writes SQL for them.
- Prompt-injection rules plus a classifier, database values fenced as data, and roles taken only from the signed session cookie.
- Secrets never leave the app. Personal data is masked in prompts, traces and logs. Result rows never reach LangSmith.
- Accepted for the demo: the app uses one database login. Two limited database accounts would be the first change for real use.

## 🔭 Observability

Set `LANGSMITH_API_KEY` and keep `LANGSMITH_TRACING=true`. Each chat turn becomes one trace named `chat_turn`:

- `sql_agent` and `po_flow` appear once, with their steps nested directly under them.
- Every run is labelled as an agent, a tool, an LLM call or a node (by tag and metadata); tools use the tool run type.
- Routing functions are not traced.
- Inputs and outputs are masked before upload; users appear as a role and a hash.
- Thumbs up and down attach a `user_score` to the turn's trace.

## 🧪 Tests

| Command | What runs |
|---------|-----------|
| `make test` | Backend: unit, integration, API, graph, security corpora and architecture rules, with coverage gates |
| `make test-frontend` | Vitest and React Testing Library, 80% coverage gate |
| `make test-smoke` | Read-only checks of every saved question against the real company database |
| `make eval-deepeval` | Per-role AI quality eval with the real model: result match, answer correctness, faithfulness, relevancy and refusals |
| `make lint` | Ruff and type checks for the backend, ESLint and TypeScript for the frontend |

The default suites never call a model provider or touch the company database: they use a scripted fake model and a seeded local Postgres that reproduces the real data's quirks.

## 🧹 Company data changes

Data was cleaned in place (units, payment terms, item names, empty date lists), with a backup and rollback script for each change. See [DATA_CHANGES.md](DATA_CHANGES.md) and `db/changes/`.

```bash
make normalise-preview                 # what would change, writes nothing
make normalise-apply                   # apply, with backups and a log entry
make normalise-rollback CHANGE=001     # restore one change
```

## 📁 Layout

```
backend/   FastAPI app (app/), tests/, evals/, scripts/ (data cleaning, eval seed)
frontend/  Next.js app: app/, components/, lib/, stores/, hooks/
db/        Data-cleaning change records and backups
docs/      API contract, manual test scenarios, interactive agent-flow explorer
```

## 🤝 Contributing

1. Create a feature branch.
2. Write a failing test first, then the code. Backend tests live in `backend/tests/`, frontend tests sit next to their components.
3. Run `make lint` and `make test-all` before opening a pull request.
4. Keep commits to meaningful milestones.

### Ideas for next steps

- Two limited database accounts (read-only for AI, narrow write for POs).
- Retrieval over documents (PDF, text) with a vector store.
- A settings page for profile and provider choice.
- Multi-source analysis across the company database and uploaded files.
