import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'
import type { User } from '@/types/user'

const API_URL = import.meta.env.VITE_API_URL

export interface BulkAssignConflict {
  planTitle: string
}

export interface BulkAssignResult {
  userId: string
  success: boolean
  reason?: string
  assignmentId?: string
  conflictWith?: BulkAssignConflict
}

export const useUsersStore = defineStore('users', () => {
  const users = ref<User[]>([])
  const me = ref<User | null>(null)

  const activeUsers = computed(() => users.value.filter((u) => !u.removed && u.id !== me.value?.id))

  const manageableUsers = computed(() => users.value.filter((u) => u.id !== me.value?.id))

  const total = computed(() => activeUsers.value.length)

  const initUsers = (initialUsers: User[]) => {
    initialUsers.forEach((u) => {
      if (!users.value.find((uin) => uin.id === u.id)) {
        users.value.push(u)
      }
    })
  }

  const initMe = (user: User) => {
    me.value = user
  }

  const getById = (id: string) => users.value.find((u) => u.id === id)

  const getFullName = (id: string) => {
    const u = getById(id)
    return u ? `${u.firstName} ${u.lastName}` : ''
  }

  const updateUser = (id, updates) => {
    let updated
    users.value = users.value.map((u) => {
      if (u.id !== id) return u
      updated = { ...u, ...updates, id: u.id }
      return updated
    })
    if (me.value?.id === id) {
      updated = updated ?? { ...me.value, ...updates, id: me.value.id }
      me.value = updated
    }
    return updated
  }

  const deleteUser = (id: string) => {
    users.value = users.value.filter((u) => u.id !== id)
  }

  const markRemoved = (id: string) => {
    users.value = users.value.map((u) => (u.id === id ? { ...u, removed: true } : u))
  }

  const restoreUser = async (id: string): Promise<User | undefined> => {
    const res = await axios.post<User>(`${API_URL}/api/users/${id}/restore`)
    users.value = users.value.map((u) => (u.id === id ? res.data : u))
    if (me.value?.id === id) me.value = res.data
    return res.data
  }

  const refetchUser = async (id: string): Promise<User | undefined> => {
    const res = await axios.get<User>(`${API_URL}/api/users/${id}`)
    users.value = users.value.map((u) => (u.id === id ? res.data : u))
    if (me.value?.id === id) me.value = res.data
    return res.data
  }

  return {
    users,
    activeUsers,
    manageableUsers,
    total,
    me,
    initUsers,
    initMe,
    getById,
    getFullName,
    updateUser,
    deleteUser,
    markRemoved,
    restoreUser,
    refetchUser,
  }
})
