# Virtuagym backend — overview

A guided tour of what lives where. Pair this with [`README.md`](./README.md)
for setup and run/test commands.

---

## Stack

- **Python 3.11+** / **FastAPI** — HTTP layer
- **SQLModel** (SQLAlchemy 2.x) — ORM + Pydantic models in one
- **PostgreSQL 16** — relational store
- **Alembic** — schema migrations
- **bcrypt** — password hashing; **sha256** — session-cookie token hashing
- **aiosmtplib** — outbound email (pluggable behind a `Mailer` Protocol)
- **pytest** — test runner

All HTTP routes mount under `/api`. Static uploads are served from `/uploads`.

---

## Project layout

```
backend/
  main.py                  FastAPI app: middleware, CORS, router mount
  config.py                pydantic-settings (.env)
  db.py                    SQLAlchemy engine + get_session dependency
  alembic.ini              Alembic config
  Dockerfile               Container image
  docker-compose.yaml      Local Postgres + Mailpit

  models/                  SQLModel table definitions (the database shape)
    auth.py                Session
    user.py                User, UserPlanAssignment, UserPlanAssignmentStatus, Gender
    plan.py                Plan, WeeklyWorkoutPlan, PlanDay, ExerciseAssignment, DurationType
    exercise.py            Exercise, BodyCategory, Equipment, WeightUnit
    template.py            PlanTemplate, WeeklySplitTemplate

  schemas/                 Pydantic request/response models (camelCase on the wire)
    common.py              CamelModel base class
    auth.py                SignupRequest, LoginRequest, ...
    user.py                UserCreate / Read / Update + serialize_user()
    plan.py                Plan*, PlanDay*, ExerciseAssignment*, WeeklyWorkoutPlan*
    template.py            PlanTemplate*, WeeklySplitTemplate*, PlanFromTemplateRequest
    assignment.py          UserPlanAssignmentCreate / Read / Update + BulkAssign* + Repoint*
    exercise.py            ExerciseCreate / Read / Update
    schedule.py            ScheduleEntry, ScheduleExercise

  routers/                 FastAPI routers — one per resource
    deps.py                get_current_user / get_current_user_optional
    auth.py                /api/auth — signup / login / logout / me
    users.py               /api/users — user CRUD + soft-delete + restore + history
    exercises.py           /api/exercises — library CRUD
    plan_templates.py      /api/plan-templates — gallery templates
    weekly_split_templates.py  /api/weekly-split-templates — weekly templates
    plans.py               /api/plans — live plan CRUD + /active + /from-template
    assignments.py         /api/assignments — bulk-assign + repoint + lifecycle

  services/                Business logic, no HTTP awareness
    auth.py                Password hashing + session create/resolve/revoke
    clock.py               Per-user "today" in their timezone
    mailer.py              Mailer Protocol + SMTPMailer + LogMailer + get_mailer()
    plan_service.py        total_days, materialize_*, plan validation
    plan_diff.py           Snapshot a Plan + compute structured before/after diff
    template_service.py    Instantiate live plans from templates; promote live → template
    schedule_service.py    Walk a plan to compute the dated calendar
    assignment_service.py  pause / resume / cancel / restart math

  scripts/
    seed.py                Idempotent seed loader (users, exercises, templates, assignments)

  alembic/                 Migration environment + versions/

  tests/
    conftest.py            Shared fixtures (in-memory SQLite, FakeMailer, assignee, ...)
    unit/                  Pure-logic tests — no DB session, no HTTP
    integration/           HTTP routes driven via TestClient + in-memory SQLite

  uploads/                 Static mount served at /uploads

  requirements.txt         Runtime deps
  requirements-dev.txt     Dev/test deps (pytest, ruff, httpx)
  .env.example             Template for the .env file
```

---

## Models

All primary keys are UUID strings (auto-generated via `default_factory`).
Foreign keys declare explicit `ON DELETE` rules (`CASCADE` / `SET NULL`).

### Core

| Table | Purpose |
|---|---|
| `user` | The accounts table. First/last name, email (unique), bcrypt password hash, timezone, optional gender + phone + avatar URL, `removed` soft-delete flag. |
| `session` | Server-stored session rows keyed by sha256 of the cookie token. Carries `user_id`, `expires_at`, `last_used_at`, optional UA / IP. |
| `exercise` | Library of named exercises with body category + equipment + optional image / video / instructions + `usage_count`. |

### Plan tree (live)

A live plan is the per-user, per-assignment tree.

