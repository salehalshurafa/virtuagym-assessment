# Virtuagym workout plan manager

A full-stack workout plan manager built for the Virtuagym technical
interview. A trainer / admin signs in, manages a library of plans and
exercises, assigns plans to users, and tracks who is on which plan
through the full lifecycle (assign → modify → pause / resume / cancel /
restart → archive). Every state-changing action that affects a user
fires a transactional email to that user.

The repository contains two independent applications and four kinds of
automated tests across them.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Browser (user)                              │
│                                                                          │
│   Vue 3 SPA  ──cookie-credentialed axios──▶                              │
│   (frontend/)                                                            │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │  HTTP + JSON
                                     │  vg_session cookie (HttpOnly)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            FastAPI app                                   │
│                            (backend/)                                    │
│                                                                          │
│   /api/auth   /api/users   /api/plans   /api/plan-templates              │
│   /api/exercises   /api/weekly-split-templates   /api/assignments        │
│                                                                          │
│   Routers ─▶ Services ─▶ SQLModel ─▶ ╮                                   │
│                                       │                                  │
│                          aiosmtplib ─▶│                                  │
└────────────────────────────────────────┼─────────────────────────────────┘
                                         │
                  ┌──────────────────────┼──────────────────────┐
                  ▼                                             ▼
        ┌──────────────────┐                          ┌──────────────────┐
        │   PostgreSQL 16  │                          │   SMTP / Mailpit │
        │                  │                          │                  │
        │  users / plans   │                          │  transactional   │
        │  assignments /   │                          │  emails (assign, │
        │  templates / ... │                          │  modify, pause,  │
        │                  │                          │  archive, ...)   │
        └──────────────────┘                          └──────────────────┘
```

---

## What's in here

| Folder                    | What it is                                                                                                                                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`backend/`](./backend)   | FastAPI + SQLModel service. Postgres-backed, alembic-migrated, cookie-session-authed. See [`backend/README.md`](./backend/README.md) and [`backend/BACKEND_OVERVIEW.md`](./backend/BACKEND_OVERVIEW.md). |
| [`frontend/`](./frontend) | Vue 3 SPA (Vite + Pinia + shadcn-vue + Tailwind). See [`frontend/README.md`](./frontend/README.md) and [`frontend/FRONTEND_OVERVIEW.md`](./frontend/FRONTEND_OVERVIEW.md).                               |

Each subsystem stands alone — independent dependencies, independent test
suites, independent configs. The contract between them is HTTP + JSON
(plus an HttpOnly session cookie for auth).

---

## Quick start

You'll need:

- **Python 3.11+** and a **PostgreSQL 16** database for the backend.
- **Node.js 20+** for the frontend.
- Optionally **Mailpit** (or any SMTP) if you want emails to actually
  send; otherwise leave `EMAILS_ENABLED=false` in the backend `.env`.

### 1. Backend

```bash
cd backend
python -m venv venv
venv/Scripts/activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements-dev.txt
cp .env.example .env           # then edit DATABASE_URL etc.

alembic upgrade head           # create the schema
python -m scripts.seed         # optional: load seed data

uvicorn main:app --reload      # serve on http://localhost:8000
```

Swagger UI: <http://localhost:8000/docs>. Full setup walkthrough in
[`backend/README.md`](./backend/README.md).

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env           # default points VITE_API_URL at the backend on :8000

npm run dev                    # serve on http://localhost:5173
```

Open <http://localhost:5173>. If you ran the seed, log in as the seed
admin (`fakeadmin@example.com / ChangeMe!23`).

---

## Architecture at a glance

### Stack

| Layer                       | Choice                                                        |
| --------------------------- | ------------------------------------------------------------- |
| Backend framework           | FastAPI (Python 3.11+)                                        |
| ORM                         | SQLModel (SQLAlchemy 2.x)                                     |
| Database                    | PostgreSQL 16                                                 |
| Migrations                  | Alembic                                                       |
| Email                       | aiosmtplib + a `Mailer` Protocol (`SMTPMailer` / `LogMailer`) |
| Frontend framework          | Vue 3 (`<script setup>`) + TypeScript                         |
| Bundler                     | Vite 8                                                        |
| State                       | Pinia (setup-style)                                           |
| UI primitives               | shadcn-vue (built on reka-ui) + Tailwind v4                   |
| HTTP client                 | axios with `withCredentials: true`                            |
| Backend tests               | pytest (unit + HTTP integration via `TestClient`)             |
| Frontend unit + integration | Vitest + @vue/test-utils + @pinia/testing                     |
| End-to-end                  | Playwright (chromium / firefox / webkit)                      |

