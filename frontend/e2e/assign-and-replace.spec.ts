import { expect, test, type Locator, type Page } from '@playwright/test'

/**
 * E2E Scenario 1 from SESSION_FOLLOWUP_3.md §8.2 — Custom plan build,
 * assign, replace.
 *
 * Drives the AssignPlansDialog from the dashboard's Active Plans header:
 *   choose-path (custom)
 *     → custom-basics (title / 2 weeks / 3 days)
 *     → custom-workouts (apply Strength Block, add a second weekly,
 *                         configure 7 days, copy day 7 from day 1)
 *     → pick-users (Sam + Lily + Alex)
 *     → conflict prompt for Alex → Replace
 *     → results banner → Done → wizard "All done" → Close
 *
 * Then asserts the new plan shows up in ActivePlansList with all three
 * assignees.
 *
 * Pre-conditions (matches SESSION_FOLLOWUP_3.md §8.2):
 *  - Backend + frontend running, seeded via `python -m scripts.seed`.
 *  - Seed users (post-seed only — don't re-run without reseeding):
 *      Sam Carter, Lily Chen     → no plan
 *      Alex Rodriguez, Tahseen   → in-progress
 *      Jordan Kim                → paused
 *      Maya Patel                → cancelled
 *  - "Strength Block" weekly-split template exists.
 *  - Library exercises include "Back Squat" / "Lunges" / "Bench Press" /
 *    "Overhead Press" (the four we drop into the second weekly).
 *
 * Re-running this test without reseeding will fail: Sam + Lily end up
 * on a plan after the first run, so the second run's "no plan" assumption
 * breaks. Reseed (`DROP SCHEMA public CASCADE; alembic upgrade head;
 * python -m scripts.seed`) between runs.
 */

interface ExerciseInputs {
  sets: number
  reps: number
  weight: number
  rest: number
}

/**
 * Workaround for Playwright × NativeSelect (`components/ui/native-select`).
 *
 * NativeSelect uses `useVModel(props, "modelValue", emit, { passive: true })`,
 * which propagates the new value to the parent binding via a watch on
 * the local ref — that watch fires on a microtask AFTER the current
 * `change` event handler completes. Manual users don't notice because
 * real browsers space input/change events with enough microtask room
 * for the watch to flush before any subsequent handler reads the parent
 * binding. Playwright's synthetic `selectOption` dispatches input/change
 * synchronously, so any parent `@change` handler that reads the v-model'd
 * ref (`onApplyTemplate` reads `templateToApply`, `onCopyDay` reads
 * `copySource`) sees a stale value and bails via its early-return.
 *
 * Net effect without this helper: the option appears selected in the DOM
 * but the side-effect (apply template / copy day) silently never runs.
 *
 * Workaround: fire `change` twice. The first dispatch (via selectOption)
 * sets the inner select's value and lets useVModel's watch propagate to
 * the parent in the awaited microtask. The second dispatch fires `change`
 * again — vModelSelect's listener no-ops on the unchanged value, but the
 * parent's `@change` handler now reads the up-to-date binding and runs
 * its side-effect.
 *
 * Remove this helper when NativeSelect is migrated off the
 * passive-useVModel pattern (e.g. listening for `update:modelValue` in
 * the parent or using a sync watch).
 */
const applyNativeSelect = async (select: Locator, value: string): Promise<void> => {
  await select.selectOption(value)
  // Re-fire change. Awaiting selectOption above already flushed the
  // microtask that propagated the new value to the parent binding, so
  // this second dispatch invokes the parent's @change with correct state.
  await select.dispatchEvent('change')
}

const dayCardFor = (dialog: Locator, dayIndex: number): Locator =>
  // Day-label inputs are unique by `aria-label` ("Label for Day 1", etc.).
  // Walk up two parents (Input → header row → DayCard root). DayCard's
  // root is the rounded card; everything for that day lives under it.
  dialog.locator('input[aria-label^="Label for"]').nth(dayIndex).locator('xpath=../..')

const addExercise = async (
  dayCard: Locator,
  name: string,
  params: ExerciseInputs,
): Promise<void> => {
  await dayCard.getByRole('button', { name: 'Add exercise' }).click()
  // The freshly added row enters edit mode; only one edit form exists at
  // a time (clicking Add Exercise auto-collapses the previous one).
  // ``exact: true`` matters here: getByLabel does case-insensitive
  // substring match by default, and "Weight" alone would also match the
  // sibling "Weight unit" <select>.
  await dayCard.getByLabel('Exercise name', { exact: true }).fill(name)
  await dayCard.getByLabel('Sets', { exact: true }).fill(String(params.sets))
  await dayCard.getByLabel('Reps', { exact: true }).fill(String(params.reps))
  await dayCard.getByLabel('Weight', { exact: true }).fill(String(params.weight))
  await dayCard.getByLabel('Rest seconds', { exact: true }).fill(String(params.rest))
  await dayCard.getByLabel('Done editing', { exact: true }).click()
}

