import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'
import type { Gender, User } from '@/types/user'

const API_BASE = import.meta.env.VITE_API_URL

export interface SignupPayload {
  firstName: string
  lastName: string
  email: string
  password: string
  timezone?: string
  gender?: Gender | null
  phoneNumber?: string | null
}

export interface LoginPayload {
  email: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const me = ref<User | null>(null)
  const loading = ref(false)
  const bootstrapAttempted = ref(false)

  const isAuthenticated = computed(() => me.value !== null)

  const browserTimezone = (): string | undefined => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone
    } catch {
      return undefined
    }
  }

  const bootstrap = async (): Promise<User | null> => {
    if (loading.value) return me.value
    loading.value = true
    try {
      const res = await axios.get<User>(`${API_BASE}/api/auth/me`)
      me.value = res.data
      return res.data
    } catch {
      me.value = null
      return null
    } finally {
      loading.value = false
      bootstrapAttempted.value = true
    }
  }

  const login = async (payload: LoginPayload): Promise<User> => {
    const res = await axios.post<User>(`${API_BASE}/api/auth/login`, payload)
    me.value = res.data
    return res.data
  }

  const signup = async (payload: SignupPayload): Promise<User> => {
    const body: SignupPayload = {
      ...payload,
      timezone: payload.timezone ?? browserTimezone(),
    }
    const res = await axios.post<User>(`${API_BASE}/api/auth/signup`, body)
    me.value = res.data
    return res.data
  }

  const logout = async (): Promise<void> => {
    try {
      await axios.post(`${API_BASE}/api/auth/logout`)
    } catch {}
    me.value = null
  }

  const patchMe = (updates: Partial<User>): void => {
    if (me.value) {
      me.value = { ...me.value, ...updates }
    }
  }

  return {
    me,
    loading,
    bootstrapAttempted,
    isAuthenticated,
    bootstrap,
    login,
    signup,
    logout,
    patchMe,
    browserTimezone,
  }
})
