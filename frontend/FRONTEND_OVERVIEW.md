# Virtuagym frontend — overview

A guided tour of what lives where in the Vue 3 SPA. Pair this with
[`README.md`](./README.md) for setup and run/test commands.

---

## Stack

- **Vue 3** (Composition API, `<script setup>`) + **TypeScript**
- **Vite 8** — dev server + bundler
- **Pinia** — state, setup-style stores
- **vue-router** — auth-guarded SPA routing
- **shadcn-vue** (built on reka-ui) + **Tailwind v4** — UI primitives
- **lucide-vue-next** — icon set
- **axios** — HTTP client (cookie-credentialed)
- **@internationalized/date** — calendar helpers via reka-ui
- **Vitest** + **@vue/test-utils** + **@pinia/testing** — unit + integration tests
- **Playwright** — end-to-end tests
- **oxlint** + **ESLint** + **Prettier** — linting / formatting

---

## Project layout

```
frontend/
  src/
    App.vue                  Sticky nav + main scroll area; bootstraps when authed
    main.ts                  Vue + Pinia + Router setup; axios.defaults.withCredentials
    router/index.ts          Routes + auth guard (calls auth.bootstrap once)

    views/
      LoginView.vue          Full-page login form
      SignupView.vue         Full-page signup form
      HomeView.vue           Dashboard for authenticated users

    components/
      ActivePlansList.vue    Active plans section + assign button
      ActivePlanDialog.vue   View a live plan + per-assignee lifecycle actions
      AssignPlansDialog.vue  Wizard: choose-path → custom or existing → pick users
      AssignNowPanel.vue     Bulk-assign panel + conflict prompt + result banner
      AssignmentConflictPrompt.vue   "Replace existing plan?" UI
      BulkUserSelect.vue     Checkbox list of users with on-plan badges
      PartialResultsBanner.vue       Post-bulk results summary

      AddPlanDialog.vue      Three-step plan-template create wizard
      PlanDialog.vue         Plan-template view + edit + soft-archive
      ModifyUserPlanDialog.vue       Edit a user's live plan (apply-all vs carve-out)
      PlanEditForm.vue       Shared editor used by Edit + Modify
      PlansList.vue          Gallery of plan templates

      AddWeeklyPlanDialog.vue        Standalone weekly template create / fork
      WeeklyPlanDialog.vue           Weekly template view + edit + delete
      WeeklyTemplateEditor.vue       The seven-day editor used by both
      WeeksList.vue                  Gallery of weekly templates

      AddExerciseDialog.vue  POST /api/exercises
      ExerciseDialog.vue     Exercise view + PATCH + DELETE
      ExercisesList.vue      Searchable exercise library

      AddUserDialog.vue              Admin-creates-user with one-time temp password
      UserProfileDialog.vue          PATCH /api/users/{me.id} + self soft-delete
      UserDetailsDialog.vue          Other-user view + edit + remove + lifecycle
      UsersList.vue                  Users table
      UserProfile.vue                Nav-bar avatar dropdown
      UserAvatar.vue                 Img-or-initials avatar
      AvatarUploader.vue             Click-or-drag image upload to data-URL
      TimezoneSelect.vue             IANA zone dropdown via Intl.supportedValuesOf

      plan-form/             The plan-form composable + its step components
        usePlanForm.ts       Composable: state + validation + dirty tracking
        ids.ts               createId() helper for form-local ids
        StepOneBasics.vue    Title / image / duration / workout-days picker
        StepTwoDays.vue      Tabbed weekly editor used by the Add wizard
        PlanWorkoutsEditor.vue   Accordion editor used by the Edit dialog
        DayCard.vue          One weekday — exercises editor, copy-from, rest toggle

      skeletons/             Bootstrap-time placeholder loaders
      ui/                    shadcn-vue primitives (button, dialog, input, ...)

    stores/                  Pinia setup-stores
      auth.ts                me / login / signup / logout / bootstrap
      users.ts               users + me + activeUsers + manageableUsers + lifecycle
      activePlans.ts         live plans dashboard data + assignee patching
      plans.ts               live plans store (ingestPlan upserts)
      planTemplates.ts       gallery plan templates
      weeklySplitTemplates.ts        gallery weekly templates
      exercises.ts           exercise library

    types/                   Domain types (mirror backend response shapes)
      user.ts                User / PlanStatus / UserCurrentPlan / Gender
      plan.ts                Plan / WeeklyWorkoutPlan / PlanDay / ExerciseAssignment
      exercise.ts            Exercise / BodyCategory / Equipment
      template.ts            PlanTemplate / WeeklySplitTemplate
      weeklyPlan.ts          Legacy weekly-plan helpers

    lib/
      images.ts              fileToDataUrl — base64 image encoder
      templateAdapter.ts     templateToPlan + planPayloadToTemplateUpdate
      templateMatch.ts       Structural fingerprints for "save as template" gating
      utils.ts               cn() — Tailwind class merge helper

    assets/                  Logo + global styles

  unit/                      Vitest unit tests (stores)
    stores/
      activePlans.spec.ts
      auth.spec.ts
      users.spec.ts

  integration/               Vitest integration tests (mounted components)
    ActivePlansList.spec.ts
    AddUserDialog.spec.ts
    LoginView.spec.ts

  e2e/                       Playwright end-to-end specs
    auth.spec.ts
    plans.spec.ts
    assign-and-replace.spec.ts
    invite-user-email.spec.ts

  public/                    Static assets (favicon, etc.)
  index.html                 Vite HTML entry
  vite.config.ts             Vite config
  vitest.config.ts           Vitest config (jsdom env, e2e excluded)
  playwright.config.ts       Playwright config (chromium / firefox / webkit projects)
  tsconfig*.json             TypeScript configs (app + node + vitest)
  package.json               Deps + npm scripts
  .env.example               Template for the .env file
```

