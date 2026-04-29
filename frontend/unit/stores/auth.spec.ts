/**
 * Unit tests for `useAuthStore`. Exercises the cookie-backed auth flow
 * with a mocked axios — the store doesn't see cookies directly (HttpOnly),
 * it just trusts the success/failure of the underlying request and mirrors
 * the `me` value into Pinia.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types/user'

vi.mock('axios')

const me: User = {
  id: 'admin',
  firstName: 'Fake',
  lastName: 'Admin',
  email: 'fakeadmin@example.com',
  timezone: 'Europe/Amsterdam',
}

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('isAuthenticated is false until `me` is populated', () => {
    const auth = useAuthStore()
    expect(auth.me).toBeNull()
    expect(auth.isAuthenticated).toBe(false)
  })

  it('login posts credentials and stores `me` on success', async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data: me } as never)
    const auth = useAuthStore()

    const result = await auth.login({ email: me.email, password: 'ChangeMe!23' })

    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/api/auth/login'), {
      email: me.email,
      password: 'ChangeMe!23',
    })
    expect(result).toEqual(me)
    expect(auth.me).toEqual(me)
    expect(auth.isAuthenticated).toBe(true)
  })

  it('login propagates the rejection so callers can render the error', async () => {
    const err = Object.assign(new Error('boom'), { response: { status: 401 } })
    vi.mocked(axios.post).mockRejectedValueOnce(err)
    const auth = useAuthStore()

    await expect(auth.login({ email: 'nope@x.example', password: 'wrong' })).rejects.toBe(err)
    expect(auth.me).toBeNull()
  })

  it('bootstrap populates `me` from /api/auth/me on success', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: me } as never)
    const auth = useAuthStore()

    const result = await auth.bootstrap()

    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/api/auth/me'))
    expect(result).toEqual(me)
    expect(auth.me).toEqual(me)
    expect(auth.bootstrapAttempted).toBe(true)
  })

  it('bootstrap leaves `me` null on 401, still flips bootstrapAttempted', async () => {
    vi.mocked(axios.get).mockRejectedValueOnce(
      Object.assign(new Error('401'), { response: { status: 401 } }),
    )
    const auth = useAuthStore()

    const result = await auth.bootstrap()

    expect(result).toBeNull()
    expect(auth.me).toBeNull()
    expect(auth.bootstrapAttempted).toBe(true)
  })

  it('logout clears `me` even if the network call fails', async () => {
    const auth = useAuthStore()
    auth.me = { ...me }
    vi.mocked(axios.post).mockRejectedValueOnce(new Error('network down'))

    await auth.logout()

    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/api/auth/logout'))
    expect(auth.me).toBeNull()
  })

  it('patchMe merges updates into the current `me`', () => {
    const auth = useAuthStore()
    auth.me = { ...me }

    auth.patchMe({ firstName: 'Renamed' })

    expect(auth.me?.firstName).toBe('Renamed')
    expect(auth.me?.email).toBe(me.email) // untouched fields preserved
  })

  it('patchMe does nothing when `me` is null (logged-out edge case)', () => {
    const auth = useAuthStore()
    auth.me = null

    auth.patchMe({ firstName: 'Renamed' })

    expect(auth.me).toBeNull()
  })

  it('browserTimezone returns the Intl-resolved zone or undefined on failure', () => {
    const auth = useAuthStore()
    const tz = auth.browserTimezone()
    // jsdom sets a real timezone string; either way it must be a non-empty string or undefined.
    expect(tz === undefined || (typeof tz === 'string' && tz.length > 0)).toBe(true)
  })
})
