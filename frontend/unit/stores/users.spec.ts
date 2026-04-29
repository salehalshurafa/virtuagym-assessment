/**
 * Unit tests for `useUsersStore`. Pure store-state mutations + the
 * computed views (`activeUsers`, `manageableUsers`).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
import { useUsersStore } from '@/stores/users'
import type { User } from '@/types/user'

vi.mock('axios')

const makeUser = (overrides: Partial<User> = {}): User => ({
  id: 'u1',
  firstName: 'Alex',
  lastName: 'Tester',
  email: 'alex@test.example',
  timezone: 'UTC',
  ...overrides,
})

describe('useUsersStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('updateUser patches an existing row and returns the new value', () => {
    const store = useUsersStore()
    store.initUsers([makeUser({ firstName: 'Alex' })])

    const updated = store.updateUser('u1', { firstName: 'Renamed' })

    expect(updated?.firstName).toBe('Renamed')
    expect(store.users[0]!.firstName).toBe('Renamed')
    // Identity preserved — id never overwritten by spread.
    expect(store.users[0]!.id).toBe('u1')
  })

  it('updateUser also patches `me` when ids match', () => {
    const store = useUsersStore()
    const me = makeUser({ id: 'me-id', firstName: 'Self' })
    store.initUsers([me])
    store.initMe(me)

    store.updateUser('me-id', { firstName: 'NewSelf' })

    expect(store.me?.firstName).toBe('NewSelf')
  })

  it('markRemoved flips `removed` locally without dropping the row', () => {
    const store = useUsersStore()
    store.initUsers([makeUser({ id: 'u1' }), makeUser({ id: 'u2' })])

    store.markRemoved('u1')

    expect(store.users).toHaveLength(2)
    expect(store.users.find((u) => u.id === 'u1')?.removed).toBe(true)
    expect(store.users.find((u) => u.id === 'u2')?.removed).toBeUndefined()
  })

  it('activeUsers computed excludes removed and current user', () => {
    const store = useUsersStore()
    const me = makeUser({ id: 'me' })
    store.initUsers([
      me,
      makeUser({ id: 'u1' }),
      makeUser({ id: 'u2', removed: true }),
      makeUser({ id: 'u3' }),
    ])
    store.initMe(me)

    expect(store.activeUsers.map((u) => u.id)).toEqual(['u1', 'u3'])
  })

  it('manageableUsers includes removed users but still excludes self', () => {
    const store = useUsersStore()
    const me = makeUser({ id: 'me' })
    store.initUsers([me, makeUser({ id: 'u1' }), makeUser({ id: 'u2', removed: true })])
    store.initMe(me)

    expect(store.manageableUsers.map((u) => u.id)).toEqual(['u1', 'u2'])
  })

  it('refetchUser GETs /api/users/{id} and replaces the local row', async () => {
    const store = useUsersStore()
    store.initUsers([makeUser({ id: 'u1', firstName: 'StaleName' })])

    const fresh = makeUser({ id: 'u1', firstName: 'FreshName' })
    vi.mocked(axios.get).mockResolvedValueOnce({ data: fresh } as never)

    const result = await store.refetchUser('u1')

    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/api/users/u1'))
    expect(result?.firstName).toBe('FreshName')
    expect(store.users[0]!.firstName).toBe('FreshName')
  })

  it('restoreUser POSTs /restore and clears the removed flag locally', async () => {
    const store = useUsersStore()
    const removed = makeUser({ id: 'u1', removed: true })
    store.initUsers([removed])

    const restored = makeUser({ id: 'u1', removed: undefined })
    vi.mocked(axios.post).mockResolvedValueOnce({ data: restored } as never)

    const result = await store.restoreUser('u1')

    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/api/users/u1/restore'))
    expect(result?.removed).toBeUndefined()
    expect(store.users[0]!.removed).toBeUndefined()
  })
})