---

## Stores

Each store is a Pinia setup-store with `defineStore('name', () => { ... })`.
Most expose:

- A reactive `ref<T[]>` of items.
- An `init*` action to seed it from the bootstrap response.
- `ingest*` upsert actions to apply server responses after a mutation.
- `getById` / `titleExists` lookups.
- A `remove*` action for local cleanup.

| Store | Backs |
|---|---|
| `useAuthStore` | `LoginView`, `SignupView`, `App.vue`'s bootstrap, the router guard, the global 401 interceptor |
| `useUsersStore` | `UsersList`, `BulkUserSelect`, `AddUserDialog`, `UserProfileDialog`, `UserDetailsDialog` |
| `useActivePlansStore` | `ActivePlansList`, `ActivePlanDialog` (read), `AssignNowPanel` (optimistic ingest after bulk-assign) |
| `usePlansStore` | Live `Plan` rows ingested after `POST /api/plans` and `POST /api/plans/from-template` |
| `usePlanTemplatesStore` | `PlansList`, `AddPlanDialog`, `PlanDialog` |
| `useWeeklySplitTemplatesStore` | `WeeksList`, `AddWeeklyPlanDialog`, `WeeklyPlanDialog`, the `Use a template` picker |
| `useExercisesStore` | `ExercisesList`, `AddExerciseDialog`, `ExerciseDialog`, the day-card's library autocomplete |

The auth store is the only one with non-trivial async actions (`bootstrap`,
`login`, `signup`, `logout`); the rest mostly do upserts and the actual
HTTP work happens inline in component handlers.

---

## Cross-cutting wiring

- **Cookie auth.** `axios.defaults.withCredentials = true` is set in `main.ts` so the browser sends the HttpOnly `vg_session` cookie with every request. The auth store's `bootstrap()` populates `me` from `GET /api/auth/me` on app load.
- **Auth guard.** `router.beforeEach` waits for the first bootstrap, then redirects unauthenticated users to `/login` (preserving the original path in `?redirect=`) and authenticated users away from `/login` / `/signup` back to `/`.
- **Global 401 interceptor.** A response interceptor in `main.ts` clears `auth.me` and bounces to `/login?redirect=...` whenever any request 401s, so a session expiring mid-use lands the user back on the login screen instead of leaving stale state.
- **Bootstrap-skeleton gate.** `App.vue` shows `HomeViewSkeleton` while `loadDashboardData()` is in flight — a parallel `Promise.allSettled` of `users / plan-templates / exercises / weekly-split-templates / plans/active`. The dashboard mounts only after that chain settles.

---

## Features provided

User-facing capabilities of the SPA, grouped by surface.

### Authentication

- **Login** with email + password against `/api/auth/login`.
- **Signup** with auto-detected timezone (via `Intl.DateTimeFormat().resolvedOptions().timeZone`).
- **Cookie-backed sessions** — once logged in, page reloads stay authenticated until the cookie expires (30-day default).
- **Auto-redirect** on session expiry — any 401 mid-session sends the user back to `/login` with a `?redirect=` so they land where they were after re-authenticating.
- **Logout** from the nav avatar dropdown.

### Plans gallery (templates)

