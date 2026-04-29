<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, Copy, Pencil, Trash2 } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { usePlanTemplatesStore } from '@/stores/planTemplates'
import { providePlanForm } from '@/components/plan-form/usePlanForm'
import PlanEditForm from '@/components/PlanEditForm.vue'
import AddPlanDialog from '@/components/AddPlanDialog.vue'
import { planPayloadToTemplateUpdate, templateToPlan } from '@/lib/templateAdapter'
import type { PlanTemplate } from '@/types/template'

const props = defineProps<{ plan: PlanTemplate }>()

const plansStore = usePlanTemplatesStore()
const form = providePlanForm()

const planView = computed(() => templateToPlan(props.plan))

const open = ref(false)
const mode = ref<'view' | 'edit'>('view')
const confirmingDelete = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const saveError = ref<string | null>(null)
const deleteError = ref<string | null>(null)
const forkOpen = ref(false)
const startFork = () => {
  forkOpen.value = true
  open.value = false
}

const canSave = computed(() => form.changesMade.value && form.isStepValid(1) && form.isStepValid(2))

const enterEdit = () => {
  form.loadPlan(planView.value)
  mode.value = 'edit'
  saveError.value = null
}

const exitEdit = () => {
  mode.value = 'view'
}

const handleSave = async () => {
  if (!canSave.value || submitting.value) return
  submitting.value = true
  saveError.value = null
  try {
    const res = await axios.patch<PlanTemplate>(
      `${import.meta.env.VITE_API_URL}/api/plan-templates/${props.plan.id}`,
      planPayloadToTemplateUpdate(form.buildPlanPayload()),
    )
    plansStore.ingestTemplate(res.data)
    open.value = false
  } catch (err) {
    console.error('failed to update plan template', err)
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
    await axios.delete(`${import.meta.env.VITE_API_URL}/api/plan-templates/${props.plan.id}`)

    plansStore.removeTemplate(props.plan.id)
    open.value = false
  } catch (err) {
    console.error('failed to delete plan template', err)
    deleteError.value = "We couldn't delete this plan template. Please try again later."
  } finally {
    deleting.value = false
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    mode.value = 'view'
    confirmingDelete.value = false
    saveError.value = null
    deleteError.value = null
    form.loadPlan(planView.value)
  } else {
    form.reset()
    mode.value = 'view'
    confirmingDelete.value = false
    submitting.value = false
    deleting.value = false
    saveError.value = null
    deleteError.value = null
  }
})

const totalDays = computed(() => {
  const d = props.plan.duration
  switch (props.plan.durationType) {
    case 'days':
      return d
    case 'weeks':
      return d * 7
    case 'months':
      return d * 30
    case 'years':
      return d * 365
    default:
      return 0
  }
})

const totalWeeks = computed(() => {
  const d = props.plan.duration
  switch (props.plan.durationType) {
    case 'days':
      return Math.floor(d / 7)
    case 'weeks':
      return d
    case 'months':
      return d * 4
    case 'years':
      return d * 52
    default:
      return 0
  }
})

const weeklyPlans = computed(() => planView.value.weeklyPlans ?? [])

const rotationCycleLength = computed(() =>
  weeklyPlans.value.reduce((sum, wp) => sum + Math.max(1, wp.weekFrequency), 0),
)

const rotationSummary = computed(() => {
  const weeks = weeklyPlans.value
  if (weeks.length === 0) return ''
  if (weeks.length === 1) {
    const w = totalWeeks.value
    return `Used for all ${w} week${w === 1 ? '' : 's'} of the plan.`
  }
  const parts = weeks.map((wp) => `${wp.weekFrequency} wk of ${wp.label || 'Untitled'}`)
  const cycle = rotationCycleLength.value
  return `Rotation: ${parts.join(' → ')} (cycles every ${cycle} week${
    cycle === 1 ? '' : 's'
  } over ${totalWeeks.value} week${totalWeeks.value === 1 ? '' : 's'}).`
})

const weeklyAssignmentSummary = (weeklyId: string) => {
  const wp = weeklyPlans.value.find((w) => w.id === weeklyId)
  if (!wp) return ''
  const workout = wp.days.filter((d) => !d.isRest).length
  const rest = wp.days.length - workout
  return `${workout} workout · ${rest} rest`
}

