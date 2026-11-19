# Phase 1 Test Plan

Companion to `PLAN.md`. Every behaviour in the plan has a test listed here, and every test is written **before** the code it covers.

## 1. TDD rules

1. **Red, green, refactor.** Write one failing test, write the least code that passes it, then clean up with all tests green.
2. **No production code without a failing test first.** That includes prompts, SQL for buttons, normalisation scripts and frontend components.
3. **Commit history shows it.** The repo is a git repository from day one. Each behaviour lands as a `test:` commit with the failing test, then a `feat:` or `fix:` commit that makes it pass.
4. **Bugs start as tests.** Any bug found later gets a regression test that reproduces it before the fix.
5. **A build step is done only when** its tests are written, they failed first, they now pass, coverage gates hold, and lint and type checks pass.
6. **Tests are deterministic.** No real OpenAI calls, no real clock and no real company DB in the default suite.

## 2. Test layers

| Layer | Marker | Runs against | When it runs |
|---|---|---|---|
| Unit | `unit` | Pure code, fake LLM, no DB | Every save and commit |
| Integration | `integration` | Local Docker Postgres with seed data | Every commit |
| API | `api` | FastAPI test client, test DB, fake LLM | Every commit |
| Graph | `graph` | Full LangGraph run, fake LLM, test DB | Every commit |
| Security | `security` | Attack corpora against validator, guardrails, API | Every commit |
| Architecture | `arch` | Import rules between packages | Every commit |
| Frontend | Vitest | Components, hooks, SSE reader, with mocked API (MSW) | Every commit |
| End-to-end | Playwright | Next.js + FastAPI + test DB + fake LLM | Every commit, in CI |
| Smoke | `smoke` | Real company DB, read-only | On demand, before a demo |
| Evals | `eval` | Real OpenAI, LangSmith | On demand, before merging prompt changes |

`pytest` runs unit, integration, api, graph, security and arch by default. `smoke` and `eval` need an explicit flag.

## 3. Test infrastructure (built first, test-first)

| Piece | Purpose |
|---|---|
| Test Postgres in Docker Compose | Company schema copied structure-only, plus the `assistant` schema from migrations |
| Seed factory | Generated data that includes every real quirk: mixed unit spellings, misspelled payment terms, empty and NULL date lists, items without stock rows, items without category, USD orders, a duplicate item name, staff UUIDs |
| Reseed fixtures | Read-only tests share one seeded state. Tests that write get a fresh seed before and after, so tests never affect each other *(build note: simpler and faster than per-test transactions here)* |
| Fake LLM | A chat model that returns scripted responses per node and records the prompts it received, so tests can assert on prompts too |
| Frozen clock | Fixture that fixes "today" so date logic is testable |
| Fake LangSmith client | Records traces and feedback, so masking and metadata can be asserted |
| `FAKE_LLM=1` app mode | Lets Playwright drive the real app without OpenAI |

## 4. Coverage gates

| Area | Gate |
|---|---|
| Backend overall | 90% lines |
| RBAC policy, SQL validator, masker, PO numbering, PO totals, normalisation runner | **100% branches** |
| Frontend overall | 80% lines |
| SSE reader, PO card, login form | 100% branches |

The build fails if a gate is missed.

## 5. Backend test catalogue

### 5.1 Auth (`tests/unit/auth`, `tests/api/auth`)

| ID | Test |
|---|---|
| AUTH-01 | Exactly three users exist with the planned emails, names and roles |
| AUTH-02 | Each user has a fixed, unique UUID |
| AUTH-03 | The users module holds a bcrypt hash, not the plain password, and the hash verifies `1234567890` |
| AUTH-04 | Login succeeds for each user and returns name and role |
| AUTH-05 | Login sets a cookie that is httpOnly, SameSite=Lax, Path=/, and Secure outside local dev |
| AUTH-06 | Wrong password returns 401 with a generic message |
| AUTH-07 | Unknown email returns the same 401 message, so emails can't be discovered |
| AUTH-08 | Email is matched case-insensitively and trimmed |
| AUTH-09 | Malformed login body returns 422 |
| AUTH-10 | JWT holds user id, role, name and an expiry 8 hours out |
| AUTH-11 | Expired token returns 401 (frozen clock) |
| AUTH-12 | Tampered signature returns 401 |
| AUTH-13 | Token signed with `alg: none` or a different secret returns 401 |
| AUTH-14 | `/auth/me` returns name and role, and 401 without a cookie |
| AUTH-15 | Logout clears the cookie |
| AUTH-16 | The 11th login attempt in a minute from one IP returns 429 |

