import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'
import type { Plan } from '@/types/plan'
import type { PlanStatus } from '@/types/user'

const API_URL = import.meta.env.VITE_API_URL

export interface ActivePlanAssignee {
  id: string
  firstName: string
  lastName: string
}

export interface ActivePlanRow extends Plan {
  assignees: ActivePlanAssignee[]
  statusSummary: PlanStatus | 'mixed'
}

export const useActivePlansStore = defineStore('activePlans', () => {
  const items = ref<ActivePlanRow[]>([])
  const loading = ref(false)
  const loadError = ref<string | null>(null)
  const initialised = ref(false)

  const refresh = async (): Promise<ActivePlanRow[] | null> => {
    loading.value = true
    loadError.value = null
    try {
      const res = await axios.get<ActivePlanRow[]>(`${API_URL}/api/plans/active`)
      items.value = res.data
      initialised.value = true
      return res.data
    } catch (err) {
      console.error('failed to load active plans', err)
      loadError.value = "We couldn't load active plans right now."
      return null
    } finally {
      loading.value = false
    }
  }

  const initActivePlans = (input: ActivePlanRow[]) => {
    items.value = input
    initialised.value = true
  }

  const ingestActivePlan = (row: ActivePlanRow) => {
    const idx = items.value.findIndex((r) => r.id === row.id)
    if (idx >= 0) {
      const next = [...items.value]
      next[idx] = row
      items.value = next
    } else {
      items.value = [...items.value, row]
    }
  }

  const removeActivePlan = (id: string) => {
    items.value = items.value.filter((r) => r.id !== id)
  }

  const updateAssignee = (
    userId: string,
    updates: Partial<Pick<ActivePlanAssignee, 'firstName' | 'lastName'>>,
  ) => {
    let touched = false
    const next = items.value.map((row) => {
      const idx = row.assignees.findIndex((a) => a.id === userId)
      if (idx < 0) return row

      const existing = row.assignees[idx]!
      touched = true
      const newAssignees = [...row.assignees]
      newAssignees[idx] = { ...existing, ...updates }
      return { ...row, assignees: newAssignees }
    })
    if (touched) items.value = next
  }

  const removeAssignee = (userId: string) => {
    const next: ActivePlanRow[] = []
    let touched = false
    for (const row of items.value) {
      if (!row.assignees.some((a) => a.id === userId)) {
        next.push(row)
        continue
      }
      touched = true
      const remaining = row.assignees.filter((a) => a.id !== userId)
      if (remaining.length > 0) {
        next.push({ ...row, assignees: remaining })
      }
    }
    if (touched) items.value = next
  }

  return {
    items,
    loading,
    loadError,
    initialised,
    refresh,
    initActivePlans,
    ingestActivePlan,
    removeActivePlan,
    updateAssignee,
    removeAssignee,
  }
})
