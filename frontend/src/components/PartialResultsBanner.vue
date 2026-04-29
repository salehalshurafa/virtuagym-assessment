<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle2, XCircle } from 'lucide-vue-next'

export interface ResultRow {
  label: string
  success: boolean
  detail?: string
}

const props = defineProps<{
  results: ResultRow[]
  successHeading?: string
  failureHeading?: string
}>()

const successes = computed(() => props.results.filter((r) => r.success))
const failures = computed(() => props.results.filter((r) => !r.success))

const tone = computed(() => {
  if (failures.value.length === 0) return 'all-success'
  if (successes.value.length === 0) return 'all-failure'
  return 'partial'
})

const banner = computed(() => {
  switch (tone.value) {
    case 'all-success':
      return {
        cls: 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200',
        title: props.successHeading ?? `All ${props.results.length} succeeded.`,
      }
    case 'all-failure':
      return {
        cls: 'border-rose-500/60 bg-rose-600/10 text-rose-200',
        title: props.failureHeading ?? `All ${props.results.length} failed.`,
      }
    default:
      return {
        cls: 'border-amber-500/60 bg-amber-500/10 text-amber-200',
        title: `${successes.value.length} succeeded, ${failures.value.length} failed.`,
      }
  }
})
</script>

<template>
  <div class="flex flex-col gap-3 rounded-md border-2 px-4 py-3" :class="banner.cls">
    <p class="text-sm font-medium">{{ banner.title }}</p>

    <ul v-if="successes.length" class="flex flex-col gap-1">
      <li
        v-for="(row, i) in successes"
        :key="`s-${i}`"
        class="flex items-center gap-2 text-xs text-emerald-200"
      >
        <CheckCircle2 class="h-3.5 w-3.5 shrink-0" />
        <span class="truncate">{{ row.label }}</span>
        <span v-if="row.detail" class="text-[10px] text-emerald-300/70">— {{ row.detail }}</span>
      </li>
    </ul>

    <ul v-if="failures.length" class="flex flex-col gap-1">
      <li
        v-for="(row, i) in failures"
        :key="`f-${i}`"
        class="flex items-center gap-2 text-xs text-rose-200"
      >
        <XCircle class="h-3.5 w-3.5 shrink-0" />
        <span class="truncate">{{ row.label }}</span>
        <span v-if="row.detail" class="text-[10px] text-rose-300/70">— {{ row.detail }}</span>
      </li>
    </ul>
  </div>
</template>
