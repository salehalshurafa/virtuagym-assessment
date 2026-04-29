<script setup lang="ts">
import { computed } from 'vue'
import { Input } from '@/components/ui/input'
import DayCard from '@/components/plan-form/DayCard.vue'
import type { PlanDay } from '@/types/plan'

const props = defineProps<{
  label: string
  days: PlanDay[]
}>()

const emit = defineEmits<{
  'update:label': [value: string]
}>()

const labelModel = computed<string>({
  get: () => props.label,
  set: (value) => emit('update:label', value),
})
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-col gap-1">
      <label class="text-xs font-semibold uppercase text-[#a0a09a]">Template name</label>
      <Input
        v-model="labelModel"
        placeholder="e.g. Push / Pull / Legs"
        aria-label="Template name"
        class="bg-[#2a2a28] border-[#3a3a37] text-white"
      />
    </div>
    <div class="flex flex-col gap-2">
      <DayCard
        v-for="day in days"
        :key="day.id"
        :day="day"
        :other-days="days.filter((d) => d.id !== day.id)"
      />
    </div>
  </div>
</template>
