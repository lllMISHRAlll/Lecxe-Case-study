# Setup guide

Step by step: get the code, configure it, start the backend and the frontend, log in, and run the tests. There is also a Docker route and a Vercel deployment section.

| Part | Runs on | Started with |
|---|---|---|
| Backend (FastAPI) | http://localhost:8000 | `uvicorn` through `uv` |
| Frontend (Next.js) | http://localhost:3000 | `npm run dev` |
| Test / sample database (optional) | localhost:55432 | Docker |

The frontend sends every `/api/*` request to the backend (a rewrite in `frontend/next.config.ts`), so the browser only ever talks to port 3000 and the login cookie works without any CORS setup.

---

## 1. What you need

| Tool | Version | Check | Install |
|---|---|---|---|
| Git | any recent | `git --version` | https://git-scm.com |
| uv (Python manager) | 0.8 or newer | `uv --version` | macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh`, or `brew install uv`. Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Python | 3.13 | `uv python list` | Nothing to do: `uv sync` downloads Python 3.13 for you |
| Node.js and npm | Node 24 | `node --version` | https://nodejs.org, or `nvm install 24` |
| Docker Desktop | any recent | `docker --version` | Only for the local sample database, the test suite and the Docker route |
| make | any | `make --version` | Optional shortcut. Every `make` command below has a plain equivalent shown next to it. On Windows use the plain commands or WSL |

You also need:
- **A PostgreSQL database** with the company tables (`inv_*` and `proc_*`). Either the company's database, or the local sample database in step 4.
- **An AI key** (optional): an Anthropic or an OpenAI key. Without one the app runs on an offline rule-based stand-in, which is fine for a first look.

---

## 2. Get the code

```bash
git clone https://github.com/lllMISHRAlll/Lecxe-Case-study.git
cd Lecxe-Case-study
```

Project layout:

```
backend/    FastAPI app, tests, evals, scripts
frontend/   Next.js app
db/         data-cleaning change records
docs/       API contract, test questions, this guide
Makefile    shortcuts for everything below
```

---

## 3. Configure the environment

All settings live in one file in the **project root** (next to the `Makefile`). The backend reads it automatically. Never commit it.

```bash
cp .env.example .env
```

Open `.env` and set these:

| Variable | What to put | Notes |
|---|---|---|
| `DATABASE_URL` | Connection URL of the database with the company tables | See step 4. Never paste it into chat, issues or screenshots |
| `DATABASE_SSLMODE` | `require` for a hosted database, `disable` for the local sample | |
| `LLM_PROVIDER` | `anthropic` or `openai` | Only the selected provider's key is used |
| `ANTHROPIC_API_KEY` | Your key (`sk-ant-...`) | When `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Your key (`sk-...`) | When `LLM_PROVIDER=openai` |
| `JWT_SECRET` | A long random string | Generate one with `openssl rand -hex 32` |
| `DEMO_LOGIN_PASSWORD` | Password for the three demo users | Shown on the quick-login buttons when `APP_ENV` is not `prod` |
| `APP_ENV` | `dev` | `prod` hides the demo password |
| `FX_USD_INR` | `88` | USD to INR rate used in answers |
| `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING` | Optional | Turns on tracing; see the README |

Everything else in `.env.example` has a sensible default.

> If you have no AI key yet, leave the key empty (or set `FAKE_LLM=true`). The backend log then says it is using the offline stand-in.

---

## 4. Database

Pick one.

### Option A: the company database

1. Put its URL in `DATABASE_URL` and keep `DATABASE_SSLMODE=require`.
2. Create the app's own tables once. They go in a separate `assistant` schema and do not touch the company tables:

```bash
make migrate
# without make:
cd backend && uv run python -m app.db.migrate
```

The assistant reads the company tables through a read-only connection. The only writes to company tables are purchase orders that you confirm in the chat.

### Option B: a local sample database (no company data needed)

This creates a throw-away Postgres in Docker, loaded with sample data that mimics the real tables.

```bash
make testdb                      # docker compose up -d --wait testdb
make seed-e2e                    # builds the sample database "assistant_e2e"
# without make:
docker compose up -d --wait testdb
cd backend && uv run python -m scripts.seed_e2e
```

Then set in `.env`:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:55432/assistant_e2e
DATABASE_SSLMODE=disable
```

The sample database already includes the `assistant` schema, so you do not need `make migrate`. It lives in memory: stopping the container (`make down`) wipes it, and you run `make testdb` and `make seed-e2e` again next time.

---

## 5. Backend

From the project root:

```bash
# 1. install Python 3.13 and all backend dependencies from the lock file
make install                     # also installs the frontend; see step 6
# or only the backend:
cd backend && uv sync

# 2. start the server with auto-reload
make dev-backend
# without make:
cd backend && uv run uvicorn app.main:create_app --factory --reload --port 8000
```

Check it works:

| URL | Expect |
|---|---|
| http://localhost:8000/api/health | `{"status":"ok"}` |
| http://localhost:8000/api/docs | Swagger page listing the endpoints |

Leave this terminal running.

---

## 6. Frontend

Open a **second terminal** at the project root.

```bash
# 1. install dependencies
cd frontend
npm ci            # exact versions from package-lock.json (recommended)
# npm install     # also works; it may update the lock file