### 5.2 RBAC (`tests/unit/rbac`, `tests/api/rbac`)

| ID | Test |
|---|---|
| RBAC-01 | Capability matrix: every role and capability pair returns the planned yes or no (15 cases) |
| RBAC-02 | Only the Procurement Manager has `po.create` |
| RBAC-03 | Warehouse Manager can't access `proc_po_payment_tranches` |
| RBAC-04 | No role can access `inv_field_definitions` or anything in `assistant` |
| RBAC-05 | Schema filter returns only the role's tables and their dictionary entries |
| RBAC-06 | Every table in the policy exists in the data dictionary and the test DB schema |
| RBAC-07 | Every route except login and health returns 401 without a session |
| RBAC-08 | Business Owner and Warehouse Manager get 403 on every PO endpoint |
| RBAC-09 | Each button runs only for its listed roles. Other roles get 403 |
| RBAC-10 | A role claimed in the message body or chat text is ignored. Only the JWT counts |

### 5.3 Data normalisation (`tests/integration/normalisation`)

Run for each change, 001 to 007:

| ID | Test |
|---|---|
| NORM-01 | Dry run reports the expected row count and changes nothing |
| NORM-02 | Backup file holds the primary key and old value of every row to be changed, written before applying |
| NORM-03 | Apply changes exactly the expected rows to the expected values |
| NORM-04 | Verify script passes after apply |
| NORM-05 | Running apply a second time changes zero rows |
| NORM-06 | Rollback restores every row exactly as it was |
| NORM-07 | A failing verify rolls back the whole change |
| NORM-08 | A change-log entry is written with date, change number, tables, reason, rows and rollback command |
| NORM-09 | The runner defaults to dry run and refuses to apply to the real DB without an explicit confirm flag |

Specific to the mappings:

| ID | Test |
|---|---|
| NORM-10 | Every unit spelling maps to the planned canonical unit (parametrised) |
| NORM-11 | Every payment-term spelling maps to the planned canonical term (parametrised) |
| NORM-12 | Terms marked "unchanged" stay unchanged |
| NORM-13 | An unknown spelling is left alone and reported |
| NORM-14 | Item names lose leading, trailing and repeated spaces only |
| NORM-15 | NULL date lists become `[]`, non-empty lists are untouched |
| NORM-16 | The existing unique index on `po_number` rejects a duplicate *(build note: no change needed, the index already exists)* |

### 5.4 SQL validator (`tests/unit/sql`, `tests/security/sql`)

Must accept:

| ID | Test |
|---|---|
| SQLV-01 | Simple select with filter and order |
| SQLV-02 | Joins across allowed tables |
| SQLV-03 | CTEs (`WITH`) |
| SQLV-04 | Aggregates and `GROUP BY` |
| SQLV-05 | Allowlisted date, string, numeric and JSON functions, `COALESCE`, `NULLIF`, `CASE` |
| SQLV-06 | Schema-qualified `public.` table names that the role is allowed |
| SQLV-07 | Words like "drop" or "delete" inside string literals |

Must reject, each with a clear error text:

| ID | Test |
|---|---|
| SQLV-10 | INSERT, UPDATE, DELETE, MERGE, TRUNCATE |
| SQLV-11 | DROP, ALTER, CREATE, GRANT, REVOKE, COMMENT |
| SQLV-12 | Two statements, such as `select 1; drop table x` |
| SQLV-13 | Line and block comments |
| SQLV-14 | `pg_sleep`, `pg_read_file`, `lo_import`, `dblink`, `set_config`, `current_setting`, `pg_terminate_backend` |
| SQLV-15 | Any function not on the allowlist |
| SQLV-16 | COPY, CALL, DO, LOCK, VACUUM, PREPARE, EXECUTE, SET, `SELECT INTO` |
| SQLV-17 | `FOR UPDATE` and `FOR SHARE` |
| SQLV-18 | `pg_catalog` and `information_schema` |
| SQLV-19 | Any table in the `assistant` schema |
| SQLV-20 | A table outside the role's scope, directly, in a join, a subquery, a CTE or a UNION |
| SQLV-21 | Case and quoting tricks, such as `"PROC_PO_PAYMENT_TRANCHES"` for the Warehouse Manager |
| SQLV-22 | `SELECT *` |
| SQLV-23 | Empty input, non-SQL text, and queries over 10,000 characters |

