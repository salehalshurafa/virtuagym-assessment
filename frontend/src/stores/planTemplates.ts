import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { PlanTemplate } from '@/types/template'

export const usePlanTemplatesStore = defineStore('planTemplates', () => {
  const items = ref<PlanTemplate[]>([])

  const templates = computed(() => items.value.filter((t) => !t.archived))

  const initTemplates = (input: PlanTemplate[]) => {
    items.value = input
  }

  const getById = (id: string) => items.value.find((t) => t.id === id)

  const titleExists = (title: string, excludeId?: string) =>
    items.value.some((t) => t.title.toLowerCase() === title.toLowerCase() && t.id !== excludeId)

  const ingestTemplate = (template: PlanTemplate) => {
    const idx = items.value.findIndex((t) => t.id === template.id)
    if (idx >= 0) {
      const next = [...items.value]
      next[idx] = template
      items.value = next
    } else {
      items.value = [...items.value, template]
    }
  }

  const removeTemplate = (id: string) => {
    items.value = items.value.filter((t) => t.id !== id)
  }

  return {
    items,
    templates,
    initTemplates,
    getById,
    titleExists,
    ingestTemplate,
    removeTemplate,
  }
})
