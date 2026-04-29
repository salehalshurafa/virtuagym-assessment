<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ChevronDown, ChevronUp, Plus, Sparkles, Trash2 } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { useWeeklySplitTemplatesStore } from '@/stores/weeklySplitTemplates'
import DayCard from './DayCard.vue'
import { usePlanForm } from './usePlanForm'

const form = usePlanForm()
const { templates } = storeToRefs(useWeeklySplitTemplatesStore())

const expandedPlanId = ref<string | null>(null)
const templateToApply = ref<Record<string, string>>({})

const hasMultiplePlans = computed(() => form.weeklyPlans.value.length > 1)

const rotationSummary = computed(() => {
  const plans = form.weeklyPlans.value
  const numWeeks = form.totalWeeks.value
  if (plans.length === 0) return ''
  if (plans.length === 1) {
    return `Used for all ${numWeeks} week${numWeeks === 1 ? '' : 's'} of the plan.`
  }
  const parts = plans.map((p) => `${p.weekFrequency} wk of ${p.label}`)
  const cycle = form.rotationCycleLength.value

  return `Rotation: ${parts.join(' → ')} (cycles every ${cycle} week${
    cycle === 1 ? '' : 's'
  } over ${numWeeks} week${numWeeks === 1 ? '' : 's'}).`
})

const planSummary = (planId: string): string => {
  const plan = form.weeklyPlans.value.find((p) => p.id === planId)
  if (!plan) return ''
  const workoutDays = plan.days.filter((d) => !d.isRest).length
  const restDays = plan.days.length - workoutDays
  return `${workoutDays} workout · ${restDays} rest`
}

const statusLabelFor = (planId: string) => {
  switch (form.getWeekStatus(planId)) {
    case 'fresh':
      return 'Custom'
    case 'from-template':
      return 'From template'
    case 'from-template-modified':
      return 'Modified template'
    default:
      return ''
  }
}

const statusClassesFor = (planId: string) => {
  switch (form.getWeekStatus(planId)) {
    case 'from-template':
      return 'border-blue-500/30 bg-blue-500/10 text-blue-300'
    case 'from-template-modified':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-300'
    default:
      return 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf]'
  }
}

const toggleExpanded = (id: string) => {
  expandedPlanId.value = expandedPlanId.value === id ? null : id
}

const handleAddPlan = () => {
  const newId = form.addWeeklyPlan()
  expandedPlanId.value = newId
}

const onApplyTemplate = (planId: string) => {
  const tplId = templateToApply.value[planId]
  if (!tplId) return
  const tpl = templates.value.find((t) => t.id === tplId)
  if (tpl) form.applyTemplate(planId, tpl as never)
  templateToApply.value[planId] = ''
}

onMounted(() => {
  form.initStep2()
})

watch(
  [() => form.isWeeklyMode.value, () => form.totalDays.value, () => form.totalWeeks.value],
  () => form.initStep2(),
)

