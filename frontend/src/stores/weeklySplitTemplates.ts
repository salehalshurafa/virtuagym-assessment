import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { WeeklySplitTemplate } from '@/types/template'

export const useWeeklySplitTemplatesStore = defineStore('weeklySplitTemplates', () => {
  const items = ref<WeeklySplitTemplate[]>([])

  const templates = computed(() => items.value)

  const initTemplates = (input: WeeklySplitTemplate[]) => {
    items.value = input
  }

  const getById = (id: string) => items.value.find((t) => t.id === id)

  const labelExists = (label: string, excludeId?: string) =>
    items.value.some((t) => t.label.toLowerCase() === label.toLowerCase() && t.id !== excludeId)

  const ingestTemplate = (template: WeeklySplitTemplate) => {
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
    labelExists,
    ingestTemplate,
    removeTemplate,
  }
})
