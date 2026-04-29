import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { Plan } from '@/types/plan'

export const usePlansStore = defineStore('plans', () => {
  const plans = ref<Plan[]>([])

  const visible = computed(() => plans.value.filter((p) => !p.archived))

  const initPlans = (input: Plan[]) => {
    plans.value = input
  }

  const getById = (id: string) => plans.value.find((p) => p.id === id)

  const titleExists = (title: string, excludeId?: string) =>
    plans.value.some((p) => p.title.toLowerCase() === title.toLowerCase() && p.id !== excludeId)

  const ingestPlan = (plan: Plan) => {
    const idx = plans.value.findIndex((p) => p.id === plan.id)
    if (idx >= 0) {
      const next = [...plans.value]
      next[idx] = plan
      plans.value = next
    } else {
      plans.value = [...plans.value, plan]
    }
  }

  const removePlan = (id: string) => {
    plans.value = plans.value.filter((p) => p.id !== id)
  }

  return {
    plans,
    visible,
    initPlans,
    getById,
    titleExists,
    ingestPlan,
    removePlan,
  }
})
