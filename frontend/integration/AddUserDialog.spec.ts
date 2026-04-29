/**
 * Integration test for AddUserDialog.vue.
 *
 * Pinia is real (with stubActions=false so initUsers etc. run), axios is
 * mocked, and shadcn dialog primitives that portal-render are stubbed
 * out so jsdom can drive the form.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import axios from 'axios'
import AddUserDialog from '@/components/AddUserDialog.vue'
import { useUsersStore } from '@/stores/users'
import type { User } from '@/types/user'

vi.mock('axios')

// shadcn-vue's Dialog portals into <body>; in jsdom we want it inline so we
// can drive its form. Replace the wrapping primitives with transparent
// passthroughs so the slot content (form + buttons) renders directly.
const stubs = {
  Dialog: { template: '<div><slot /></div>' },
  DialogTrigger: { template: '<div><slot /></div>' },
  DialogContent: { template: '<div role="dialog"><slot /></div>' },
  DialogHeader: { template: '<div><slot /></div>' },
  DialogTitle: { template: '<h2><slot /></h2>' },
  TimezoneSelect: {
    props: ['modelValue'],
    template: '<input data-test="tz" :value="modelValue" />',
  },
}

const makeUserResponse = (email: string): User => ({
  id: 'newly-created',
  firstName: 'Eve',
  lastName: 'Invited',
  email,
  timezone: 'Europe/Amsterdam',
})

const mountDialog = (): VueWrapper => {
  return mount(AddUserDialog, {
    global: {
      plugins: [createTestingPinia({ stubActions: false, createSpy: vi.fn })],
      stubs,
    },
  })
}

describe('AddUserDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the form payload and ingests the response into the users store', async () => {
    const wrapper = mountDialog()
    const email = `eve_${Date.now()}@test.example`
    const created = makeUserResponse(email)
    vi.mocked(axios.post).mockResolvedValueOnce({ data: created } as never)

    await wrapper.find('#add-user-first').setValue('Eve')
    await wrapper.find('#add-user-last').setValue('Invited')
    await wrapper.find('#add-user-email').setValue(email)

    await wrapper.find('button.bg-\\[\\#ff6f14\\]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    // axios.post was called against /api/users with the form fields. The
    // password is generated client-side, so we assert on shape rather than
    // a fixed string.
    expect(axios.post).toHaveBeenCalledTimes(1)
    const [url, body] = vi.mocked(axios.post).mock.calls[0]!
    expect(url).toContain('/api/users')
    expect(body).toMatchObject({
      firstName: 'Eve',
      lastName: 'Invited',
      email,
    })
    expect((body as { password: string }).password.length).toBeGreaterThan(0)

    // Store ingested the response.
    expect(useUsersStore().users.find((u) => u.id === 'newly-created')).toBeTruthy()
  })

  it('surfaces a 409 (duplicate email) as an inline error and does NOT advance to success', async () => {
    const wrapper = mountDialog()
    vi.mocked(axios.post).mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 409 },
    })
    // ``axios.isAxiosError`` is a static helper the component checks against
    // the rejection. Make it return true for our mocked rejection.
    vi.mocked(axios.isAxiosError).mockReturnValue(true)

    await wrapper.find('#add-user-first').setValue('Eve')
    await wrapper.find('#add-user-last').setValue('Invited')
    await wrapper.find('#add-user-email').setValue('eve@test.example')

    await wrapper.find('button.bg-\\[\\#ff6f14\\]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('A user with that email already exists.')
    // No success-phase password reveal.
    expect(wrapper.text()).not.toContain('User created')
  })

  it('flips to the success phase showing the temp password after a successful create', async () => {
    const wrapper = mountDialog()
    const created = makeUserResponse('fresh@test.example')
    vi.mocked(axios.post).mockResolvedValueOnce({ data: created } as never)

    await wrapper.find('#add-user-first').setValue('Eve')
    await wrapper.find('#add-user-last').setValue('Invited')
    await wrapper.find('#add-user-email').setValue('fresh@test.example')

    await wrapper.find('button.bg-\\[\\#ff6f14\\]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('User created')
    // The temp password is rendered inside a <code> block; just check the
    // copy affordance is visible.
    expect(wrapper.text()).toContain('Copy')
    expect(wrapper.find('code').exists()).toBe(true)
    expect(wrapper.find('code').text().length).toBeGreaterThan(0)
  })

  it('emits "created" with the new user when the POST succeeds', async () => {
    const wrapper = mountDialog()
    const created = makeUserResponse('emit@test.example')
    vi.mocked(axios.post).mockResolvedValueOnce({ data: created } as never)

    await wrapper.find('#add-user-first').setValue('Eve')
    await wrapper.find('#add-user-last').setValue('Invited')
    await wrapper.find('#add-user-email').setValue('emit@test.example')
    await wrapper.find('button.bg-\\[\\#ff6f14\\]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const events = wrapper.emitted('created')
    expect(events).toBeTruthy()
    expect(events![0]![0]).toMatchObject({ id: 'newly-created' })
  })
})