const loginAsAdmin = async (page: Page): Promise<void> => {
  await page.context().clearCookies()
  await page.goto('/login')
  await page.getByLabel('Email').fill('fakeadmin@example.com')
  await page.getByLabel('Password').fill('ChangeMe!23')
  await page.getByRole('button', { name: /sign in/i }).click()
  // Login POST + cookie set + router push + auth.bootstrap() race past
  // the default expect.timeout (5s in playwright.config.ts).
  await expect(page).toHaveURL('/', { timeout: 15_000 })
}

test.describe('Custom plan build → bulk-assign → conflict resolved as Replace', () => {
  // The custom-plan flow is long; bump the per-test budget so we don't
  // bail mid-form on slower machines.
  test.setTimeout(90_000)

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('builds a 2-week custom plan, assigns to 3 users, replaces Alex', async ({ page }) => {
    const planTitle = `E2E-Assign test ${Date.now()}`

    // After login, App.vue's `v-if="isBootstrapping"` un-mounts the entire
    // HomeView while the parallel store loads (users / plan-templates /
    // exercises / weekly-split-templates / plans/active) settle. Wait for
    // the actual button we click next rather than a sibling heading —
    // same gate, more honest target, and the failure mode is clearer.
    const assignBtn = page.getByRole('button', { name: /assign plans/i })
    await expect(assignBtn).toBeVisible({ timeout: 25_000 })
    await assignBtn.click()

    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()

    // ---- Step: choose-path -------------------------------------------------
    await dialog.getByRole('button', { name: /build a custom plan/i }).click()
    await dialog.getByRole('button', { name: /^next$/i }).click()

    // ---- Step: custom-basics ----------------------------------------------
    await dialog.getByLabel('Name').fill(planTitle)
    await dialog.getByLabel('Duration', { exact: true }).fill('2')
    await dialog.getByLabel('Duration type').selectOption('weeks')
    // Workout-days-per-week pill picker — buttons labeled 1..7. Pick 3.
    await dialog.getByRole('button', { name: '3', exact: true }).click()
    await dialog.getByRole('button', { name: /^next$/i }).click()

    // ---- Step: custom-workouts --------------------------------------------
    // Apply the "Strength Block" template into the (sole) starting weekly.
    //
    // The fire-change-twice pattern below works around a Playwright/
    // NativeSelect interaction bug — see `applyNativeSelect` for the
    // diagnosis. Without the second dispatch, `onApplyTemplate` runs on
    // a stale parent binding and bails, leaving W1 with empty default days.
    const tplSelect = dialog.getByLabel('Apply weekly template')
    const strengthOption = tplSelect.locator('option').filter({ hasText: 'Strength Block' }).first()
    await expect(strengthOption).toHaveAttribute('value', /.+/)
    const strengthValue = await strengthOption.getAttribute('value')
    await applyNativeSelect(tplSelect, strengthValue!)

    // Active weekly's label is now "Strength Block". Add a second weekly —
    // the dialog auto-switches active to it. Both weeklies default to
    // weekFrequency=1, perfect for a 2-week plan (1 + 1 = 2 per cycle).
    await dialog.getByRole('button', { name: /add weekly workout plan/i }).click()

    // Sanity-check: the multi-plan frequency input is now visible (only
    // shown when there's >1 weekly).
    await expect(dialog.getByLabel('Week frequency')).toBeVisible()

    // ---- Configure the second weekly's seven days -------------------------
    // Day 1 — Legs
    const day1 = dayCardFor(dialog, 0)
    await day1.getByLabel(/^Label for Day 1$/).fill('Day 1 - Legs')
    await addExercise(day1, 'Back Squat', { sets: 4, reps: 8, weight: 70, rest: 90 })
    await addExercise(day1, 'Lunges', { sets: 3, reps: 12, weight: 20, rest: 60 })

    // Day 2 — Push
    const day2 = dayCardFor(dialog, 1)
    await day2.getByLabel(/^Label for Day 2$/).fill('Day 2 - Push')
    await addExercise(day2, 'Bench Press', { sets: 4, reps: 8, weight: 60, rest: 90 })
    await addExercise(day2, 'Overhead Press', { sets: 3, reps: 10, weight: 35, rest: 60 })

    // Days 3–6 — rest
    // The checkbox uses one-way `:checked="day.isRest"` + `@change="toggleRest"`.
    // `.check()` clicks the input, which should fire `change` and flip
    // Vue's reactive `day.isRest` to true. Verifying with toBeChecked()
    // after each toggle gives us a precise failure ("day N didn't toggle")
    // instead of a vague "Next is disabled" 90s timeout.
    for (const idx of [2, 3, 4, 5]) {
      const card = dayCardFor(dialog, idx)
      const rest = card.getByLabel('Rest day')
      await rest.check()
      await expect(rest).toBeChecked()
    }

    // Day 7 — copy from "Day 1 - Legs". applyNativeSelect handles the
    // Playwright/NativeSelect bug; without it, `onCopyDay` runs against
    // a stale `copySource` and bails, leaving Day 7 empty.
    const day7 = dayCardFor(dialog, 6)
    const copyFrom = day7.getByLabel('Copy configuration from another day')
    const day1Option = copyFrom.locator('option').filter({ hasText: 'Day 1 - Legs' }).first()
    await expect(day1Option).toHaveAttribute('value', /.+/)
    const day1Value = await day1Option.getAttribute('value')
    await applyNativeSelect(copyFrom, day1Value!)

    // ---- Step: pick-users -------------------------------------------------
    await dialog.getByRole('button', { name: /^next$/i }).click()

    // BulkUserSelect renders one button per user. Default substring-match
    // on getByRole('button', { name }) finds them by full name.
    for (const fullName of ['Sam Carter', 'Lily Chen', 'Alex Rodriguez']) {
      await dialog.getByRole('button', { name: fullName }).click()
    }

    // Submit. Alex has an in-progress plan from seed → conflict prompt.
    await dialog.getByRole('button', { name: /^Assign \d+ user/i }).click()

    // ---- Conflict prompt --------------------------------------------------
    await expect(dialog.getByText(/already.*active or paused plan/i)).toBeVisible()
    // One Replace per conflict row; Alex is the only conflict.
    await dialog.getByRole('button', { name: /^Replace$/ }).click()
    await dialog.getByRole('button', { name: /^Continue$/ }).click()

    // ---- Results banner ---------------------------------------------------
    // Two API calls land here, in sequence:
    //   1. POST /api/plans (materialises the plan via prepareAssignment).
    //   2. POST /api/assignments/bulk (cancels Alex's existing assignment
    //      via forceReplaceUserIds, then creates 3 fresh in-progress rows).
    // Plus a refetchUser per successful assignee. On a cold backend this
    // can run long, so wait for *any* banner heading first (all-success,
    // partial, or all-failure) with a generous timeout. That tells us the
    // request actually finished. Then assert specifically that all 3
    // succeeded — if it's a different heading, the error quotes the
    // actual text so we see whether it was a partial / DB_ERROR / etc.
    const anyBanner = dialog.getByText(
      /(?:Assigned \d+ users?\.|All \d+ failed\.|\d+ succeeded, \d+ failed\.)/,
    )
    await expect(anyBanner).toBeVisible({ timeout: 90_000 })
    await expect(dialog.getByText('Assigned 3 users.')).toBeVisible()

    // Done in the AssignNowPanel results phase → wizard advances to
    // its "All done" view → Close.
    await dialog.getByRole('button', { name: /^Done$/ }).click()
    await expect(dialog.getByText('All done.')).toBeVisible()
    // Two "Close" buttons exist in the dialog: the footer's primary Close
    // and shadcn's built-in `data-slot="dialog-close"` X icon (accessible
    // name "Close" via an sr-only span). The footer button comes first in
    // DOM order; `.first()` picks it deterministically.
    await dialog
      .getByRole('button', { name: /^Close$/ })
      .first()
      .click()
    await expect(dialog).toBeHidden()

    // ---- Assert: new plan in ActivePlansList ------------------------------
    // Two paths can add the row:
    //   - the optimistic ingest in AssignNowPanel.runAssignment (fires
    //     after `await Promise.all(refetchUser)` — adds 1–3s of network
    //     latency over a truly synchronous "store update"), and
    //   - the background `activePlansStore.refresh()` GET /api/plans/active
    //     (real DB query, slower but the safety net).
    // 30s covers either. If even refresh hasn't landed the row by then,
    // something is broken in the ingest — pull a trace to diagnose.
    const newRow = page.getByRole('button').filter({ hasText: planTitle })
    await expect(newRow).toBeVisible({ timeout: 90_000 })

    // Open ActivePlanDialog and assert all three assignees appear.
    await newRow.click()
    const detail = page.getByRole('dialog')
    await expect(detail).toBeVisible()
    // Each assignee's name appears in two places inside ActivePlanDialog:
    // the chip toolbar at the top (a <button>) and the per-assignee body
    // (e.g. an "Assigned by …" row). `.first()` picks one deterministically;
    // the assertion is just "name is rendered somewhere".
    await expect(detail.getByText('Sam Carter').first()).toBeVisible()
    await expect(detail.getByText('Lily Chen').first()).toBeVisible()
    await expect(detail.getByText('Alex Rodriguez').first()).toBeVisible()
  })
})