Limits and database checks:

| ID | Test |
|---|---|
| SQLV-30 | A missing `LIMIT` is added |
| SQLV-31 | A `LIMIT` above 500 is lowered to 500 |
| SQLV-32 | `EXPLAIN` on the test DB turns an unknown column into an error naming that column (integration) |
| SQLV-33 | A plan above the cost threshold is rejected with a "narrow the query" error (integration) |
| SQLV-34 | Checks run in the documented order and report the first failure |

### 5.5 Database sessions (`tests/integration/db`, `tests/arch`)

| ID | Test |
|---|---|
| DB-01 | The read session refuses an INSERT |
| DB-02 | The read session cancels a query after 5 seconds |
| DB-03 | Results above 500 rows are cut to 500 and flagged as truncated |
| DB-04 | Connection settings require SSL |
| DB-05 | The write session commits in the PO and history modules |
| DB-06 | Architecture: the agent, SQL and graph packages never import the write session |
| DB-07 | Architecture: the PO module never imports the SQL generator |

### 5.6 Guardrails and masking (`tests/unit/guardrails`, `tests/security/prompts`)

| ID | Test |
|---|---|
| GRD-01 | Empty input and input over 1,000 characters return 422 |
| GRD-02 | Control characters are removed and unicode is normalised |
| GRD-03 | Prompt-injection corpus of about 30 samples is blocked: "ignore previous instructions", system-prompt requests, role escalation, jailbreak role-play, base64-wrapped instructions, raw SQL, HTML and markdown injection |
| GRD-04 | Benign corpus of about 30 real questions passes, including ones with "drop", "delete" or "update" in normal use |
| GRD-05 | Off-topic requests are routed to a short chat reply |
| GRD-06 | Secrets typed into chat are flagged and masked before anything else sees them |
| GRD-07 | Free text from DB rows reaches the LLM truncated and wrapped as quoted data |
| MASK-01 | Each detector masks its pattern: emails, Indian and international phone numbers, UUIDs, connection strings, API keys, JWTs, GSTIN, PAN (parametrised) |
| MASK-02 | No false positives on PO numbers, item codes, amounts, dates or HSN codes |
| MASK-03 | Address fields are masked by column name |
| MASK-04 | Masking twice gives the same result as masking once |
| MASK-05 | The same staff UUID always gets the same label, and demo users get their names |
| OUT-01 | Invalid LLM JSON is retried once, then fails safely |
| OUT-02 | Answer number check passes matching numbers, allows rounding and percentages, and flags invented numbers |
| OUT-03 | A flagged answer is replaced with the template answer |
| OUT-04 | Errors shown to users carry a reference id and no database or stack-trace details |

### 5.7 Follow-up rewriter and router (`tests/unit/agents`)

| ID | Test |
|---|---|
| RTR-01 | A standalone question skips the rewriter with no LLM call |
| RTR-02 | A follow-up is rewritten using only the last 3 turns, checked through the recorded prompt |
| RTR-03 | A button payload routes to the button query with no LLM call |
| RTR-04 | An open PO draft routes the message to the PO subgraph |
| RTR-05 | "Cancel" or a clearly different question while a draft is open leaves the PO flow |
| RTR-06 | Each intent label from the classifier maps to the right branch (parametrised) |
| RTR-07 | Low confidence leads to a clarifying question |
| RTR-08 | Invalid classifier output is retried once, then becomes a clarifying question |

### 5.8 Button queries (`tests/integration/canned`, `tests/smoke`)

For each of the 20 buttons:

| ID | Test |
|---|---|
| CAN-01 | Runs on the seed and returns the expected columns |
| CAN-02 | Returns the expected rows for the seed (golden file) |
| CAN-03 | Passes the SQL validator as a safety net |
| CAN-04 | Finishes in under 500 ms on the seed |
| CAN-05 | Is listed only for its planned roles |

Shared behaviour:

| ID | Test |
|---|---|
| CAN-10 | An empty date-filtered result reports the latest date that has data (frozen clock) |
| CAN-11 | USD amounts are converted with the configured rate, and the answer says so |
| CAN-12 | Items without a category show as "Uncategorised" |
| CAN-13 | Lines with a unit mismatch are flagged in quantity comparisons |
| SMOKE-01 | Every button runs read-only on the real DB and returns the expected columns |
| SMOKE-02 | Every table in the data dictionary exists on the real DB with the documented columns |

### 5.9 PO domain logic (`tests/unit/po`)