```
plan
  └─ weekly_workout_plan        (1:N — direct FK on weekly_workout_plan.plan_id)
       └─ plan_day              (1:N — direct FK on plan_day.weekly_plan_id)
            └─ exercise_assignment   (1:N — direct FK on plan_day.id)

(or, for "flat-mode" plans:)
plan
  └─ plan_day                   (1:N — direct FK on plan_day.plan_id)
       └─ exercise_assignment
```

| Table | Purpose |
|---|---|
| `plan` | Top-level live plan. Carries title, duration + duration type, optional image, optional `workout_days_per_week`, `archived` flag. |
| `weekly_workout_plan` | One weekly pattern inside a plan. Carries label, `week_frequency` (how many consecutive weeks this pattern runs), `order_index`. |
| `plan_day` | One day of a weekly (or one day of a flat plan). Carries label, `is_rest`, `order_index`. |
| `exercise_assignment` | One exercise slot inside a day. Carries `exercise_name` (free-text), optional FK to library `exercise`, sets / reps / weight / weight_unit / rest_seconds. |

### Plan tree (templates)

Gallery templates are JSON-stored copies that get instantiated into live trees on demand.

| Table | Purpose |
|---|---|
| `plan_template` | A reusable plan blueprint. Same fields as `plan`, but with the nested structure stored as JSON columns (`weekly_plans` or `flat_days`). |
| `weekly_split_template` | A reusable weekly pattern blueprint. Stores the seven-day structure as JSON. |

### Assignment

| Table | Purpose |
|---|---|
| `user_plan_assignment` | Links a user to a live plan with per-link state: `start_date`, `end_date`, `status` (`in-progress` / `paused` / `cancelled` / `completed`), optional `remaining_days` (set on pause), `assigned_at`, `assigned_by_name` / `assigned_by_email`. A partial unique index ensures at most one in-progress assignment per user. |

### Enums

| Enum | Values |
|---|---|
| `UserPlanAssignmentStatus` | `in-progress`, `completed`, `cancelled`, `paused` |
| `DurationType` | `days`, `weeks`, `months`, `years` |
| `BodyCategory` | `chest`, `back`, `legs`, `core`, `arms`, `shoulders`, `cardio` |
| `Equipment` | `bar`, `dumbbell`, `machine`, `cable`, `free-weight` |
| `WeightUnit` | `kg`, `lbs` |
| `Gender` | `male`, `female`, `other` |

All enums use **member values** (not names) as their Postgres ENUM labels,
so the wire format matches the values listed above (`in-progress`,
`free-weight`, etc.).

---

## Services

Business logic kept out of the routers, so the same functions can be
called from tests or the CLI without going through HTTP.

| Module | What it does |
|---|---|
| `services/auth.py` | `hash_password` / `verify_password` (bcrypt with explicit 72-byte truncation), `hash_token` (sha256), `create_session` / `resolve_session` / `revoke_session` for cookie-backed sessions. |
| `services/clock.py` | `today_for(user)` — resolves "today" against the user's timezone so a NY admin pausing a Tokyo user gets the Tokyo calendar boundary. |
| `services/mailer.py` | `Mailer` Protocol with one method per email kind (`send_plan_assigned`, `send_plan_modified`, `send_plan_archived`, the four lifecycle events, plus `send_user_account_created`). Two implementations: `SMTPMailer` (real network) and `LogMailer` (writes to log only). `get_mailer()` is a FastAPI dependency that picks based on the `EMAILS_ENABLED` env var. |
| `services/plan_service.py` | `total_days(duration, duration_type)`, the materialize helpers that build `Plan` / `WeeklyWorkoutPlan` / `PlanDay` / `ExerciseAssignment` ORM objects from request payloads, and the validators that reject malformed plan structure (e.g. non-rest day with no exercises). |
| `services/plan_diff.py` | `snapshot_plan(plan) -> dict` and `compute_plan_diff(old, new) -> list[change]`. Used by `PATCH /api/plans/{id}` to render an emailable diff into the modify-plan email. |
| `services/template_service.py` | `instantiate_plan_template` — build a fresh live `Plan` tree from a `PlanTemplate`'s JSON. `serialize_plan_to_template_json` / `serialize_weekly_to_template_json` — the inverse, used for "save as template". `cascade_library_exercises_for_week` — backfill the exercise library when promoting a custom week. |
| `services/schedule_service.py` | `compute_schedule(assignment) -> list[ScheduleEntry]` — walk the assignment's plan structure and emit one dated entry per calendar day from `start_date` through `end_date`. Cycles weekly rotations correctly. |
| `services/assignment_service.py` | `pause` / `resume` / `cancel` / `restart` — pure mutations on a `UserPlanAssignment` with the per-state preconditions (raise 409 on bad transitions). |

---

## API surface