# 2. start the dev server, pointing it at the backend
BACKEND_URL=http://localhost:8000 npm run dev
# the same thing through make, from the project root:
make dev-frontend
```

On Windows PowerShell set the variable first: `$env:BACKEND_URL="http://localhost:8000"; npm run dev`.

`BACKEND_URL` defaults to `http://localhost:8000`, so you can leave it out when the backend runs there.

Open http://localhost:3000. You should see the login page.

Production build (optional):

```bash
cd frontend
npm run build
npm start          # serves on http://localhost:3000
```

---

## 7. Log in and try it

1. Open http://localhost:3000.
2. Pick a role with the quick-login button, or sign in with its demo email and the password you set in `DEMO_LOGIN_PASSWORD`:

| Role | Demo login |
|---|---|
| Procurement Manager | `procurement@demo.local` |
| Business Owner | `owner@demo.local` |
| Warehouse Manager | `warehouse@demo.local` |

3. Click a suggested question, or type one. Role-wise questions to try: [TEST_QUESTIONS.md](TEST_QUESTIONS.md).

If everything is wired correctly, the steps tick off on the right, the SQL appears, then a table or chart, and the answer types out on the left.

---

## 8. Run everything in Docker instead

This builds and starts the backend and the frontend in containers. It reads the same root `.env`.

```bash
make up           # docker compose up --build -d --wait backend frontend
make down         # stop and remove the containers
```

Open http://localhost:3000. Inside Docker the frontend reaches the backend at `http://backend:8000` automatically.

Note: a database on `localhost` is not reachable from inside a container as `localhost`. For the local sample database use `host.docker.internal` instead of `localhost` in `DATABASE_URL`, or run the backend with `make dev-backend` and only the frontend in Docker.

---

## 9. Tests and checks

| Command | What it does |
|---|---|
| `make test` | Backend tests with coverage gates. Needs the Docker test database (`make testdb` starts it) |
| `make test-frontend` | Frontend tests with coverage gates |
| `make lint` | Ruff and type checks for the backend, ESLint and TypeScript for the frontend |
| `make test-all` | Backend and frontend tests |
| `make eval-deepeval` | AI quality eval against the real model (needs an AI key) |

Without make:

```bash
cd backend  && uv run pytest
cd frontend && npm test            # or: npm run test:coverage
cd frontend && npm run lint && npm run typecheck
```

The tests never call a model provider and never touch the company database.

---

## 10. Deploy on Vercel

Two separate Vercel projects from the same repository.

### Backend project

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Framework preset | Other |
| Entry point | `backend/index.py` (already in the repo; it exposes the FastAPI app) |
| Function timeout | 300 s, set in `backend/vercel.json` so streaming answers are not cut |
| Environment variables | Every variable from step 3 (`DATABASE_URL`, `DATABASE_SSLMODE=require`, the AI key, `JWT_SECRET`, `APP_ENV=prod`, and so on). Set them in the Vercel dashboard, not in the repo |

After deploying, open `<backend-url>/api/health`. It should return `{"status":"ok"}`. Run `make migrate` once from your machine against the same database if the `assistant` schema does not exist yet.

### Frontend project

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Next.js |
| Install / build | `npm ci` / `npm run build` (defaults) |
| Environment variable | `BACKEND_URL` = the backend project's URL, with no trailing slash |

`BACKEND_URL` is used when the app is built, so **set it before the first deploy, and redeploy the frontend if you change it**.

Current deployment:
- Frontend: https://lecxe-procurement-web.vercel.app
- Backend: https://lecxe-procurement-api.vercel.app

---

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| `uv: command not found` | Install uv (step 1) and open a new terminal |
| Wrong Python version | Run `uv sync` inside `backend/`; it fetches Python 3.13 itself |
| `node` is older than 24 | `nvm install 24 && nvm use 24`, then `npm ci` again |
| `make: command not found` (Windows) | Use the plain commands shown next to each `make` command, or WSL |
| Port 8000 or 3000 already in use | Stop the other process, or run on another port: `--port 8001` for uvicorn, `npm run dev -- -p 3001` for Next.js (and set `BACKEND_URL` to match) |
| Login page loads but login fails, or every request gives 404 or 502 | The backend is not running, or `BACKEND_URL` is wrong. Open http://localhost:8000/api/health to check |
| Backend log says it is using the offline stand-in | The selected provider has no key. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to match `LLM_PROVIDER`, then restart |
| "The AI service isn't available right now" | The key is wrong or has no quota. Check the key matches the provider (`sk-ant-` is Anthropic, `sk-` is OpenAI) |
| SSL error connecting to the database | Hosted databases need `DATABASE_SSLMODE=require`. The local sample needs `disable` |
| `relation "assistant.conversations" does not exist` | Run `make migrate` (company database). The sample database already has it |
| `make test` cannot connect to port 55432 | Docker is not running. Start Docker Desktop, then `make testdb` |
| Changed `.env` but nothing changed | Restart the backend. In Docker: `docker compose up -d --force-recreate backend` |
| Answers arrive all at once instead of streaming (hosted) | Do not put a compression or buffering proxy in front of `/api/chat/stream`. The frontend already disables compression |
| Frontend on Vercel returns errors for `/api/...` | `BACKEND_URL` was missing at build time. Set it and redeploy the frontend |
