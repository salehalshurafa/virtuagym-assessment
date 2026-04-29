/**
 * Integration test for ActivePlansList.vue.
 *
 * Pinia is real (via `createTestingPinia({ stubActions: false })`),
 * children that would pull in network or portal-rendered DOM are
 * stubbed — we're testing this component's render logic in isolation.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { useActivePlansStore, type ActivePlanRow } from '@/stores/activePlans'
import ActivePlansList from '@/components/ActivePlansList.vue'

vi.mock('axios')

const stubs = {
  ActivePlanDialog: true,
  AssignPlansDialog: true,
  ModifyUserPlanDialog: true,
}

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

const mountList = (rows: ActivePlanRow[] = []): VueWrapper => {
  const wrapper = mount(ActivePlansList, {
    global: {
      plugins: [
        createTestingPinia({
          stubActions: false, // let real store actions run; we want filter/render logic
          createSpy: vi.fn,
        }),
      ],
      stubs,
    },
  })
  // Seed the store after mount so initialised flips on and the skeleton is hidden.
  if (rows.length > 0) {
    useActivePlansStore().initActivePlans(rows)
  }
  return wrapper
}

describe('ActivePlansList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders one row per active plan with title and assignee preview', async () => {
    const wrapper = mountList([
      makeRow({
        id: 'plan-1',
        title: 'Strength Block',
        assignees: [
          { id: 'u1', firstName: 'Alex', lastName: 'Tester' },
          { id: 'u2', firstName: 'Eve', lastName: 'Other' },
        ],
      }),
      makeRow({
        id: 'plan-2',
        title: 'Endurance Block',
        assignees: [{ id: 'u3', firstName: 'Sam', lastName: 'Carter' }],
      }),
    ])
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Strength Block')
    expect(text).toContain('Endurance Block')
    expect(text).toContain('Alex Tester')
    expect(text).toContain('Sam Carter')
  })

  it('shows the empty state when there are no active plans', async () => {
    const wrapper = mountList([])

    useActivePlansStore().initActivePlans([])
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('No plans are currently assigned to anyone.')
  })

  it('search filter narrows the visible rows by title (case-insensitive)', async () => {
    const wrapper = mountList([
      makeRow({ id: 'a', title: 'Strength Block' }),
      makeRow({ id: 'b', title: 'Endurance Block' }),
      makeRow({ id: 'c', title: 'Strength Plus' }),
    ])
    await wrapper.vm.$nextTick()

    const search = wrapper.find('input[aria-label="Search active plans"]')
    await search.setValue('strength')

    const text = wrapper.text()
    expect(text).toContain('Strength Block')
    expect(text).toContain('Strength Plus')
    expect(text).not.toContain('Endurance Block')
  })

  it('status filter shows only rows whose statusSummary matches', async () => {
    const wrapper = mountList([
      makeRow({ id: 'a', title: 'In Progress One', statusSummary: 'in-progress' }),
      makeRow({ id: 'b', title: 'Paused One', statusSummary: 'paused' }),
      makeRow({ id: 'c', title: 'Mixed One', statusSummary: 'mixed' }),
    ])
    await wrapper.vm.$nextTick()

    await wrapper.find('select[aria-label="Filter by status"]').setValue('paused')

    const text = wrapper.text()
    expect(text).toContain('Paused One')
    expect(text).not.toContain('In Progress One')
    expect(text).not.toContain('Mixed One')
  })

  it('shows the no-match message when filters exclude every row', async () => {
    const wrapper = mountList([makeRow({ id: 'a', title: 'Strength Block' })])
    await wrapper.vm.$nextTick()

    await wrapper.find('input[aria-label="Search active plans"]').setValue('nope-no-match')

    expect(wrapper.text()).toContain('No active plans match your filters.')
  })
})
