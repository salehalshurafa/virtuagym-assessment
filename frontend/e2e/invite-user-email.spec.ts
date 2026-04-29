import { expect, test, type APIRequestContext } from '@playwright/test'

/**
 * E2E Scenario 2 from SESSION_FOLLOWUP_3.md §8.2 — Admin invites a new
 * user; welcome email arrives in Mailpit.
 *
 * Drives the AddUserDialog from the UsersList header, then asserts that
 * the backend's `Mailer.send_user_account_created` actually delivered an
 * email by querying Mailpit's HTTP API.
 *
 * Pre-conditions:
 *  - Backend + frontend running, seeded.
 *  - Backend `.env` has `EMAILS_ENABLED=true` and `SMTP_HOST` pointed
 *    at a Mailpit instance (per SESSION_FOLLOWUP.md §3.2).
 *  - Mailpit reachable at MAILPIT_URL (defaults to http://localhost:8025
 *    for local development; set the env var when Mailpit is on the GCP VM).
 *
 * Re-runnable: every run uses a unique email so no 409 collision in the
 * users table, and Mailpit accumulates without conflict (we filter by
 * recipient email when verifying).
 */

const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:8025'

interface MailpitMessageSummary {
  ID: string
  To: { Address: string; Name: string }[]
  From: { Address: string; Name: string }
  Subject: string
}

interface MailpitMessage extends MailpitMessageSummary {
  HTML: string
  Text: string
}

interface MailpitListResponse {
  messages: MailpitMessageSummary[]
  total: number
  unread: number
  count: number
}

/**
 * Poll Mailpit until at least one message addressed to ``recipient`` is
 * found, then return its full body. Throws when the timeout elapses.
 *
 * Mailpit's `/api/v1/messages` lists the most-recent first, summary only.
 * `/api/v1/message/{ID}` returns the full message including HTML + Text.
 */
const waitForMailTo = async (
  request: APIRequestContext,
  recipient: string,
  timeoutMs = 15_000,
): Promise<MailpitMessage> => {
  const deadline = Date.now() + timeoutMs
  let lastErr: Error | null = null
  while (Date.now() < deadline) {
    try {
      const listRes = await request.get(`${MAILPIT_URL}/api/v1/messages?limit=50`)
      if (!listRes.ok()) throw new Error(`mailpit list ${listRes.status()}`)
      const list = (await listRes.json()) as MailpitListResponse
      const match = list.messages.find((m) =>
        m.To.some((t) => t.Address.toLowerCase() === recipient.toLowerCase()),
      )
      if (match) {
        const detailRes = await request.get(`${MAILPIT_URL}/api/v1/message/${match.ID}`)
        if (!detailRes.ok()) throw new Error(`mailpit detail ${detailRes.status()}`)
        return (await detailRes.json()) as MailpitMessage
      }
    } catch (err) {
      lastErr = err as Error
    }
    await new Promise((r) => setTimeout(r, 500))
  }
  throw new Error(
    `No Mailpit message addressed to ${recipient} within ${timeoutMs}ms (last err: ${lastErr?.message ?? 'none'})`,
  )
}

test.describe('Admin invites a new user → welcome email arrives', () => {
  // Per-test budget. The default in playwright.config.ts (30s) is tight:
  // login + dashboard bootstrap + Mailpit polling can chew through it on
  // a cold backend. 60s gives all three phases breathing room.
  test.setTimeout(60_000)

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies()
    await page.goto('/login')
    await page.getByLabel('Email').fill('fakeadmin@example.com')
    await page.getByLabel('Password').fill('ChangeMe!23')
    await page.getByRole('button', { name: /sign in/i }).click()
    // Login POST + cookie + router push + bootstrap race past the
    // default 5s expect.timeout from playwright.config.ts.
    await expect(page).toHaveURL('/', { timeout: 15_000 })
  })

  test('AddUserDialog → Mailpit receives a welcome email mentioning the admin', async ({
    page,
    request,
  }) => {
    const stamp = Date.now()
    const inviteEmail = `e2e_invite_${stamp}@test.example`
    const inviteFirstName = 'Eve'
    const inviteLastName = 'Invited'

    // Sanity-ping Mailpit before driving the UI — better to fail fast with
    // a clear message than to time out at the assertion below.
    const ping = await request.get(`${MAILPIT_URL}/api/v1/info`)
    expect(
      ping.ok(),
      `Mailpit not reachable at ${MAILPIT_URL}. Set MAILPIT_URL or start Mailpit (docker compose up -d mailpit).`,
    ).toBeTruthy()

    // Open AddUserDialog from the UsersList header. The whole dashboard
    // (HomeView) is gated behind App.vue's `v-if="isBootstrapping"` until
    // the parallel store loads finish, so wait for the actual button we
    // need rather than a sibling heading — same gate, more honest target.
    const addUserBtn = page.getByRole('button', { name: /add user/i })
    await expect(addUserBtn).toBeVisible({ timeout: 25_000 })
    await addUserBtn.click()

    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('heading', { name: 'Add user' })).toBeVisible()

    // Fill the form. Timezone defaults to the detected browser zone, so
    // we leave it; gender + phone are optional, fill them to exercise the
    // full payload path.
    await dialog.getByLabel('First name').fill(inviteFirstName)
    await dialog.getByLabel('Last name').fill(inviteLastName)
    await dialog.getByLabel('Email').fill(inviteEmail)
    await dialog.getByRole('button', { name: 'female', exact: true }).click()
    await dialog.getByLabel('Phone number').fill('+31 6 9999 0000')

    await dialog.getByRole('button', { name: /create user/i }).click()

    // Success phase — title flips to "User created" and the temp password
    // is revealed exactly once for the admin to copy out-of-band.
    await expect(dialog.getByRole('heading', { name: 'User created' })).toBeVisible({
      timeout: 10_000,
    })
    await expect(dialog.getByRole('button', { name: /^Copy$/ })).toBeVisible()

    // Dismiss the success dialog.
    await dialog.getByRole('button', { name: /^Done$/ }).click()
    await expect(dialog).toBeHidden()

    // ---- Mailpit assertion ------------------------------------------------
    const message = await waitForMailTo(request, inviteEmail)

    // Subject — mention the product. The exact wording is mailer-specific;
    // we look for "Virtuagym" rather than over-pinning the copy.
    expect(message.Subject).toMatch(/virtuagym/i)

    // Body — must mention the inviter (Fake Admin) somewhere, plus point the
    // recipient at the admin to obtain their password (not embed it).
    const body = `${message.HTML}\n${message.Text}`
    expect(body, 'welcome email should mention the admin who created the account').toMatch(
      /Fake\s*Admin/i,
    )
    expect(
      body,
      'welcome email should reference the admin email (or "your admin") so the user knows who to ask',
    ).toMatch(/fakeadmin@example\.com|admin/i)
    expect(
      body,
      'welcome email must NOT contain the temp password — security regression if it does',
    ).not.toMatch(/password\s*[:=]\s*\S{8,}/i)
  })
})
