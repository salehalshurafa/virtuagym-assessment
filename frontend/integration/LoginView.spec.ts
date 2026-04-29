/**
 * Integration test for LoginView.vue.
 *
 * vue-router is mocked so we can assert on `router.replace` calls without
 * mounting a real router. The auth store is real (Pinia) and `auth.login`
 * is the integration boundary — we mock axios under it.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import axios from 'axios'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

vi.mock('axios')

// vue-router stub. We need ``useRouter()`` to return an object with a
// ``replace`` spy and a ``currentRoute`` ref-like value.
const replaceSpy = vi.fn()
const currentRoute = { value: { query: {} as Record<string, string> } }
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: replaceSpy, currentRoute }),
  RouterLink: { template: '<a><slot /></a>' },
}))

const mountLogin = (): VueWrapper => {
  return mount(LoginView, {
    global: {
      plugins: [createTestingPinia({ stubActions: false, createSpy: vi.fn })],
    },
  })
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentRoute.value.query = {}
  })

  it('successful login calls auth.login and redirects to "/"', async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({
      data: {
        id: 'admin',
        firstName: 'Fake',
        lastName: 'Admin',
        email: 'fakeadmin@example.com',
        timezone: 'UTC',
      },
    } as never)

    const wrapper = mountLogin()
    await wrapper.find('#email').setValue('fakeadmin@example.com')
    await wrapper.find('#password').setValue('ChangeMe!23')
    await wrapper.find('form').trigger('submit.prevent')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    // Login POST hit the auth endpoint.
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/api/auth/login'), {
      email: 'fakeadmin@example.com',
      password: 'ChangeMe!23',
    })
    // Auth store reflects the logged-in user.
    expect(useAuthStore().me).toMatchObject({ email: 'fakeadmin@example.com' })
    // Router was asked to navigate home.
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })

  it('honors a ?redirect=/some/path query when redirecting after login', async () => {
    currentRoute.value.query = { redirect: '/dashboard/users' }
    vi.mocked(axios.post).mockResolvedValueOnce({
      data: {
        id: 'admin',
        firstName: 'Fake',
        lastName: 'Admin',
        email: 'fakeadmin@example.com',
        timezone: 'UTC',
      },
    } as never)

    const wrapper = mountLogin()
    await wrapper.find('#email').setValue('fakeadmin@example.com')
    await wrapper.find('#password').setValue('ChangeMe!23')
    await wrapper.find('form').trigger('submit.prevent')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(replaceSpy).toHaveBeenCalledWith('/dashboard/users')
  })

  it('shows the right inline error on a 401', async () => {
    vi.mocked(axios.isAxiosError).mockReturnValue(true)
    vi.mocked(axios.post).mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 401 },
    })

    const wrapper = mountLogin()
    await wrapper.find('#email').setValue('fakeadmin@example.com')
    await wrapper.find('#password').setValue('definitely-wrong')
    await wrapper.find('form').trigger('submit.prevent')
    // The rejection chain (axios.post → auth.login → onSubmit's catch
    // → finally that flips submitting=false) takes several microtasks;
    // flushPromises drains all pending ones at once.
    await flushPromises()

    expect(wrapper.text()).toContain('Invalid email or password.')
    // No redirect on failure.
    expect(replaceSpy).not.toHaveBeenCalled()
    // Auth store still shows logged-out.
    expect(useAuthStore().me).toBeNull()
  })

  it('shows a generic error on non-401 failures (e.g. network down)', async () => {
    vi.mocked(axios.isAxiosError).mockReturnValue(false)
    vi.mocked(axios.post).mockRejectedValueOnce(new Error('network down'))

    const wrapper = mountLogin()
    await wrapper.find('#email').setValue('fakeadmin@example.com')
    await wrapper.find('#password').setValue('ChangeMe!23')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain("Couldn't sign you in. Please try again.")
    expect(replaceSpy).not.toHaveBeenCalled()
  })

  it('blocks submit and shows an inline error when fields are empty', async () => {
    const wrapper = mountLogin()
    await wrapper.find('form').trigger('submit.prevent')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Email and password are required.')
    expect(axios.post).not.toHaveBeenCalled()
    expect(replaceSpy).not.toHaveBeenCalled()
  })
})