const statusLabel = computed(() => {
  if (props.plan.archived) return 'Archived'
  return 'Template'
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <button
        type="button"
        class="group flex w-full items-center gap-3 rounded-lg border border-[#3a3a37] bg-[#2a2a28]/60 px-4 py-3 text-left transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
        :aria-label="`Open ${plan.title}`"
      >
        <span class="flex-1 truncate text-sm font-medium text-white">
          {{ plan.title }}
        </span>
        <span
          class="shrink-0 rounded-full border border-[#ff6f14] bg-[#1f1f1d] px-2.5 py-0.5 text-xs font-medium text-[#ff6f14]"
        >
          {{ plan.duration }} {{ plan.durationType }}
        </span>
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-3xl max-h-[90vh] p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37] overflow-hidden"
    >
      <template v-if="mode === 'view'">
        <div class="relative h-48 w-full shrink-0 overflow-hidden">
          <img
            v-if="plan.imageUrl"
            :src="plan.imageUrl"
            :alt="`${plan.title} cover`"
            class="h-full w-full object-cover"
          />
          <div
            v-else
            class="h-full w-full bg-gradient-to-br from-[#2a2a28] via-[#1f1f1d] to-[#0f0f0e]"
          />
          <div
            class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/40 to-transparent"
          />
          <div class="absolute bottom-4 left-6 right-12">
            <DialogTitle class="text-3xl font-bold text-white drop-shadow-lg">
              {{ plan.title }}
            </DialogTitle>
            <p class="mt-1 text-xs text-white/80">
              {{ plan.duration }} {{ plan.durationType }}
              <template v-if="plan.workoutDaysPerWeek">
                · {{ plan.workoutDaysPerWeek }} workout day{{
                  plan.workoutDaysPerWeek === 1 ? '' : 's'
                }}
                / wk
              </template>
            </p>
          </div>
        </div>

        <div class="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5 scrollbar-thin">
          <section class="flex flex-col gap-3">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Overview
            </h3>
            <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div class="flex flex-col gap-0.5">
                <dt class="text-xs text-[#a0a09a]">Duration</dt>
                <dd class="text-white">
                  {{ plan.duration }} {{ plan.durationType }}
                  <span class="text-xs text-[#a0a09a]">({{ totalDays }} days)</span>
                </dd>
              </div>
              <div v-if="plan.workoutDaysPerWeek" class="flex flex-col gap-0.5">
                <dt class="text-xs text-[#a0a09a]">Workout days</dt>
                <dd class="text-white">{{ plan.workoutDaysPerWeek }} per week</dd>
              </div>
              <div class="flex flex-col gap-0.5">
                <dt class="text-xs text-[#a0a09a]">Status</dt>
                <dd class="text-white">{{ statusLabel }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="weeklyPlans.length" class="flex flex-col gap-3">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Workouts
            </h3>
            <p v-if="rotationSummary" class="text-xs text-[#a0a09a]">{{ rotationSummary }}</p>
            <ul class="flex flex-col gap-2">
              <li
                v-for="wp in weeklyPlans"
                :key="wp.id"
                class="flex items-center gap-3 rounded-md border border-[#3a3a37] bg-[#2a2a28]/40 px-3 py-2"
              >
                <span class="flex-1 truncate text-sm font-medium text-white">
                  {{ wp.label || 'Untitled week' }}
                </span>
                <span class="shrink-0 text-xs text-[#a0a09a]">
                  {{ weeklyAssignmentSummary(wp.id) }}
                </span>
                <span
                  class="shrink-0 rounded-full bg-[#1f1f1d] px-2 py-0.5 text-xs font-medium text-[#d4d4cf] tabular-nums"
                >
                  ×{{ wp.weekFrequency }} wk
                </span>
              </li>
            </ul>
          </section>

          <section v-else-if="planView.flatDays?.length" class="flex flex-col gap-3">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Workouts
            </h3>
            <p class="text-xs text-[#a0a09a]">
              {{ planView.flatDays.length }} day{{ planView.flatDays.length === 1 ? '' : 's' }} ·
              {{ planView.flatDays.filter((d) => !d.isRest).length }} workout ·
              {{ planView.flatDays.filter((d) => d.isRest).length }} rest
            </p>
          </section>
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
                class="flex items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
                @click="startFork"
              >
                <Copy class="h-3.5 w-3.5" />
                Fork
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
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
              Permanently delete this plan?
            </span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63] disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="deleting"
                @click="confirmingDelete = false"
              >
                Cancel
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-red-600 bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-40"
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
          <DialogTitle class="text-2xl text-white">Edit plan</DialogTitle>
        </DialogHeader>

        <div class="flex flex-1 flex-col overflow-y-auto px-6 py-5 scrollbar-thin">
          <PlanEditForm />
        </div>

        <div class="flex flex-col gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3">
          <p v-if="saveError" class="text-right text-xs text-rose-300">{{ saveError }}</p>
          <div class="flex items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63] disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="submitting"
              @click="exitEdit"
            >
              Cancel
            </button>
            <button
              type="button"
              class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="!canSave || submitting"
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

  <AddPlanDialog :open="forkOpen" :prefill="plan" no-trigger @update:open="forkOpen = $event" />
</template>