### Auth

Session-cookie-based, server-stored. The browser carries an HttpOnly
`vg_session` cookie; the backend resolves the cookie to a user row via
`services/auth.py::resolve_session` on every protected request. The
frontend never sees the cookie directly — it just trusts the success /
401 of every call.

```
User submits credentials  ──▶  POST /api/auth/login
                                  │
                                  ▼  Set-Cookie: vg_session=...; HttpOnly
Browser stores cookie  ◀───
                                  │
Subsequent requests    ──▶  Cookie: vg_session=...
                                  │
                                  ▼
                            services/auth.py::resolve_session
                                  │
                                  ▼  injected as `current_user` into routers
                            routers/...  (carries the request out)
```

On app load the frontend's `useAuthStore.bootstrap()` calls
`GET /api/auth/me` to recover the logged-in user without forcing a
re-login on every page reload.

### Data model (high level)

```
                      ┌────────────────────┐
                      │   plan_template    │   ← gallery (JSON-stored)
                      └─────────┬──────────┘
                                │ instantiate_plan_template
                                ▼
┌──────────┐     1:N      ┌──────────────┐    1:N    ┌────────────┐    1:N    ┌──────────────────────┐
│   user   │◀──────────────│      plan    │──────────▶│ weekly_    │──────────▶│   plan_day           │
│          │ user_plan_    │              │           │ workout_   │           │                      │
│          │ assignment    │              │           │ plan       │           │                      │
└──────────┘               └──────┬───────┘           └────────────┘           │                      │
                                  │                                            │                      │
                                  │  flat-mode plans skip the weekly layer:    │                      │
                                  └────────────1:N───────────────────────────▶│                      │
                                                                              └─────────┬────────────┘
                                                                                        │ 1:N
                                                                                        ▼
                                                                          ┌──────────────────────────┐
                                                                          │   exercise_assignment    │
                                                                          │  (slot in a day; free-   │
                                                                          │   text name, optional FK │
                                                                          │   to library exercise)   │
                                                                          └──────────────────────────┘

                                  ┌──────────────────────┐
                                  │  exercise (library)  │   ← reusable named exercises
                                  └──────────────────────┘
```

`user_plan_assignment` is the linking table that carries per-link state:
`start_date`, `end_date`, `status` (`in-progress` / `paused` /
`cancelled` / `completed`), `remaining_days` (set on pause), and
`assigned_at` / `assigned_by_*` for audit / display. A partial unique
index ensures **at most one in-progress assignment per user**.

Templates (`plan_template` and `weekly_split_template`) are
JSON-stored gallery blueprints. They get instantiated into a fresh live
plan tree on assignment via `services/template_service.py`.

### Email side effects

Every router that mutates user-visible state fires a matching mailer
method after the DB transaction commits:

| Trigger                                                            | Mailer method                               |
| ------------------------------------------------------------------ | ------------------------------------------- |
| `POST /api/users` (admin invite)                                   | `send_user_account_created`                 |
| `POST /api/assignments(/bulk)` and `POST /api/plans/from-template` | `send_plan_assigned`                        |
| `PATCH /api/plans/{id}`                                            | `send_plan_modified` (with structured diff) |
| `DELETE /api/plans/{id}`                                           | `send_plan_archived`                        |
| `POST /api/assignments/{id}/{pause,resume,cancel,restart}`         | matching `send_plan_*`                      |
| `POST /api/assignments/repoint-multi`                              | `send_plan_modified` per repointed user     |

Mail failures are wrapped in `try/except` so a flaky SMTP can never
break a request. The `Mailer` is a Protocol with two implementations
(`SMTPMailer`, `LogMailer`) selected per-request via the
`EMAILS_ENABLED` env var, so dev runs default to "log only" and
production runs out to real SMTP.

---

## Testing strategy