watch(
  () => form.weeklyPlans.value.map((p) => p.id).join(','),
  () => {
    if (
      expandedPlanId.value &&
      !form.weeklyPlans.value.some((p) => p.id === expandedPlanId.value)
    ) {
      expandedPlanId.value = null
    }
  },
)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <span class="text-xs text-[#a0a09a]">
        <template v-if="form.isWeeklyMode.value">
          {{ form.totalWeeks.value }} week{{ form.totalWeeks.value === 1 ? '' : 's' }} •
          {{ form.workoutDaysPerWeek.value }} workout day{{
            form.workoutDaysPerWeek.value === 1 ? '' : 's'
          }}
          per week
        </template>
        <template v-else>{{ form.totalDays.value }} days</template>
      </span>
      <button
        v-if="form.isWeeklyMode.value"
        type="button"
        class="flex items-center gap-1 rounded-md border border-dashed border-[#ff6f14] px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#ff6f14]/10 focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
        @click="handleAddPlan"
      >
        <Plus class="h-3.5 w-3.5" />
        Add weekly workout plan
      </button>
    </div>

    <p v-if="form.isWeeklyMode.value && rotationSummary" class="text-xs text-[#a0a09a]">
      {{ rotationSummary }}
    </p>

    <div v-if="form.isWeeklyMode.value" class="flex flex-col gap-2">
      <div
        v-for="plan in form.weeklyPlans.value"
        :key="plan.id"
        class="rounded-md border border-[#3a3a37] bg-[#2a2a28]/40"
      >
        <button
          type="button"
          class="flex w-full items-center gap-3 px-4 py-3 text-left hover:cursor-pointer hover:bg-[#2a2a28]"
          @click="toggleExpanded(plan.id)"
        >
          <component
            :is="expandedPlanId === plan.id ? ChevronUp : ChevronDown"
            class="h-4 w-4 shrink-0 text-[#a0a09a]"
          />
          <span class="flex-1 truncate text-sm font-medium text-white">{{ plan.label }}</span>
          <span
            class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider"
            :class="statusClassesFor(plan.id)"
          >
            {{ statusLabelFor(plan.id) }}
          </span>
          <span class="hidden shrink-0 text-xs text-[#a0a09a] sm:inline">
            {{ planSummary(plan.id) }}
          </span>
          <span
            class="shrink-0 rounded-full bg-[#1f1f1d] px-2 py-0.5 text-xs font-medium text-[#d4d4cf] tabular-nums"
          >
            ×{{ plan.weekFrequency }} wk
          </span>
        </button>

        <div
          v-if="expandedPlanId === plan.id"
          class="flex flex-col gap-3 border-t border-[#3a3a37] p-3"
        >
          <div class="flex flex-wrap items-center gap-2">
            <label class="flex flex-1 items-center gap-2 text-xs text-[#d4d4cf] min-w-48">
              Label
              <Input
                v-model="plan.label"
                aria-label="Weekly plan label"
                class="h-7 flex-1 bg-[#1f1f1d] border-[#3a3a37] text-sm text-white"
              />
            </label>
            <label v-if="hasMultiplePlans" class="flex items-center gap-2 text-xs text-[#d4d4cf]">
              Repeats for
              <Input
                v-model.number="plan.weekFrequency"
                type="number"
                min="1"
                aria-label="Week frequency"
                class="h-7 w-14 bg-[#1f1f1d] border-[#3a3a37] text-center text-sm text-white"
              />
              week(s)
            </label>
            <button
              v-if="hasMultiplePlans"
              type="button"
              class="grid h-7 w-7 place-items-center rounded-md text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#3a3a37] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
              :aria-label="`Remove ${plan.label}`"
              @click="form.removeWeeklyPlan(plan.id)"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>

          <div
            v-if="templates.length"
            class="flex flex-wrap items-center gap-2 rounded-md border border-dashed border-[#3a3a37] bg-[#1f1f1d] px-3 py-2"
          >
            <Sparkles class="h-3.5 w-3.5 shrink-0 text-[#ff6f14]" />
            <span class="text-xs text-[#d4d4cf]">Use a template:</span>
            <NativeSelect
              v-model="templateToApply[plan.id]"
              class="h-8 min-w-44 flex-1 bg-[#2a2a28] border-[#3a3a37] text-xs text-white"
              aria-label="Apply weekly template"
              @change="onApplyTemplate(plan.id)"
            >
              <NativeSelectOption value="">Pick a template…</NativeSelectOption>
              <NativeSelectOption v-for="t in templates" :key="t.id" :value="t.id">
                {{ t.label }} ({{ t.days.filter((d) => !d.isRest).length }}/{{
                  t.days.length
                }}
                days)
              </NativeSelectOption>
            </NativeSelect>
          </div>

          <div class="flex flex-col gap-2">
            <DayCard
              v-for="day in plan.days"
              :key="day.id"
              :day="day"
              :other-days="plan.days.filter((d) => d.id !== day.id)"
              :weekly-plan-id="plan.id"
            />
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col gap-2">
      <DayCard
        v-for="day in form.flatDays.value"
        :key="day.id"
        :day="day"
        :other-days="form.flatDays.value.filter((d) => d.id !== day.id)"
      />
    </div>
  </div>
</template>
