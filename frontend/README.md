# Virtuagym Assessment Frontend

Vue 3 single-page app for the workout plan manager. Talks JSON over HTTP
to the FastAPI backend (see [`../backend/README.md`](../backend/README.md))
and runs entirely in the browser.

For a tour of the code (folders, components, stores, test layout), see
[`FRONTEND_OVERVIEW.md`](./FRONTEND_OVERVIEW.md).

---

## Requirements

- Node.js 20+ (LTS recommended)
- The backend running and reachable on the URL you'll set as `VITE_API_URL`
- Mailpit running on `MAILPIT_URL` only if you intend to run `e2e/invite-user-email.spec.ts`

---

## Setup

```bash
cd frontend
npm install
```

Copy the example env file and fill in values:

```bash
cp .env.example .env
```

The two settings that always need attention:

| Variable       | What it is                                                                                                                   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `VITE_API_URL` | Backend API base URL. Every axios call in the stores prepends this to `/api/...`. No trailing slash.                         |
| `MAILPIT_URL`  | Mailpit's HTTP base — only used by the welcome-email e2e spec. Safe to leave at the default if you're not running that test. |

Other notes:

- Only variables prefixed with **`VITE_`** are exposed to the running app via `import.meta.env`. Anything else (like `MAILPIT_URL`) is read by Node-side test code only.
- The dev server picks up `.env` automatically. Restart `npm run dev` after changing it.

---

## Run the dev server

```bash
npm run dev
```

Default port is `5173`. The dev server proxies nothing — the app makes
direct cross-origin calls to `VITE_API_URL`. CORS is configured on
the backend to allow `http://localhost:5173` by default.

To preview a production build instead of the dev server:

```bash
npm run build && npm run preview
```

`preview` serves the bundled output from `dist/` on port `4173` — useful
for confirming the production bundle works end to end.

---

## Type check + lint + format

```bash
npm run type-check     # vue-tsc — strict type check across the project
npm run lint           # oxlint + eslint, with --fix
npm run format         # prettier
```

`type-check` should always pass before committing — it's the gate that
catches API contract drift between the backend response shapes and the
frontend types.

---

## Run the tests

The suite splits into three layers:

```
frontend/
  unit/                Vitest — pure store + composable tests, no DOM
  integration/         Vitest — single-component tests with mocked axios
                       and real Pinia (via @pinia/testing)
  e2e/                 Playwright — full stack, real browser
```

### Unit + integration (Vitest)

```bash
npx vitest run                     # everything (unit + integration)
npx vitest run unit/               # unit only
npx vitest run integration/        # integration only
npx vitest run unit/stores/auth.spec.ts   # one file
npx vitest run -t "shows the right inline error"   # one test by name
npx vitest                         # watch mode (re-runs on file change)
```

Vitest uses jsdom (configured in `vitest.config.ts`), so DOM APIs work
without a real browser. axios is mocked per file via `vi.mock('axios')`,
so no backend is needed for these layers.

### End-to-end (Playwright)

E2E specs drive a real browser against the running stack: real frontend,
real backend, real database, real SMTP (Mailpit). The dev server is
auto-started by Playwright (`webServer` block in `playwright.config.ts`).

Pre-conditions before running:

- Backend running on the URL in `VITE_API_URL`.
- Database seeded (`cd ../backend && python -m scripts.seed`).
- Mailpit running on `MAILPIT_URL` if you want the welcome-email spec to pass.

```bash
npx playwright test                                # all specs, all browsers
npx playwright test --project=chromium             # chromium only (fastest)
npx playwright test --workers=1                    # serial (avoids parallel races on shared seed users)
npx playwright test assign-and-replace             # one spec
npx playwright test --debug                        # Playwright Inspector
npx playwright show-report                         # HTML report from the last run
```

For a thorough local pass: `--project=chromium --workers=1`. Re-seed
between runs with `python -m scripts.seed` since the assign-and-replace
spec mutates the seed users.

---

## Project layout

A short overview lives in [`FRONTEND_OVERVIEW.md`](./FRONTEND_OVERVIEW.md).
The high-level shape:

```
frontend/
  src/
    App.vue              Top-level shell + nav + bootstrap
    main.ts              Vue + Pinia + Router setup; axios defaults
    router/              vue-router config + auth guard
    views/               LoginView / SignupView / HomeView
    components/          Dashboard sections + dialogs + plan-form composable
    stores/              Pinia setup-stores (one per resource)
    types/               Domain types mirroring the backend
    lib/                 Small helpers (image encode, templateMatch, utils)
    assets/              Logo + global styles
  unit/                  Vitest unit tests (stores)
  integration/           Vitest integration tests (components)
  e2e/                   Playwright end-to-end specs
  public/                Static assets served as-is
  .env.example           Template for the .env file
```