| ID | Test |
|---|---|
| PO-01 | Line subtotal, tax and total are correct, using Decimal with 2-place rounding |
| PO-02 | Header totals equal the sum of the lines |
| PO-03 | Defaults: status placed, currency INR, placed_on today, tax 0, unit from the item, terms from the vendor |
| PO-04 | Payment terms become required when the vendor has none |
| PO-05 | Quantity or price of zero or less is rejected |
| PO-06 | Inactive vendors and items are rejected |
| PO-07 | A unit different from the item's unit is allowed with a warning |
| PO-08 | Tranches built from each canonical term have the right percentages (summing to 100), due basis, offset days, advance and dispatch flags (parametrised) |
| PO-09 | Slot extraction fills `PODraft` from the fake LLM's output |
| PO-10 | Plain-language edits work: change price, add a line, remove a line, change quantity |
| PO-11 | Entity resolution: exact item code match, fuzzy name match, several matches lead to a choice, no match leads to a question |
| PO-12 | Last-price suggestion prefers the same vendor and currency |
| PO-13 | Missing details are asked one at a time, in a fixed order |

### 5.10 PO repository (`tests/integration/po`)

| ID | Test |
|---|---|
| POR-01 | Next number is the highest number for the year plus one |
| POR-02 | The first PO of a new year is `-0001` (frozen clock) |
| POR-03 | Numbers in other formats are ignored when finding the highest |
| POR-04 | Two inserts at the same time get different numbers (threads) |
| POR-05 | A number clash retries once and succeeds. A second clash fails cleanly |
| POR-06 | Header, lines and tranches are written with the exact expected values |
| POR-07 | `custom_fields` holds the assistant marker and `created_by` holds the PM's UUID |
| POR-08 | A failure partway through leaves nothing written |
| POR-09 | The same idempotency key twice creates one PO and returns the same number |
| POR-10 | An item that disappears before confirm makes the insert fail cleanly |

### 5.11 Chat history (`tests/integration/history`)

| ID | Test |
|---|---|
| HIS-01 | A conversation gets its title from the first question |
| HIS-02 | Messages round-trip with their payload |
| HIS-03 | A user can't read, list or delete another user's conversation (404) |
| HIS-04 | Soft-deleted conversations are hidden |
| HIS-05 | Drafts round-trip, and status only moves from open to confirmed or cancelled |
| HIS-06 | Migrations create objects only in `assistant`, including Alembic's version table |
| HIS-07 | Migrations downgrade cleanly |

### 5.12 Result reducer and charts (`tests/unit/viz`)

| ID | Test |
|---|---|
| VIZ-01 | Reducer gives row count, totals, min and max, and the top 20 rows |
| VIZ-02 | Long text is truncated and quoted, and staff IDs are replaced by labels |
| VIZ-03 | Chart rules (parametrised): date plus number gives line, 6 or fewer shares give pie, categories plus number give bar, more than 12 categories give horizontal bar, two numbers give scatter, a single value or empty result gives a table only |
| VIZ-04 | The chart decider calls the LLM only when the rules can't decide |
| VIZ-05 | Chart specs contain exactly the values in the rows, nothing invented |

### 5.13 Graph runs (`tests/graph`)

| ID | Test |
|---|---|
| GRAPH-01 | Button path runs end to end and saves history once |
| GRAPH-02 | Data-question path runs end to end |
| GRAPH-03 | Bad SQL followed by good SQL takes 2 attempts and succeeds |
| GRAPH-04 | Three bad attempts end with the "couldn't answer" reply |
| GRAPH-05 | A runtime error on AI-written SQL goes back to the fix step |
| GRAPH-06 | A runtime error on a button query goes straight to the error reply |
| GRAPH-07 | Blocked, denied, chit-chat and clarify paths each reply and save history |
| GRAPH-08 | Chart and answer both finish before history is saved, and it's saved once |
| GRAPH-09 | A three-turn PO conversation ends with a created PO in the test DB |
| GRAPH-10 | A Warehouse Manager asking for a PO gets the denied reply and no draft is created |

### 5.14 Streaming API (`tests/api/stream`)

| ID | Test |
|---|---|
| SSE-01 | Every event matches its Pydantic schema |
| SSE-02 | Event order for a data question: steps, sql, rows, then chart and tokens, then done |
| SSE-03 | Tokens come only from the answer and reply nodes |
| SSE-04 | An exception sends an `error` event with a reference id and closes the stream |
| SSE-05 | A client disconnect cancels the graph run |
| SSE-06 | 21 requests in a minute from one user returns 429 on the last |

