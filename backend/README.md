# Virtuagym Assessment Test Backend

FastAPI service that backs the workout plan manager. Speaks JSON over HTTP,
persists to Postgres via SQLModel, and emits transactional emails through
SMTP (or a no-op log mailer in dev).

For a tour of the code (folders, models, services, test layout), see
[`BACKEND_OVERVIEW.md`](./BACKEND_OVERVIEW.md).

---

## Requirements

- Python 3.11+
- A Postgres 16 database reachable from the host
- An SMTP server if you want emails to actually send (Mailpit works locally)

---

## Setup

```bash
cd backend
python -m venv venv            # Might need to use python3 in macOS / Linux
venv/Scripts/activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements-dev.txt # Might need to use python3 in macOS / Linux
```

Copy the example env file and fill in values:

```bash
cp .env.example .env
```

The two settings that always need attention:

| Variable         | What it is                                                                            |
| ---------------- | ------------------------------------------------------------------------------------- |
| `DATABASE_URL`   | Postgres connection string. Format: `postgresql+psycopg://user:pass@host:5432/dbname` |
| `EMAILS_ENABLED` | `true` to send via SMTP, `false` to write to the log instead                          |

Other variables (`CORS_ORIGINS`, `COOKIE_SECURE`, `SMTP_HOST`, etc.) are
documented inline in `.env.example`.

---

## Database

Run migrations to create the schema:

```bash
alembic upgrade head
```

Optional — load seed users, exercises, templates, and a handful of live
assignments so the dashboard has something to render:

```bash
python -m scripts.seed
```

The seed is idempotent on natural keys (email / title / label) so it's
safe to re-run.

To wipe and reseed cleanly:

```bash
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO virtuagym;"
alembic upgrade head
python -m scripts.seed
```

---

## Run the server

```bash
uvicorn main:app --reload
```

Default port is 8000. Interactive API docs (auto-generated from FastAPI)
are at:

- <http://localhost:8000/docs> — Swagger UI
- <http://localhost:8000/redoc> — ReDoc

Health check: `GET /health` returns `{"status": "ok"}`.

---

## Admin User to use

- Email: `fakeadmin@example.com`
- Password: `ChangeMe!23`

---

## Run the tests

The suite is split into two folders under `tests/`:

```
tests/
  conftest.py          shared fixtures (in-memory SQLite, FakeMailer, ...)
  unit/                pure-logic tests — no DB session, no HTTP
  integration/         HTTP routes driven via FastAPI's TestClient
```

### Run everything

```bash
pytest tests/
```

### Scope by type

```bash
pytest tests/unit/          # unit tests only
pytest tests/integration/   # integration tests only
```

### Scope by file or test

```bash
pytest tests/integration/test_plans.py
pytest tests/unit/test_assignment_service.py::test_pause_sets_remaining_days
pytest tests/ -k "pause"                    # any test whose name contains "pause"
pytest tests/ -k "pause and not completed"  # boolean filtering
```

### Useful flags

| Flag         | What it does                                        |
| ------------ | --------------------------------------------------- |
| `-v`         | Verbose: print each test name + status              |
| `-q`         | Quiet: dots and a one-line summary                  |
| `--tb=short` | Short tracebacks on failure                         |
| `-x`         | Stop after the first failure                        |
| `--lf`       | Re-run only what failed last time                   |
| `-s`         | Don't capture stdout — `print()` calls show up live |
| `--co`       | Collect-only: list tests without running them       |

### Common combinations

```bash
# Quick smoke
pytest tests/ -q

# Iterate on a failing test
pytest tests/integration/test_plans.py::test_patch_plan_emails_current_assignees -v --tb=long -s

# Re-run only what failed
pytest tests/ --lf -v
```

The tests use an in-memory SQLite database — no Postgres needed to run
them, and no setup beyond `pip install -r requirements-dev.txt`.

---

## Project layout

A short overview lives in [`BACKEND_OVERVIEW.md`](./BACKEND_OVERVIEW.md).
The high-level shape:

```
backend/
  main.py              FastAPI app + router mounting + middleware
  config.py            pydantic-settings (.env)
  db.py                SQLAlchemy engine + get_session dependency
  models/              SQLModel table definitions
  schemas/             Pydantic request/response shapes (camelCase aliases)
  routers/             FastAPI routers, one per resource
  services/            Business logic (mailer, plan / assignment / schedule)
  alembic/             Migration environment + versions
  scripts/seed.py      Seed loader
  tests/               unit/ + integration/
  uploads/             Static file mount for uploaded images
```
