# Procurement Assistant

A chat assistant over a manufacturer's purchasing and inventory database. People sign in as one of three roles, ask questions in plain English or click suggested questions, and get answers with tables and charts streamed into a split screen. The Procurement Manager can also raise real purchase orders by describing them in chat.

Built with FastAPI, LangGraph, OpenAI or Anthropic (switchable), and Next.js, test-first. Plan: [PLAN.md](PLAN.md). Every test: [TEST_PLAN.md](TEST_PLAN.md). API: [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## Roles

| Demo login (password `1234567890`) | Role | Can do |
|---|---|---|
| procurement@demo.local, Arjun Rao | Procurement Manager | Ask about purchasing and stock, 7 suggested questions, **raise POs** |
| owner@demo.local, Meera Iyer | Business Owner | Ask about everything, 6 questions on spend and vendor performance |
| warehouse@demo.local, Kabir Shah | Warehouse Manager | Ask about stock and deliveries, 7 questions, no payment schedules |

Users and permissions live in code (`backend/app/auth`, `backend/app/rbac`) and are enforced on the server for every request.

## How a message is handled

```
message -> pre-process -> guardrails -> rewrite follow-up -> route
   button      -> saved query ------------------------------\
   question    -> SQL agent (link tables, write SQL,         -> run read-only -> reduce
                  validate + EXPLAIN, fix up to 3 times) ---/       -> chart + answer (parallel)
   PO request  -> role check -> PO flow (extract, match, ask, confirm, insert)
   small talk  -> reply
every path -> save to history
```

The graph is in `backend/app/agents`. Each node streams events (steps, SQL, rows, chart, tokens, PO card) to the browser.

## Getting started

Needs Docker, [uv](https://docs.astral.sh/uv/) and Node 24.

```bash
cp .env.example .env          # set DATABASE_URL; add OPENAI_API_KEY and LANGSMITH_API_KEY when you have them
make install                  # backend, frontend and e2e dependencies
make testdb                   # local Postgres for tests (port 55432)
make migrate                  # creates the `assistant` schema in the company DB (once)
make dev-backend              # http://localhost:8000/api/docs
make dev-frontend             # http://localhost:3000
```

Or run everything in containers with `make up` (http://localhost:3000).

### Choosing the AI provider

Set `LLM_PROVIDER` in `.env` and restart the backend (`docker compose up -d --force-recreate backend`, or restart `make dev-backend`):

| `LLM_PROVIDER` | Key | Fast tier (guardrails, routing, PO details) | Strong tier (SQL, answers) |
|---|---|---|---|
| `openai` (default) | `OPENAI_API_KEY` | `OPENAI_MODEL_FAST`, default `gpt-4o-mini` | `OPENAI_MODEL_SQL`, default `gpt-4o` |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL_FAST`, default `claude-haiku-5-5` | `ANTHROPIC_MODEL_STRONG`, default `claude-opus-5-5` |

On Anthropic, strong-tier calls use server-side refusal fallbacks: if Claude declines a request on policy grounds, the API retries it on a fallback model within the same call.

Without the selected provider's key the app uses an offline rule-based stand-in (`FAKE_LLM`), so it still runs end to end for demos and tests. The backend log warns when that happens.

## Tests

| Command | What runs |
|---|---|
| `make test` | Backend: unit, integration, API, graph, security corpora, architecture rules. Fails under 90% coverage, or under 100% branches for RBAC, the SQL validator, masking, PO numbering and totals, and the data-cleaning runner |
| `make test-frontend` | Vitest and React Testing Library, 80% coverage gate |
| `make test-e2e` | Playwright: login, buttons, streamed answers, a full PO, role refusal, refresh, logout |
| `make test-smoke` | Read-only checks of every button against the real company DB |
| `make eval` | AI quality evals with the real model: SQL accuracy, routing, PO extraction, injection |

The default suites never call OpenAI or touch the company database: they use a scripted fake model and a seeded local Postgres that reproduces the real data's quirks.

## Company data changes

Data was cleaned in place (units, payment terms, item names, empty date lists): 112 rows, each change backed up with a rollback script. See [DATA_CHANGES.md](DATA_CHANGES.md) and `db/changes/`.

```bash
make normalise-preview                 # what would change, writes nothing
make normalise-apply                   # apply, with backups and a log entry
make normalise-rollback CHANGE=001     # restore one change
```

The app's own tables (chat history, PO drafts) live in a separate `assistant` schema.

## Security

- AI-written SQL runs only in read-only sessions with a 5-second timeout and a 500-row cap, after a parser-based check: one SELECT, the role's tables only, allowlisted functions, no comments, no bind parameters, then an `EXPLAIN` dry run.
- Writes (POs, history, data cleaning) use fixed, parameterised statements. The AI never writes SQL for them.
- Prompt-injection rules plus a classifier, data from the database fenced as data, roles taken only from the signed session cookie.
- Secrets never leave the app. Personal data is masked in prompts, traces and logs. Result rows never reach LangSmith.
- Accepted for the demo: the app uses the database's `postgres` login. Two limited database accounts would be the first change for real use.

## Observability

Set `LANGSMITH_API_KEY` (and keep `LANGSMITH_TRACING=true`). Each chat turn becomes one trace with every graph node as a child run, grouped by conversation, masked before upload. Thumbs up and down attach a score to the turn's trace.

## Layout

```
backend/   FastAPI app (app/), tests/, evals/, scripts/ (data cleaning, e2e seed)
frontend/  Next.js app: app/, components/, lib/, stores/
e2e/       Playwright suite
db/        data-cleaning change records and backups
docs/      API contract
```