### 5.15 Observability (`tests/unit/observability`)

| ID | Test |
|---|---|
| OBS-01 | Tracing is off without an API key and the app still works |
| OBS-02 | With a key, traces carry role, intent, hashed user id, retries and row count |
| OBS-03 | Trace inputs and outputs are masked and contain no result rows |
| OBS-04 | No raw email or user id appears anywhere in trace data |
| OBS-05 | The conversation id is sent as the thread id |
| OBS-06 | Thumbs up or down sends feedback against the right run id |
| OBS-07 | Tracing is forced off during the test suite |

## 6. Frontend test catalogue (Vitest, React Testing Library, MSW)

| ID | Test |
|---|---|
| FE-01 | Login page shows three quick-login buttons, and each fills its email and password |
| FE-02 | Submitting calls the login API and moves to `/chat` |
| FE-03 | A 401 shows a clear error message |
| FE-04 | Middleware sends visitors without a session to `/login` and lets others through |
| FE-05 | Header shows "Hey {name}, {Role} welcome" for each role (parametrised) |
| FE-06 | Logout calls the API and returns to `/login` |
| FE-07 | Each role sees exactly its own buttons (parametrised) |
| FE-08 | SSE reader parses events, including events split across chunks and several events in one chunk |
| FE-09 | Tokens append to the answer as they arrive |
| FE-10 | Step tracker ticks as step events arrive |
| FE-11 | SQL panel shows highlighted SQL |
| FE-12 | Data table renders rows and flags truncated results |
| FE-13 | Each chart type renders from its spec |
| FE-14 | `answer_replace` swaps the answer text |
| FE-15 | An error event shows a message and re-enables input |
| FE-16 | PO card shows lines and totals |
| FE-17 | Confirm sends an idempotency key, and a double click sends one request |
| FE-18 | Edit and Cancel send the right actions |
| FE-19 | History list loads, switching conversations loads their messages, and delete removes one |
| FE-20 | Thumbs up or down calls the feedback API |
| FE-21 | Login and chat pages pass automated accessibility checks (axe) |

## 7. End-to-end scenarios (Playwright, `FAKE_LLM=1`, test DB)

| ID | Scenario |
|---|---|
| E2E-01 | Each role logs in with the quick button and sees the right greeting and buttons |
| E2E-02 | Clicking a button shows steps, a table and a chart on the right, and a summary on the left |
| E2E-03 | A typed question streams an answer word by word |
| E2E-04 | The Procurement Manager raises a PO over several turns, confirms, sees the new number, and the PO exists in the test DB |
| E2E-05 | The Warehouse Manager asks to raise a PO and is refused |
| E2E-06 | A refreshed page restores the conversation and an open PO draft |
| E2E-07 | Logout returns to login, and `/chat` is no longer reachable |

## 8. AI quality evals (LangSmith, on demand)

| ID | Eval | Pass mark |
|---|---|---|
| EVAL-01 | About 30 questions with reference SQL, scored by comparing result sets on the test DB | 85% or more correct |
| EVAL-02 | Router dataset of about 40 labelled messages | 95% or more correct |
| EVAL-03 | PO slot extraction on about 20 order messages | 90% or more fields correct |
| EVAL-04 | Prompt-injection corpus against the real guard model | 100% blocked |

A prompt change is merged only if no eval drops below its pass mark.

## 9. Order of work

Tests for each step are written first, following the build order in `PLAN.md` section 15:

| Step | Tests |
|---|---|
| 0 | Test infrastructure (section 3) |
| 1 | AUTH |
| 2 | RBAC |
| 3 | NORM |
| 4 | SQLV |
| 5 | DB |
| 6 | GRD, MASK, OUT |
| 7 | RTR |
| 8 | CAN |
| 9 | PO |
| 10 | POR |
| 11 | HIS |
| 12 | VIZ |
| 13 | GRAPH, SSE |
| 14 | OBS |
| 15 | FE, E2E |
| Before demo | SMOKE, EVAL |

## 10. Commands

```
make test            # unit, integration, api, graph, security, arch, with coverage gates
make test-frontend   # Vitest with coverage gates
make test-e2e        # Playwright against the Docker stack with FAKE_LLM=1
make test-smoke      # read-only checks on the real company DB
make eval            # LangSmith evals with the real model
make test-all        # everything except smoke and eval
```

A CI workflow runs `make test-all` on every push once the repo is hosted.
