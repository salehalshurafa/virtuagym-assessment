<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { CalendarDays, Check, Copy, Pencil, Trash2 } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import WeeklyTemplateEditor from '@/components/WeeklyTemplateEditor.vue'
import AddWeeklyPlanDialog from '@/components/AddWeeklyPlanDialog.vue'
import { useWeeklySplitTemplatesStore } from '@/stores/weeklySplitTemplates'
import { createId } from '@/components/plan-form/ids'
import type { PlanDay } from '@/types/plan'
import type { WeeklySplitTemplate } from '@/types/template'
type WeeklyPlan = WeeklySplitTemplate

const props = defineProps<{ weeklyPlan: WeeklyPlan }>()

const weeklyPlansStore = useWeeklySplitTemplatesStore()

const open = ref(false)
const mode = ref<'view' | 'edit'>('view')
const confirmingDelete = ref(false)
const forkOpen = ref(false)

const editLabel = ref('')
const editDays = ref<PlanDay[]>([])
const editError = ref<string | null>(null)
const submitting = ref(false)
const deleting = ref(false)
const saveError = ref<string | null>(null)
const deleteError = ref<string | null>(null)

const cloneDays = (source: WeeklyPlan): PlanDay[] =>
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

const enterEdit = () => {
  editLabel.value = props.weeklyPlan.label
  editDays.value = cloneDays(props.weeklyPlan)
  editError.value = null
  mode.value = 'edit'
}

const exitEdit = () => {
  mode.value = 'view'
}

const validateEdit = () => {
  const trimmed = editLabel.value.trim()
  if (!trimmed) {
    editError.value = 'Template name is required.'
    return false
  }
  if (weeklyPlansStore.labelExists(trimmed, props.weeklyPlan.id)) {
    editError.value = `A template named "${trimmed}" already exists. Pick a different name.`
    return false
  }
  editError.value = null
  return true
}

const editIsValid = computed(() => {
  if (!editLabel.value.trim()) return false
  return editDays.value.every(
    (d) =>
      d.isRest ||
      (d.exercises.length > 0 && d.exercises.every((e) => e.exerciseName.trim() !== '')),
  )
})