- **Add Plan** — three-step wizard: Basics → Workouts → Schedule & Assignees.
- **Edit / archive** plan templates.
- **Fork** an existing template into a new one (via `PlanDialog`'s Fork button → controlled `AddPlanDialog`).
- **Two plan modes** — weekly (rotating weekly patterns) and flat (one continuous list of days).
- **Conditional workout-days-per-week** picker that shows only for whole-week durations.

### Weekly splits gallery (templates)

- **Add / edit / delete** standalone weekly templates.
- **Fork** an existing weekly template.
- **Seven-day editor** with rest-day toggle and "copy from another day" shortcut.

### Exercise library

- **CRUD** for the exercise library (name, body category, equipment, image / video / instructions).
- **Library autocomplete** inside the day editor — typing matches against the library, exact matches auto-link the `exerciseId` so the assignment knows which library row it came from.
- **Top-3 popular** exercises shown when no search is active.

### Users

- **Admin-create user** — generates a 16-char random temp password, posts to `/api/users`, reveals the password once for out-of-band sharing.
- **Edit profile** — name, email, gender, phone, timezone, avatar (uploaded as a 2 MB-capped data-URL).
- **Soft-delete + Re-list** — removed users stay in the list with a "Removed" badge and a one-click restore.
- **History view** — every plan a user has ever been on, sorted by `assigned_at` desc.
- **Lifecycle actions** — pause / resume / cancel / restart a user's current assignment from the active-plan dialog.

### Active plans dashboard

- **Live plans view** — every plan with at least one in-progress or paused assignee, plus the assignee chips and an aggregate `statusSummary`.
- **Filter** by title search, duration type, and status (in-progress / paused / mixed).
- **Drill-in** — open `ActivePlanDialog` to see the per-assignee detail, dated schedule, and structural breakdown.

### Assignment

- **Build-and-assign wizard** (`AssignPlansDialog`) — pick "build a custom plan" or "use existing template", configure, then assign in one flow.
- **Bulk assignment** — multi-select users, with **conflict detection** for users already on a plan and a Replace / Skip prompt per conflict.
- **Atomic plan create + assign** via `POST /api/plans/from-template` for the "use existing as-is" path; the build-custom path uses deferred plan creation (`prepareAssignment`) so closing the dialog before the assign click never leaves an orphan plan in the DB.
- **Optimistic ingest** — after a successful assign the active-plans dashboard updates synchronously without waiting for a server refresh.

### Modify user plan

- **Apply to everyone** — modify the live plan in place; sends `send_plan_modified` to every assignee with a structured diff.
- **Carve out** — clone the plan, repoint just this user's assignment to the clone; other assignees stay on the original.
- **Single-user fast path** — when the user is the only assignee, the apply-question step is skipped automatically.

### UI and feedback

- **Skeleton loaders** for every dashboard section during bootstrap.
- **Inline errors** (rose-tinted strips) on every save / delete handler.
- **Loading states** on every button that hits the network ("Saving…", "Assigning…", etc.) with the button disabled to prevent double-submits.
- **Responsive** down to phone widths — gallery rows stack, dashboard stacks, dialogs fit small viewports.
- **Dark mode by default** — `class="dark"` on portal-rendered popovers/dialogs so shadcn theme variables resolve to dark values.

---

## Test layers

Three flavors. Each has its own folder and its own runner.

### Unit (Vitest, `unit/`)

Pure logic — Pinia store mutations + computeds + axios-mocked actions. No
DOM mount, no `vue-router`, no children. Fast and isolated.

| File | What it covers |
|---|---|
| `unit/stores/activePlans.spec.ts` | `ingestActivePlan` upsert, `removeActivePlan`, `updateAssignee` (cross-row patch), `removeAssignee` (drop + prune empty) |
| `unit/stores/users.spec.ts` | `updateUser` (with `me` mirroring), `markRemoved`, `activeUsers` / `manageableUsers` computeds, `refetchUser` / `restoreUser` against mocked axios |
| `unit/stores/auth.spec.ts` | `login` / `bootstrap` / `logout` / `patchMe` / `browserTimezone` against mocked axios |

### Integration (Vitest, `integration/`)

Component-level tests — real Pinia (via `@pinia/testing`'s
`createTestingPinia`), real component render, but **axios is mocked**.
Drives user interactions (`setValue`, `trigger`) and asserts on rendered
output, store mutations, and emitted events.

| File | What it covers |
|---|---|
| `integration/ActivePlansList.spec.ts` | Renders rows from store state, search filter, status filter, empty / no-match states |
| `integration/AddUserDialog.spec.ts` | Form fill → POST → store ingest, 409 inline error, success-phase password reveal, `created` event emission |
| `integration/LoginView.spec.ts` | Form fill → `auth.login` → router redirect (with `?redirect=` honored), 401 / generic error rendering, empty-fields guard |

### E2E (Playwright, `e2e/`)

Full stack: real frontend, real backend, real database, real SMTP for the
welcome-email spec. Drives a real browser via Playwright's auto-launched
chromium / firefox / webkit projects. Asserts on rendered DOM and (in
spec #4) on Mailpit's HTTP API for outbound side-effect verification.

| Spec | What it covers |
|---|---|
| `e2e/auth.spec.ts` | 401 redirect, login happy path, wrong-password inline error, signup creates account |
| `e2e/plans.spec.ts` | Newly-saved weekly template appears in WeeksList without reload (Bug-1 e2e mirror) |
| `e2e/assign-and-replace.spec.ts` | Custom plan build → bulk-assign 3 users → conflict-replace → results banner → new plan visible in ActivePlansList with all 3 assignees |
| `e2e/invite-user-email.spec.ts` | Admin invites user → success dialog with temp password → welcome email arrives in Mailpit referencing the inviter |

### How to run

See [`README.md`](./README.md) for the full command reference. The
shortest paths:

```bash
npx vitest run                          # unit + integration
npx playwright test --project=chromium  # e2e against a single browser
```