Every endpoint mounts under `/api`. Responses are camelCase via Pydantic
alias generators; nullable fields are excluded from JSON when empty
(`response_model_exclude_none=True`).

| Mount | Source | Highlights |
|---|---|---|
| `/api/auth` | `routers/auth.py` | `POST /signup`, `POST /login`, `POST /logout`, `GET /me` |
| `/api/users` | `routers/users.py` | User CRUD, `DELETE` is soft (sets `removed=true`), `POST /{id}/restore`, `GET /{id}/assignments` (history) |
| `/api/exercises` | `routers/exercises.py` | Library CRUD |
| `/api/plan-templates` | `routers/plan_templates.py` | Template gallery CRUD, `POST /from-plan` (promote a live plan to a template) |
| `/api/weekly-split-templates` | `routers/weekly_split_templates.py` | Weekly template CRUD, `POST /from-weekly-plan` |
| `/api/plans` | `routers/plans.py` | Live plan CRUD (`DELETE` is soft archive). `GET /active` powers the dashboard. `POST /from-template` instantiates a template + bulk-assigns in one transaction. |
| `/api/assignments` | `routers/assignments.py` | `POST /bulk` (assign with conflict detection), `POST /repoint-multi` (carve out one user from a shared plan), lifecycle endpoints (`/{id}/pause`, `/resume`, `/cancel`, `/restart`), `/{id}/schedule` |

The interactive Swagger UI at `/docs` lists every route with full
request/response shapes.

---

## Email side effects

Routers that mutate user-visible state fire the matching mailer method
after the DB transaction commits. Failures in the mailer are caught and
swallowed so a flaky SMTP can never break a request.

| Trigger | Mailer method |
|---|---|
| `POST /api/users` (admin-create) | `send_user_account_created` |
| `POST /api/assignments` / `/bulk` / `POST /api/plans/from-template` | `send_plan_assigned` (per new assignee) |
| `PATCH /api/plans/{id}` | `send_plan_modified` (per active assignee, with structured diff) |
| `DELETE /api/plans/{id}` | `send_plan_archived` (per current assignee) |
| `POST /api/assignments/{id}/{pause,resume,cancel,restart}` | matching `send_plan_*` |
| `POST /api/assignments/repoint-multi` | `send_plan_modified` (per repointed user) |

All emails are multipart text + HTML with a small dark-orange branded shell.

---

## Tests

```
tests/
  conftest.py
  unit/
    test_assignment_service.py
    test_auth.py
    test_user.py
  integration/
    test_auth.py
    test_users.py
    test_plans.py
```

### Two layers, two purposes

**Unit (`tests/unit/`)** — pure-logic tests with no DB session and no
HTTP. They construct objects in memory, call a service function, and
assert on the result.

- `test_assignment_service.py` — pause / resume / cancel / restart math.
- `test_auth.py` — bcrypt + sha256 helpers (`hash_password`, `verify_password`, `to_bcrypt_bytes`, `hash_token`).
- `test_user.py` — `serialize_user` shaping (latest plan, removed flag, timezone defaults, optional profile fields).

**Integration (`tests/integration/`)** — drive real FastAPI routes via
`TestClient` against an in-memory SQLite engine. Exercise the full
request → router → ORM → response cycle without a network or real
Postgres.

- `test_auth.py` — signup / login / me / logout, including 401 paths.
- `test_users.py` — admin-create flow, soft-delete + restore, removed users still listable with the flag.
- `test_plans.py` — plan create + assign + visible on `/active`, plan modification fires `send_plan_modified`, plan delete archives + emails, atomic plan-from-template, validation rejecting empty workouts.

### Shared fixtures (in `tests/conftest.py`)

| Fixture | Use |
|---|---|
| `engine_fixture` | Brand-new in-memory SQLite engine per test, schema created from `SQLModel.metadata`. |
| `session` | SQLModel session bound to the engine, for direct DB writes/reads inside tests. |
| `client` | `TestClient` with `get_session` overridden to use the test engine. |
| `seed_user` | Inserts a known admin user (`admin@test.example` / `TestPass!23`). |
| `auth_client` | A `TestClient` already logged in as `seed_user` via real `/api/auth/login`. |
| `stub_current_user` | Overrides `get_current_user` to short-circuit to `seed_user`, bypassing the cookie path entirely. |
| `assignee` | A non-admin user (`Eve Assignee`) for tests that need someone to assign plans to. |
| `fake_mailer` | Overrides `get_mailer` with a `FakeMailer` that records every send into `fm.calls`, so tests can assert on email side effects. |

### How to run

See [`README.md`](./README.md) for the full command reference. The two
most common:

```bash
pytest tests/              # everything
pytest tests/unit/         # unit only
pytest tests/integration/  # integration only
```