const handleSave = async () => {
  if (!editIsValid.value || !validateEdit() || submitting.value) return
  submitting.value = true
  saveError.value = null
  try {
    const res = await axios.patch<WeeklyPlan>(
      `${import.meta.env.VITE_API_URL}/api/weekly-split-templates/${props.weeklyPlan.id}`,
      {
        label: editLabel.value.trim(),
        days: editDays.value.map((d, di) => ({
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
    open.value = false
  } catch (err) {
    console.error('failed to update weekly template', err)
    saveError.value = "We couldn't save your changes. Please try again later."
  } finally {
    submitting.value = false
  }
}

const handleDelete = async () => {
  if (deleting.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await axios.delete(
      `${import.meta.env.VITE_API_URL}/api/weekly-split-templates/${props.weeklyPlan.id}`,
    )
    weeklyPlansStore.removeTemplate(props.weeklyPlan.id)
    open.value = false
  } catch (err) {
    console.error('failed to delete weekly template', err)
    deleteError.value = "We couldn't delete this template. Please try again later."
  } finally {
    deleting.value = false
  }
}

const startFork = () => {
  forkOpen.value = true
}

const onForkSaved = () => {
  open.value = false
}

watch(open, (isOpen) => {
  if (isOpen) {
    mode.value = 'view'
    confirmingDelete.value = false
    saveError.value = null
    deleteError.value = null
  } else {
    submitting.value = false
    deleting.value = false
    saveError.value = null
    deleteError.value = null
  }
})

const workoutDayCount = computed(() => props.weeklyPlan.days.filter((d) => !d.isRest).length)
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <button
        type="button"
        class="group flex w-full items-center gap-3 rounded-lg border border-[#3a3a37] bg-[#2a2a28]/60 px-4 py-3 text-left transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
        :aria-label="`Open ${weeklyPlan.label}`"
      >
        <CalendarDays class="h-4 w-4 shrink-0 text-[#a0a09a]" />
        <span class="flex-1 truncate text-sm font-medium text-white">
          {{ weeklyPlan.label }}
        </span>
        <span
          class="shrink-0 rounded-full border border-[#ff6f14] bg-[#1f1f1d] px-2.5 py-0.5 text-xs font-medium text-[#ff6f14]"
        >
          Template
        </span>
        <span class="shrink-0 text-xs text-[#a0a09a] tabular-nums">
          {{ workoutDayCount }}/{{ weeklyPlan.days.length }} days
        </span>
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-3xl max-h-[90vh] p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37] overflow-hidden"
    >
      <template v-if="mode === 'view'">
        <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-4">
          <DialogTitle class="text-2xl text-white">{{ weeklyPlan.label }}</DialogTitle>
          <p class="mt-1 text-xs text-[#a0a09a]">
            {{ workoutDayCount }} workout · {{ weeklyPlan.days.length - workoutDayCount }} rest
          </p>
        </DialogHeader>

        <div class="flex flex-1 flex-col gap-3 overflow-y-auto px-6 py-5 scrollbar-thin">
          <ul class="flex flex-col gap-2">
            <li
              v-for="(day, dayIdx) in weeklyPlan.days"
              :key="dayIdx"
              class="rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-3 py-2"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-medium text-white">{{ day.label }}</span>
                <span
                  v-if="day.isRest"
                  class="rounded-full border border-[#3a3a37] bg-[#2a2a28] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[#a0a09a]"
                >
                  Rest
                </span>
                <span
                  v-else
                  class="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-blue-300"
                >
                  Workout
                </span>
              </div>
              <ul
                v-if="!day.isRest && (day.exercises?.length ?? 0) > 0"
                class="mt-1.5 flex flex-col gap-1"
              >
                <li
                  v-for="(ex, exIdx) in day.exercises ?? []"
                  :key="exIdx"
                  class="flex items-center justify-between gap-2 text-xs text-[#d4d4cf]"
                >
                  <span class="truncate">{{ ex.exerciseName }}</span>
                  <span class="shrink-0 text-[#a0a09a] tabular-nums">
                    {{ ex.sets }} × {{ ex.reps }}
                    <template v-if="ex.weight != null && ex.weight > 0">
                      · {{ ex.weight }}{{ ex.weightUnit }}
                    </template>
                  </span>
                </li>
              </ul>
            </li>
          </ul>
        </div>

        <div
          class="flex items-center justify-between gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3"
        >
          <template v-if="!confirmingDelete">
            <button
              type="button"
              class="flex items-center gap-1 rounded-md border border-red-600/60 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:cursor-pointer hover:bg-red-600/10 hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-600"
              @click="confirmingDelete = true"
            >
              <Trash2 class="h-3.5 w-3.5" />
              Delete
            </button>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
                @click="startFork"
              >
                <Copy class="h-3.5 w-3.5" />
                Fork
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
                @click="enterEdit"
              >
                <Pencil class="h-3.5 w-3.5" />
                Edit
              </button>
            </div>
          </template>
          <template v-else>
            <span class="flex items-center gap-1.5 text-xs text-red-300">
              <Trash2 class="h-3.5 w-3.5" />
              Permanently delete this template?
            </span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="deleting"
                @click="confirmingDelete = false"
              >
                Cancel
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-red-600 bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="deleting"
                @click="handleDelete"
              >
                <Trash2 class="h-3.5 w-3.5" />
                {{ deleting ? 'Deleting…' : 'Confirm delete' }}
              </button>
            </div>
          </template>
          <p
            v-if="deleteError"
            class="basis-full rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
          >
            {{ deleteError }}
          </p>
        </div>
      </template>

      <template v-else>
        <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-4">
          <DialogTitle class="text-2xl text-white">Edit weekly template</DialogTitle>
        </DialogHeader>

        <div class="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5 scrollbar-thin">
          <WeeklyTemplateEditor
            :label="editLabel"
            :days="editDays"
            @update:label="editLabel = $event"
          />
          <p
            v-if="editError"
            class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
          >
            {{ editError }}
          </p>
        </div>

        <div class="flex flex-col gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3">
          <p v-if="saveError" class="text-right text-xs text-rose-300">{{ saveError }}</p>
          <div class="flex items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="submitting"
              @click="exitEdit"
            >
              Cancel
            </button>
            <button
              type="button"
              class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="!editIsValid || submitting"
              @click="handleSave"
            >
              <Check class="h-3.5 w-3.5" />
              {{ submitting ? 'Saving…' : 'Save changes' }}
            </button>
          </div>
        </div>
      </template>
    </DialogContent>
  </Dialog>

  <AddWeeklyPlanDialog
    v-model:open="forkOpen"
    :prefill="weeklyPlan"
    no-trigger
    @saved="onForkSaved"
  />
</template>
