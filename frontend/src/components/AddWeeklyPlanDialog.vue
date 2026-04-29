<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, Plus } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import WeeklyTemplateEditor from '@/components/WeeklyTemplateEditor.vue'
import { useWeeklySplitTemplatesStore } from '@/stores/weeklySplitTemplates'
import { createId } from '@/components/plan-form/ids'
import type { PlanDay } from '@/types/plan'
import type { WeeklySplitTemplate } from '@/types/template'
type WeeklyPlan = WeeklySplitTemplate

const props = defineProps<{
  prefill?: WeeklyPlan | null
  open?: boolean
  noTrigger?: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  saved: [weeklyPlan: WeeklyPlan]
}>()

const weeklyPlansStore = useWeeklySplitTemplatesStore()

const internalOpen = ref(props.open ?? false)

watch(
  () => props.open,
  (v) => {
    if (v !== undefined) internalOpen.value = v
  },
)

watch(internalOpen, (v) => {
  if (props.open !== undefined && props.open !== v) {
    emit('update:open', v)
  }
})

const label = ref('')
const days = ref<PlanDay[]>([])
const error = ref<string | null>(null)
const submitting = ref(false)
const saveError = ref<string | null>(null)

const buildEmptyDays = (): PlanDay[] =>
  Array.from({ length: 7 }, (_, i) => ({
    id: createId(),
    label: `Day ${i + 1}`,
    isRest: false,
    orderIndex: i,
    exercises: [],
  }))

const buildDaysFromPrefill = (source: WeeklyPlan): PlanDay[] =>
  source.days.map((d, i) => ({
    id: createId(),
    label: d.label,
    isRest: d.isRest ?? false,
    orderIndex: i,
    exercises: (d.exercises ?? []).map((e, ei) => ({
      id: createId(),
      exerciseId: e.exerciseId ?? null,
      exerciseName: e.exerciseName,
      sets: e.sets ?? 3,
      reps: e.reps ?? 10,
      weight: e.weight ?? null,
      weightUnit: (e.weightUnit as 'kg' | 'lbs' | undefined) ?? 'kg',
      restSeconds: e.restSeconds ?? 60,
      orderIndex: ei,
    })),
  }))

const initFromPrefill = () => {
  if (props.prefill) {
    label.value = `${props.prefill.label} (copy)`
    days.value = buildDaysFromPrefill(props.prefill)
  } else {
    label.value = ''
    days.value = buildEmptyDays()
  }
  error.value = null
  saveError.value = null
  submitting.value = false
}

watch(internalOpen, (v) => {
  if (v) initFromPrefill()
})

const isValid = computed(() => {
  if (!label.value.trim()) return false
  return days.value.every(
    (d) =>
      d.isRest ||
      (d.exercises.length > 0 && d.exercises.every((e) => e.exerciseName.trim() !== '')),
  )
})

const validate = () => {
  const trimmed = label.value.trim()
  if (!trimmed) {
    error.value = 'Template name is required.'
    return false
  }
  if (weeklyPlansStore.labelExists(trimmed)) {
    error.value = `A template named "${trimmed}" already exists. Pick a different name.`
    return false
  }
  error.value = null
  return true
}

watch(label, () => {
  if (error.value) validate()
})

const handleSave = async () => {
  if (!isValid.value || !validate() || submitting.value) return
  submitting.value = true
  saveError.value = null
  try {
    const res = await axios.post<WeeklyPlan>(
      `${import.meta.env.VITE_API_URL}/api/weekly-split-templates`,
      {
        label: label.value.trim(),
        days: days.value.map((d, di) => ({
          label: d.label,
          isRest: d.isRest,
          orderIndex: di,
          exercises: d.exercises.map((e, ei) => ({
            exerciseId: e.exerciseId ?? null,
            exerciseName: e.exerciseName,
            sets: e.sets,
            reps: e.reps,
            weight: e.weight ?? null,
            weightUnit: e.weightUnit,
            restSeconds: e.restSeconds,
            orderIndex: ei,
          })),
        })),
      },
    )
    weeklyPlansStore.ingestTemplate(res.data)
    emit('saved', res.data)
    internalOpen.value = false
  } catch (err) {
    console.error('failed to save weekly template', err)
    saveError.value = "We couldn't save the template. Please try again later."
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="internalOpen">
    <DialogTrigger v-if="!noTrigger" as-child>
      <button
        type="button"
        class="flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
        aria-label="Add weekly template"
      >
        <Plus class="h-3.5 w-3.5" />
        Add
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-3xl max-h-[90vh] overflow-y-auto bg-[#181818] text-white border-[#3a3a37] scrollbar-thin"
    >
      <DialogHeader>
        <DialogTitle class="text-2xl text-white">
          {{ prefill ? 'Fork weekly template' : 'New weekly split' }}
        </DialogTitle>
      </DialogHeader>

      <WeeklyTemplateEditor :label="label" :days="days" @update:label="label = $event" />

      <p
        v-if="error"
        class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
      >
        {{ error }}
      </p>
      <p
        v-if="saveError"
        class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
      >
        {{ saveError }}
      </p>

      <div class="mt-2 flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="submitting"
          @click="internalOpen = false"
        >
          Cancel
        </button>
        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!isValid || submitting"
          @click="handleSave"
        >
          <Check class="h-3.5 w-3.5" />
          {{ submitting ? 'Saving…' : 'Save template' }}
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>