Four layers covering different risks:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Tests                                                                      │
│                                                                             │
│   ┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐             │
│   │  Backend    │   │  Frontend unit   │   │  Frontend        │             │
│   │  unit       │   │  (Vitest)        │   │  integration     │             │
│   │  (pytest)   │   │                  │   │  (Vitest)        │             │
│   │             │   │  Pinia stores    │   │                  │             │
│   │  Pure logic │   │  with mocked     │   │  Mounted Vue     │             │
│   │  no DB      │   │  axios           │   │  components,     │             │
│   │             │   │                  │   │  real Pinia,     │             │
│   └─────────────┘   └──────────────────┘   │  mocked axios    │             │
│                                            └──────────────────┘             │
│   ┌─────────────────────┐                  ┌──────────────────┐             │
│   │ Backend integration │                  │  Playwright e2e  │             │
│   │ (pytest +           │                  │                  │             │
│   │ FastAPI TestClient) │                  │  Real browser,   │             │
│   │                     │                  │  real frontend,  │             │
│   │ HTTP routes against │                  │  real backend,   │             │
│   │ in-memory SQLite    │                  │  real DB,        │             │
│   │                     │                  │  real Mailpit    │             │
│   └─────────────────────┘                  └──────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Layer                | Where                        | Runner                                    | What it catches                                                                                                             |
| -------------------- | ---------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Backend unit         | `backend/tests/unit/`        | pytest                                    | Pure logic in `services/` (assignment math, password helpers, user serialization)                                           |
| Backend integration  | `backend/tests/integration/` | pytest + `TestClient`                     | HTTP routes end-to-end against in-memory SQLite (auth flow, user CRUD, plan lifecycle, email side effects via `FakeMailer`) |
| Frontend unit        | `frontend/unit/`             | Vitest                                    | Pinia store mutations + computeds + axios-mocked actions                                                                    |
| Frontend integration | `frontend/integration/`      | Vitest + @vue/test-utils + @pinia/testing | Mounted components driving form interactions, mocked axios, real Pinia, asserting on render + store + emit + side effects   |
| End-to-end           | `frontend/e2e/`              | Playwright                                | Real-stack flows: auth, custom-plan build + assign + conflict-replace, admin-invite + welcome email arrives in Mailpit      |

Run order during a typical green-pass before committing:

```bash
# Backend
cd backend && pytest tests/

# Frontend (unit + integration)
cd ../frontend && npx vitest run

# Frontend (e2e — needs a running stack + seed)
cd ../backend && uvicorn main:app &
cd ../frontend && npm run dev &
cd ../backend && python -m scripts.seed
cd ../frontend && npx playwright test --project=chromium --workers=1
```

Or scope to whichever layer is relevant during iteration.

---

## Documentation map

| Doc                                                                | What's in it                                                                |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| [`backend/README.md`](./backend/README.md)                         | How to install, configure, migrate, seed, run, and test the backend         |
| [`backend/BACKEND_OVERVIEW.md`](./backend/BACKEND_OVERVIEW.md)     | Backend folders, models, services, API surface, email triggers, test layers |
| [`frontend/README.md`](./frontend/README.md)                       | How to install, configure, run, type-check, lint, and test the frontend     |
| [`frontend/FRONTEND_OVERVIEW.md`](./frontend/FRONTEND_OVERVIEW.md) | Frontend folders, components, stores, features, test layers                 |
| `backend/.env.example`                                             | Backend env-var template with inline docs                                   |
| `frontend/.env.example`                                            | Frontend env-var template with inline docs                                  |

For the original product brief, see `technical-interview-project.docx`
at the repo root.

---

## Known limitations

- **Image upload** uses base64 `data:` URLs stored in the existing `image_url` / `avatar_url` columns. A real upload endpoint with object storage is not implemented.
- **Admin-invite emails** include "ask the admin for your password" rather than a magic-link reset flow.
- **Production cookie / CORS hardening** — `cookie_secure=False` for dev. Flip to `True` and lock CORS to the production origin before deploying anywhere real.
- **Bcrypt's 72-byte input limit** is documented and tested but not migrated away from. A future move to Argon2id (with `passlib`'s `CryptContext`) would let existing bcrypt hashes transparently re-hash on next login.
