<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Plus, Sparkles, Trash2 } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { useWeeklySplitTemplatesStore } from '@/stores/weeklySplitTemplates'
import DayCard from './DayCard.vue'
import { usePlanForm } from './usePlanForm'

const form = usePlanForm()
const { templates } = storeToRefs(useWeeklySplitTemplatesStore())

const activePlanId = ref('')
const templateToApply = ref('')

onMounted(() => {
  form.initStep2()
  if (form.isWeeklyMode.value && form.weeklyPlans.value[0]) {
    activePlanId.value = form.weeklyPlans.value[0].id
  }
})

watch(
  () => form.weeklyPlans.value.map((p) => p.id).join(','),
  () => {
    const stillExists = form.weeklyPlans.value.some((p) => p.id === activePlanId.value)
    if (!stillExists && form.weeklyPlans.value[0]) {
      activePlanId.value = form.weeklyPlans.value[0].id
    }
  },
)

const activePlan = computed(() => form.weeklyPlans.value.find((p) => p.id === activePlanId.value))

const weeklyDays = computed(() => activePlan.value?.days ?? [])

const hasMultiplePlans = computed(() => form.weeklyPlans.value.length > 1)

const activeStatus = computed(() =>
  activePlan.value ? form.getWeekStatus(activePlan.value.id) : null,
)

const statusLabel = computed(() => {
  switch (activeStatus.value) {
    case 'fresh':
      return 'Custom'
    case 'from-template':
      return 'From template'
    case 'from-template-modified':
      return 'Modified template'
    default:
      return ''
  }
})

const statusClasses = computed(() => {
  switch (activeStatus.value) {
    case 'from-template':
      return 'border-blue-500/30 bg-blue-500/10 text-blue-300'
    case 'from-template-modified':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-300'
    default:
      return 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf]'
  }
})

const rotationSummary = computed(() => {
  const plans = form.weeklyPlans.value
  if (plans.length === 0) return ''
  if (plans.length === 1) {
    const w = form.totalWeeks.value
    return `Used for all ${w} week${w === 1 ? '' : 's'} of the plan.`
  }
  const parts = plans.map((p) => `${p.weekFrequency} wk of ${p.label}`)
  const cycle = form.rotationCycleLength.value
  const total = form.totalWeeks.value
  return `Rotation: ${parts.join(' → ')} (cycles every ${cycle} week${
    cycle === 1 ? '' : 's'
  } over ${total} week${total === 1 ? '' : 's'}).`
})

const handleAddPlan = () => {
  const newId = form.addWeeklyPlan()
  activePlanId.value = newId
}

const handleRemovePlan = (planId: string) => {
  form.removeWeeklyPlan(planId)
}

const onApplyTemplate = () => {
  if (!templateToApply.value || !activePlan.value) return
  const tpl = templates.value.find((t) => t.id === templateToApply.value)

  if (tpl) form.applyTemplate(activePlan.value.id, tpl as never)
  templateToApply.value = ''
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="text-xs text-[#a0a09a]">
      <template v-if="form.isWeeklyMode.value">
        {{ form.totalWeeks.value }} week{{ form.totalWeeks.value === 1 ? '' : 's' }} •
        {{ form.workoutDaysPerWeek.value }} workout day{{
          form.workoutDaysPerWeek.value === 1 ? '' : 's'
        }}
        per week
      </template>
      <template v-else> {{ form.totalDays.value }} days </template>
    </div>

    <div v-if="form.isWeeklyMode.value" class="flex flex-col gap-3">
      <div class="flex items-center gap-2 border-b border-[#3a3a37] pb-2">
        <div class="flex min-w-0 flex-1 gap-1 overflow-x-auto pb-1">
          <button
            v-for="plan in form.weeklyPlans.value"
            :key="plan.id"
            type="button"
            :class="[
              'shrink-0 rounded-md px-3 py-1 text-xs font-medium transition-colors hover:cursor-pointer',
              plan.id === activePlanId
                ? 'bg-[#ff6f14] text-white'
                : 'bg-[#2a2a28] text-[#d4d4cf] hover:bg-[#3a3a37] hover:text-white',
            ]"
            @click="activePlanId = plan.id"
          >
            {{ plan.label }}
          </button>
        </div>
        <button
          type="button"
          class="flex shrink-0 items-center gap-1 rounded-md border border-dashed border-[#ff6f14] px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#ff6f14]/10 focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
          @click="handleAddPlan"
        >
          <Plus class="h-3.5 w-3.5" />
          Add weekly workout plan
        </button>
      </div>

      <p class="text-xs text-[#a0a09a]">{{ rotationSummary }}</p>

      <div v-if="activePlan" class="flex flex-col gap-3">
        <div
          class="flex flex-wrap items-center gap-3 rounded-md border border-[#3a3a37] bg-[#2a2a28]/40 px-3 py-2"
        >
          <div class="flex flex-1 items-center gap-2 min-w-0">
            <Input
              v-model="activePlan.label"
              aria-label="Weekly plan label"
              class="h-8 min-w-0 flex-1 bg-[#1f1f1d] border-[#3a3a37] text-sm text-white"
            />
            <span
              v-if="activeStatus"
              class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider"
              :class="statusClasses"
            >
              {{ statusLabel }}
            </span>
          </div>
          <div class="flex items-center gap-3">
            <label v-if="hasMultiplePlans" class="flex items-center gap-2 text-xs text-[#d4d4cf]">
              Repeats for
              <Input
                v-model.number="activePlan.weekFrequency"
                type="number"
                min="1"
                aria-label="Week frequency"
                class="h-7 w-14 bg-[#1f1f1d] border-[#3a3a37] text-center text-sm text-white"
              />
              week(s) per rotation
            </label>
            <button
              v-if="hasMultiplePlans"
              type="button"
              class="grid h-7 w-7 place-items-center rounded-md text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#3a3a37] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
              :aria-label="`Remove ${activePlan.label}`"
              @click="handleRemovePlan(activePlan.id)"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div
          v-if="templates.length"
          class="flex flex-wrap items-center gap-2 rounded-md border border-dashed border-[#3a3a37] bg-[#1f1f1d] px-3 py-2"
        >
          <Sparkles class="h-3.5 w-3.5 shrink-0 text-[#ff6f14]" />
          <span class="text-xs text-[#d4d4cf]">Use a template:</span>
          <NativeSelect
            v-model="templateToApply"
            class="h-8 min-w-44 flex-1 bg-[#2a2a28] border-[#3a3a37] text-xs text-white"
            aria-label="Apply weekly template"
            @change="onApplyTemplate"
          >
            <NativeSelectOption value="">Pick a template…</NativeSelectOption>
            <NativeSelectOption v-for="t in templates" :key="t.id" :value="t.id">
              {{ t.label }} ({{ t.days.filter((d) => !d.isRest).length }}/{{ t.days.length }} days)
            </NativeSelectOption>
          </NativeSelect>
          <span class="text-[10px] text-[#a0a09a]"
            >Fills label + days; you can still edit anything.</span
          >
        </div>

        <div class="flex flex-col gap-2">
          <DayCard
            v-for="day in weeklyDays"
            :key="day.id"
            :day="day"
            :other-days="weeklyDays.filter((d) => d.id !== day.id)"
            :weekly-plan-id="activePlan.id"
          />
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
