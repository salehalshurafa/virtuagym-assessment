/**
 * Unit tests for `useActivePlansStore`. Pure store-state mutations only —
 * no Vue mount, no axios beyond `refresh()` (which is mocked when used).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useActivePlansStore, type ActivePlanRow } from '@/stores/activePlans'

vi.mock('axios')

const makeRow = (overrides: Partial<ActivePlanRow> = {}): ActivePlanRow => ({
  id: 'plan-1',
  title: 'Strength Block',
  duration: 4,
  durationType: 'weeks',
  archived: false,
  userCount: 1,
  weeklyPlans: undefined,
  flatDays: undefined,
  assignees: [{ id: 'u1', firstName: 'Alex', lastName: 'Tester' }],
  statusSummary: 'in-progress',
  ...overrides,
})

describe('useActivePlansStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initActivePlans seeds items and flips initialised', () => {
    const store = useActivePlansStore()
    expect(store.initialised).toBe(false)

    store.initActivePlans([makeRow(), makeRow({ id: 'plan-2' })])

    expect(store.items).toHaveLength(2)
    expect(store.initialised).toBe(true)
  })

  it('ingestActivePlan patches by id (no duplicate on re-ingest)', () => {
    const store = useActivePlansStore()
    store.ingestActivePlan(makeRow({ title: 'Original' }))
    store.ingestActivePlan(makeRow({ title: 'Renamed' }))

    expect(store.items).toHaveLength(1)
    expect(store.items[0]!.title).toBe('Renamed')
  })

  it('ingestActivePlan appends when id is new', () => {
    const store = useActivePlansStore()
    store.ingestActivePlan(makeRow({ id: 'plan-1' }))
    store.ingestActivePlan(makeRow({ id: 'plan-2' }))

    expect(store.items.map((r) => r.id)).toEqual(['plan-1', 'plan-2'])
  })

  it('removeActivePlan drops by id and leaves others alone', () => {
    const store = useActivePlansStore()
    store.initActivePlans([makeRow({ id: 'a' }), makeRow({ id: 'b' }), makeRow({ id: 'c' })])
    store.removeActivePlan('b')

    expect(store.items.map((r) => r.id)).toEqual(['a', 'c'])
  })

  it('updateAssignee patches the assignee snapshot across every row that includes them', () => {
    const store = useActivePlansStore()
    store.initActivePlans([
      makeRow({
        id: 'plan-1',
        assignees: [
          { id: 'u1', firstName: 'Alex', lastName: 'Old' },
          { id: 'u2', firstName: 'Bea', lastName: 'Other' },
        ],
      }),
      makeRow({
        id: 'plan-2',
        assignees: [{ id: 'u1', firstName: 'Alex', lastName: 'Old' }],
      }),
      makeRow({ id: 'plan-3', assignees: [] }),
    ])

    store.updateAssignee('u1', { lastName: 'Renamed' })

    // Both rows that contained u1 reflect the update.
    expect(store.items[0]!.assignees[0]!.lastName).toBe('Renamed')
    expect(store.items[1]!.assignees[0]!.lastName).toBe('Renamed')
    // u2 untouched.
    expect(store.items[0]!.assignees[1]!.lastName).toBe('Other')
  })

  it('removeAssignee drops the user from every row and prunes plans that empty out', () => {
    const store = useActivePlansStore()
    store.initActivePlans([
      makeRow({
        id: 'shared',
        assignees: [
          { id: 'u1', firstName: 'Alex', lastName: 'A' },
          { id: 'u2', firstName: 'Bea', lastName: 'B' },
        ],
      }),
      makeRow({
        id: 'solo',
        assignees: [{ id: 'u1', firstName: 'Alex', lastName: 'A' }],
      }),
      makeRow({
        id: 'untouched',
        assignees: [{ id: 'u3', firstName: 'Cleo', lastName: 'C' }],
      }),
    ])

    store.removeAssignee('u1')

    // Shared plan keeps Bea, solo plan is pruned, untouched plan stays.
    expect(store.items.map((r) => r.id)).toEqual(['shared', 'untouched'])
    expect(store.items[0]!.assignees.map((a) => a.id)).toEqual(['u2'])
  })
})
