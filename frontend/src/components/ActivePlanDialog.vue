<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  Ban,
  Bookmark,
  CalendarDays,
  Check,
  ChevronDown,
  Loader2,
  Pause,
  Pencil,
  Play,
  RotateCcw,
  X,
} from 'lucide-vue-next'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import UserAvatar from '@/components/UserAvatar.vue'
import axios from 'axios'
import { usePlanTemplatesStore } from '@/stores/planTemplates'
import { useWeeklySplitTemplatesStore } from '@/stores/weeklySplitTemplates'
import { useUsersStore } from '@/stores/users'
import { useActivePlansStore } from '@/stores/activePlans'
import type { Plan, WeeklyWorkoutPlan, PlanDay } from '@/types/plan'
import type { PlanStatus, UserScheduleEntry } from '@/types/user'
import type { PlanTemplate, WeeklySplitTemplate } from '@/types/template'
import { planMatchesAnyTemplate, weeklyMatchesAnyTemplate } from '@/lib/templateMatch'

interface Assignee {
  id: string
  firstName: string
  lastName: string
}

interface ActivePlanRow extends Plan {
  assignees: Assignee[]
  statusSummary: PlanStatus | 'mixed'
}

const props = defineProps<{
  plan: ActivePlanRow
}>()

const emit = defineEmits<{
  close: []
  requestModify: [userId: string]
}>()

const open = ref(true)
watch(open, (v) => {
  if (!v) emit('close')
})

const planTemplatesStore = usePlanTemplatesStore()
const { templates: planTemplates } = storeToRefs(planTemplatesStore)
const weeklySplitTemplatesStore = useWeeklySplitTemplatesStore()
const { templates: weeklySplitTemplates } = storeToRefs(weeklySplitTemplatesStore)
const usersStore = useUsersStore()
const activePlansStore = useActivePlansStore()

const API_URL = import.meta.env.VITE_API_URL

const canSaveAsTemplate = computed(() => !planMatchesAnyTemplate(props.plan, planTemplates.value))

const showingTitleInput = ref(false)
const newTitle = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const successMessage = ref<string | null>(null)

const startSaveAsTemplate = () => {
  const stripped = props.plan.title.replace(/\s+—\s+[^—]+$/, '').trim()
  newTitle.value = stripped || props.plan.title
  submitError.value = null
  successMessage.value = null
  showingTitleInput.value = true
}

const cancelSaveAsTemplate = () => {
  showingTitleInput.value = false
  submitError.value = null
}

const handleSaveAsTemplate = async () => {
  if (submitting.value) return
  const t = newTitle.value.trim()
  if (!t) {
    submitError.value = 'Title is required.'
    return
  }
  submitting.value = true
  submitError.value = null
  try {
    const res = await axios.post<PlanTemplate>(`${API_URL}/api/plan-templates/from-plan`, {
      planId: props.plan.id,
      title: t,
    })
    planTemplatesStore.ingestTemplate(res.data)
    successMessage.value = `Saved as template "${res.data.title}".`
    showingTitleInput.value = false
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      submitError.value = `A template named "${t}" already exists.`
    } else {
      submitError.value = "We couldn't save the template. Please try again later."
    }
  } finally {
    submitting.value = false
  }
}

const weeklyTitleInputs = ref<Record<string, string>>({})
const weeklySubmittingId = ref<string | null>(null)
const weeklySubmitError = ref<Record<string, string | null>>({})
const weeklySuccessMessage = ref<Record<string, string | null>>({})
const showingWeeklyInputId = ref<string | null>(null)

const canSaveWeeklyAsTemplate = (wp: WeeklyWorkoutPlan | null | undefined) => {
  if (!wp) return false
  return !weeklyMatchesAnyTemplate(wp, weeklySplitTemplates.value)
}

const startSaveWeeklyAsTemplate = (wp: WeeklyWorkoutPlan) => {
  weeklyTitleInputs.value[wp.id] = wp.label
  weeklySubmitError.value[wp.id] = null
  weeklySuccessMessage.value[wp.id] = null
  showingWeeklyInputId.value = wp.id
}

const cancelSaveWeeklyAsTemplate = () => {
  showingWeeklyInputId.value = null
}

const handleSaveWeeklyAsTemplate = async (wp: WeeklyWorkoutPlan) => {
  if (weeklySubmittingId.value) return
  const label = (weeklyTitleInputs.value[wp.id] ?? '').trim()
  if (!label) {
    weeklySubmitError.value[wp.id] = 'Label is required.'
    return
  }
  weeklySubmittingId.value = wp.id
  weeklySubmitError.value[wp.id] = null
  try {
    const res = await axios.post<WeeklySplitTemplate>(
      `${API_URL}/api/weekly-split-templates/from-weekly-plan`,
      { weeklyPlanId: wp.id, label },
    )
    weeklySplitTemplatesStore.ingestTemplate(res.data)
    weeklySuccessMessage.value[wp.id] = `Saved as template "${res.data.label}".`
    showingWeeklyInputId.value = null
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      weeklySubmitError.value[wp.id] = `A template labelled "${label}" already exists.`
    } else {
      weeklySubmitError.value[wp.id] = "We couldn't save the template. Please try again later."
    }
  } finally {
    weeklySubmittingId.value = null
  }
}

const expandedDayKey = ref<string | null>(null)

const dayKey = (day: PlanDay, weeklyId: string | null) => `${weeklyId ?? 'flat'}:${day.id}`

const toggleDay = (day: PlanDay, weeklyId: string | null) => {
  if (day.isRest || day.exercises.length === 0) return
  const k = dayKey(day, weeklyId)
  expandedDayKey.value = expandedDayKey.value === k ? null : k
}

interface EnrichedAssignee extends Assignee {
  assignmentId: string | null
  status: PlanStatus | null
  avatarUrl?: string | null
  assignedByName?: string | null
  assignedByEmail?: string | null
}

const enrichedAssignees = computed<EnrichedAssignee[]>(() =>
  props.plan.assignees.map((a) => {
    const u = usersStore.getById(a.id)
    return {
      ...a,
      assignmentId: u?.latestPlan?.id ?? null,
      status: u?.latestPlan?.status ?? null,
      avatarUrl: u?.avatarUrl ?? null,
      assignedByName: u?.latestPlan?.assignedByName ?? null,
      assignedByEmail: u?.latestPlan?.assignedByEmail ?? null,
    }
  }),
)

type ActionType = 'pause' | 'resume' | 'cancel' | 'restart'

interface ActionTheme {
  icon: typeof Pause
  label: string
  verb: string
  buttonClasses: string
  panelClasses: string
  panelTextClasses: string
  confirmClasses: string
  message: (firstName: string) => string
}

const actionThemes: Record<ActionType, ActionTheme> = {
  pause: {
    icon: Pause,
    label: 'Pause',
    verb: 'Pause plan',
    buttonClasses:
      'border-amber-500/60 bg-amber-500/5 text-amber-300 hover:border-amber-500 hover:bg-amber-500/15 hover:text-amber-200 focus:ring-amber-500/50',
    panelClasses: 'border-amber-500/60 bg-amber-500/10',
    panelTextClasses: 'text-amber-200',
    confirmClasses:
      'border-amber-500 bg-amber-500 text-[#181818] hover:bg-amber-400 focus:ring-amber-500/50',
    message: (n) =>
      `Pause this plan for ${n}? The remaining days will be saved so you can resume later.`,
  },
  resume: {
    icon: Play,
    label: 'Resume',
    verb: 'Resume plan',
    buttonClasses:
      'border-emerald-500/60 bg-emerald-500/5 text-emerald-300 hover:border-emerald-500 hover:bg-emerald-500/15 hover:text-emerald-200 focus:ring-emerald-500/50',
    panelClasses: 'border-emerald-500/60 bg-emerald-500/10',
    panelTextClasses: 'text-emerald-200',
    confirmClasses:
      'border-emerald-500 bg-emerald-500 text-white hover:bg-emerald-400 focus:ring-emerald-500/50',
    message: (n) =>
      `Resume this plan for ${n}? The end date is recomputed from today plus the remaining days saved at pause.`,
  },
  cancel: {
    icon: Ban,
    label: 'Cancel',
    verb: 'Cancel plan',
    buttonClasses:
      'border-rose-500/60 bg-rose-600/5 text-rose-300 hover:border-rose-500 hover:bg-rose-600/15 hover:text-rose-200 focus:ring-rose-500/50',
    panelClasses: 'border-rose-500/60 bg-rose-600/10',
    panelTextClasses: 'text-rose-200',
    confirmClasses:
      'border-rose-600 bg-rose-600 text-white hover:bg-rose-500 focus:ring-rose-500/50',
    message: (n) =>
      `Cancel this plan for ${n}? The user will no longer be on this plan and progress is not kept.`,
  },
  restart: {
    icon: RotateCcw,
    label: 'Restart',
    verb: 'Restart plan',
    buttonClasses:
      'border-indigo-500/60 bg-indigo-500/5 text-indigo-300 hover:border-indigo-500 hover:bg-indigo-500/15 hover:text-indigo-200 focus:ring-indigo-500/50',
    panelClasses: 'border-indigo-500/60 bg-indigo-500/10',
    panelTextClasses: 'text-indigo-200',
    confirmClasses:
      'border-indigo-500 bg-indigo-500 text-white hover:bg-indigo-400 focus:ring-indigo-500/50',
    message: (n) =>
      `Restart this plan for ${n} from today? The new end date is computed from the plan's full duration.`,
  },
}

const planStatusDisplay: Record<PlanStatus, { label: string; classes: string }> = {
  'in-progress': {
    label: 'In progress',
    classes: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  },
  paused: {
    label: 'Paused',
    classes: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  },
  completed: {
    label: 'Completed',
    classes: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
  },
  cancelled: {
    label: 'Cancelled',
    classes: 'border-rose-500/40 bg-rose-600/10 text-rose-300',
  },
}

const summaryDisplay: Record<PlanStatus | 'mixed', { label: string; classes: string }> = {
  ...planStatusDisplay,
  mixed: {
    label: 'Mixed',
    classes: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
  },
}

interface PendingAction {
  assignmentId: string
  action: ActionType
}

const pendingAction = ref<PendingAction | null>(null)
const actionInFlight = ref(false)
const actionError = ref<string | null>(null)

const requestAction = (assignmentId: string, action: ActionType) => {
  pendingAction.value = { assignmentId, action }
  actionError.value = null
}

const cancelPendingAction = () => {
  if (actionInFlight.value) return
  pendingAction.value = null
  actionError.value = null
}

const confirmPendingAction = async () => {
  const pa = pendingAction.value
  if (!pa) return
  actionInFlight.value = true
  actionError.value = null
  try {
    await axios.post(`${API_URL}/api/assignments/${pa.assignmentId}/${pa.action}`)
    const targetUser = enrichedAssignees.value.find((a) => a.assignmentId === pa.assignmentId)
    if (targetUser) {
      await usersStore.refetchUser(targetUser.id).catch(() => undefined)
    }

    activePlansStore.refresh().catch(() => undefined)
    pendingAction.value = null
  } catch (err) {
    console.error(`Failed to ${pa.action} assignment`, err)
    actionError.value = `Couldn't ${pa.action} this plan. Please try again.`
  } finally {
    actionInFlight.value = false
  }
}

const onModifyClick = (userId: string) => {
  emit('requestModify', userId)
  open.value = false
}

const canPause = (s: PlanStatus | null) => s === 'in-progress'
const canResume = (s: PlanStatus | null) => s === 'paused'
const canCancel = (s: PlanStatus | null) => s === 'in-progress' || s === 'paused'
const canRestart = (s: PlanStatus | null) => s !== null

const todayIso = (() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})()

const formatShort = (value: string | Date) => {
  const d = value instanceof Date ? value : new Date(value)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const selectedAssigneeId = ref<string | null>(enrichedAssignees.value[0]?.id ?? null)

watch(
  () => enrichedAssignees.value.map((a) => a.id).join(','),
  (joined) => {
    if (selectedAssigneeId.value && joined.split(',').includes(selectedAssigneeId.value)) {
      return
    }
    selectedAssigneeId.value = enrichedAssignees.value[0]?.id ?? null
  },
)

const selectedAssignee = computed(
  () => enrichedAssignees.value.find((a) => a.id === selectedAssigneeId.value) ?? null,
)

const selectedSchedule = computed<UserScheduleEntry[]>(() => {
  if (!selectedAssigneeId.value) return []
  const u = usersStore.getById(selectedAssigneeId.value)
  return u?.latestPlan?.schedule ?? []
})

interface ScheduleWeek {
  weekIndex: number
  startDate: string
  endDate: string
  entries: UserScheduleEntry[]
}

const scheduleWeeks = computed<ScheduleWeek[]>(() => {
  const schedule = selectedSchedule.value
  if (schedule.length === 0) return []
  const groups: ScheduleWeek[] = []
  for (let i = 0; i < schedule.length; i += 7) {
    const slice = schedule.slice(i, i + 7)

    const first = slice[0]!
    const last = slice[slice.length - 1]!
    groups.push({
      weekIndex: Math.floor(i / 7) + 1,
      startDate: first.date,
      endDate: last.date,
      entries: slice,
    })
  }
  return groups
})

const todayWeekIndex = computed(() => {
  for (const g of scheduleWeeks.value) {
    if (todayIso >= g.startDate && todayIso <= g.endDate) return g.weekIndex
  }
  return null
})

const activeWeekIndex = ref<number>(1)

watch(
  [() => selectedAssigneeId.value, todayWeekIndex, () => scheduleWeeks.value.length],
  () => {
    activeWeekIndex.value = todayWeekIndex.value ?? scheduleWeeks.value[0]?.weekIndex ?? 1
  },
  { immediate: true },
)

const activeScheduleWeek = computed(
  () => scheduleWeeks.value.find((g) => g.weekIndex === activeWeekIndex.value) ?? null,
)

const expandedScheduleEntryKey = ref<string | null>(null)

const scheduleEntryKey = (entry: UserScheduleEntry) => `${entry.date}:${entry.dayId}`

const toggleScheduleEntry = (entry: UserScheduleEntry) => {
  if (entry.isRest || entry.exercises.length === 0) return
  const k = scheduleEntryKey(entry)
  expandedScheduleEntryKey.value = expandedScheduleEntryKey.value === k ? null : k
}

const scheduleEntryStateClass = (entry: UserScheduleEntry) => {
  if (entry.date < todayIso) return 'opacity-60'
  if (entry.date === todayIso) return 'ring-1 ring-[#ff6f14]/60'
  return ''
}

const scheduleEntryStateLabel = (entry: UserScheduleEntry) => {
  if (entry.date < todayIso) return 'Past'
  if (entry.date === todayIso) return 'Today'
  return 'Upcoming'
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent
      class="dark sm:max-w-3xl max-h-[90vh] p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37] overflow-hidden"
    >
      <DialogHeader class="border-b border-[#3a3a37] px-4 pt-5 pb-4 sm:px-6 sm:pt-6 sm:pb-5">
        <div class="flex items-center justify-between gap-3">
          <div class="flex flex-col gap-0.5 min-w-0">
            <DialogTitle class="text-xl sm:text-2xl font-bold text-white truncate">
              {{ plan.title }}
            </DialogTitle>
            <p class="text-xs text-[#a0a09a]">
              {{ plan.duration }} {{ plan.durationType }}
              <template v-if="plan.workoutDaysPerWeek">
                · {{ plan.workoutDaysPerWeek }} workout day{{
                  plan.workoutDaysPerWeek === 1 ? '' : 's'
                }}/week
              </template>
            </p>
          </div>
          <span
            class="shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium"
            :class="summaryDisplay[plan.statusSummary].classes"
          >
            {{ summaryDisplay[plan.statusSummary].label }}
          </span>
        </div>
      </DialogHeader>

      <div
        class="flex flex-1 flex-col gap-6 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5 scrollbar-thin"
      >
        <section class="flex flex-col gap-2">
          <h3 class="text-xs font-semibold uppercase text-[#a0a09a]">
            Assigned to ({{ plan.assignees.length }})
          </h3>
          <ul
            class="flex flex-col gap-1.5 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-2 py-2"
          >
            <li
              v-for="a in enrichedAssignees"
              :key="a.id"
              class="flex flex-col gap-2 rounded-md px-2 py-1.5"
            >
              <div class="flex flex-wrap items-center gap-2">
                <UserAvatar
                  :name="`${a.firstName} ${a.lastName}`"
                  :avatar-url="a.avatarUrl ?? undefined"
                  class="h-8 w-8 text-[10px]"
                />
                <span class="text-sm text-white truncate min-w-0">
                  {{ a.firstName }} {{ a.lastName }}
                </span>
                <span
                  v-if="a.status"
                  class="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider"
                  :class="planStatusDisplay[a.status].classes"
                >
                  {{ planStatusDisplay[a.status].label }}
                </span>
                <div class="ml-auto flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    class="flex items-center gap-1 rounded-md border-2 border-sky-500/60 bg-sky-500/5 px-2 py-1 text-[11px] font-medium text-sky-300 transition-colors hover:cursor-pointer hover:border-sky-500 hover:bg-sky-500/15 hover:text-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-500/50"
                    @click="onModifyClick(a.id)"
                  >
                    <Pencil class="h-3 w-3" />
                    Modify
                  </button>
                  <button
                    v-if="a.assignmentId && canPause(a.status)"
                    type="button"
                    class="flex items-center gap-1 rounded-md border-2 px-2 py-1 text-[11px] font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
                    :class="actionThemes.pause.buttonClasses"
                    @click="requestAction(a.assignmentId, 'pause')"
                  >
                    <Pause class="h-3 w-3" />
                    Pause
                  </button>
                  <button
                    v-if="a.assignmentId && canResume(a.status)"
                    type="button"
                    class="flex items-center gap-1 rounded-md border-2 px-2 py-1 text-[11px] font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
                    :class="actionThemes.resume.buttonClasses"
                    @click="requestAction(a.assignmentId, 'resume')"
                  >
                    <Play class="h-3 w-3" />
                    Resume
                  </button>
                  <button
                    v-if="a.assignmentId && canCancel(a.status)"
                    type="button"
                    class="flex items-center gap-1 rounded-md border-2 px-2 py-1 text-[11px] font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
                    :class="actionThemes.cancel.buttonClasses"
                    @click="requestAction(a.assignmentId, 'cancel')"
                  >
                    <Ban class="h-3 w-3" />
                    Cancel
                  </button>
                  <button
                    v-if="a.assignmentId && canRestart(a.status)"
                    type="button"
                    class="flex items-center gap-1 rounded-md border-2 px-2 py-1 text-[11px] font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
                    :class="actionThemes.restart.buttonClasses"
                    @click="requestAction(a.assignmentId, 'restart')"
                  >
                    <RotateCcw class="h-3 w-3" />
                    Restart
                  </button>
                </div>
              </div>

              <p
                v-if="a.assignedByName || a.assignedByEmail"
                class="ml-10 text-[11px] text-[#a0a09a]"
              >
                Assigned by
                <span class="text-[#d4d4cf]">
                  {{ a.assignedByName ?? a.assignedByEmail }}
                </span>
                <a
                  v-if="a.assignedByEmail && a.assignedByName"
                  :href="`mailto:${a.assignedByEmail}`"
                  class="text-[#a0a09a]/80 hover:text-[#d4d4cf]"
                >
                  ({{ a.assignedByEmail }})
                </a>
              </p>

              <div
                v-if="
                  pendingAction && a.assignmentId && pendingAction.assignmentId === a.assignmentId
                "
                class="flex flex-col gap-2 rounded-md border-2 px-3 py-2"
                :class="actionThemes[pendingAction.action].panelClasses"
              >
                <p
                  class="text-xs font-medium"
                  :class="actionThemes[pendingAction.action].panelTextClasses"
                >
                  {{ actionThemes[pendingAction.action].message(a.firstName) }}
                </p>
                <p v-if="actionError" class="text-xs text-red-300">
                  {{ actionError }}
                </p>
                <div class="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    class="rounded-md border-2 border-[#3a3a37] px-2.5 py-1 text-[11px] font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                    :disabled="actionInFlight"
                    @click="cancelPendingAction"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    class="flex items-center gap-1.5 rounded-md border-2 px-2.5 py-1 text-[11px] font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-50"
                    :class="actionThemes[pendingAction.action].confirmClasses"
                    :disabled="actionInFlight"
                    @click="confirmPendingAction"
                  >
                    <Loader2 v-if="actionInFlight" class="h-3 w-3 animate-spin" />
                    <component
                      v-else
                      :is="actionThemes[pendingAction.action].icon"
                      class="h-3 w-3"
                    />
                    {{ actionThemes[pendingAction.action].verb }}
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </section>

        <section
          v-if="enrichedAssignees.length && scheduleWeeks.length"
          class="flex flex-col gap-3"
        >
          <div class="flex items-center gap-2">
            <CalendarDays class="h-4 w-4 text-[#a0a09a]" />
            <h3 class="text-xs font-semibold uppercase text-[#a0a09a]">Schedule</h3>
          </div>

          <div v-if="enrichedAssignees.length > 1" class="flex flex-wrap items-center gap-1.5">
            <span class="text-[11px] uppercase tracking-wider text-[#a0a09a]"> Viewing for </span>
            <button
              v-for="a in enrichedAssignees"
              :key="`sched-pick-${a.id}`"
              type="button"
              class="rounded-full border-2 px-2.5 py-0.5 text-[11px] font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
              :class="
                selectedAssigneeId === a.id
                  ? 'border-[#ff6f14] bg-[#ff6f14]/15 text-[#ff7e2a] focus:ring-[#ff6f14]/50'
                  : 'border-[#3a3a37] bg-[#1f1f1d] text-[#d4d4cf] hover:border-[#55554f] hover:text-white focus:ring-[#6a6a63]'
              "
              @click="selectedAssigneeId = a.id"
            >
              {{ a.firstName }} {{ a.lastName }}
            </button>
          </div>

          <div
            class="flex gap-1 overflow-x-auto border-b border-[#3a3a37] scrollbar-thin pb-1"
            role="tablist"
            aria-label="Schedule weeks"
          >
            <button
              v-for="group in scheduleWeeks"
              :key="`sched-week-${group.weekIndex}`"
              type="button"
              role="tab"
              :aria-selected="activeWeekIndex === group.weekIndex"
              class="flex shrink-0 flex-col items-start gap-0.5 rounded-t-md border-2 border-b-0 px-4 py-2 text-left transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
              :class="
                activeWeekIndex === group.weekIndex
                  ? 'border-[#ff6f14] bg-[#ff6f14]/10 text-white'
                  : 'border-transparent bg-[#1f1f1d] text-[#a0a09a] hover:bg-[#2a2a28] hover:text-white'
              "
              @click="activeWeekIndex = group.weekIndex"
            >
              <span
                class="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider"
              >
                Week {{ group.weekIndex }}
                <span
                  v-if="todayWeekIndex === group.weekIndex"
                  class="rounded-full bg-[#ff6f14] px-1.5 py-px text-[9px] font-bold text-[#181818]"
                >
                  Today
                </span>
              </span>
              <span class="text-[10px] tabular-nums opacity-80">
                {{ formatShort(group.startDate) }} – {{ formatShort(group.endDate) }}
              </span>
            </button>
          </div>

          <ul v-if="activeScheduleWeek" class="flex flex-col gap-2">
            <li
              v-for="entry in activeScheduleWeek.entries"
              :key="scheduleEntryKey(entry)"
              class="flex flex-col"
            >
              <button
                type="button"
                class="flex w-full items-center gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-3 py-2.5 text-left transition-colors"
                :class="[
                  scheduleEntryStateClass(entry),
                  entry.isRest || entry.exercises.length === 0
                    ? 'cursor-default'
                    : 'hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28]',
                  expandedScheduleEntryKey === scheduleEntryKey(entry)
                    ? 'rounded-b-none border-b-0'
                    : '',
                ]"
                :aria-expanded="expandedScheduleEntryKey === scheduleEntryKey(entry)"
                @click="toggleScheduleEntry(entry)"
              >
                <div class="flex w-16 shrink-0 flex-col text-xs tabular-nums text-[#a0a09a]">
                  <span class="font-medium text-white">{{ formatShort(entry.date) }}</span>
                  <span class="text-[10px] uppercase tracking-wider">
                    {{ scheduleEntryStateLabel(entry) }}
                  </span>
                </div>
                <div class="flex flex-1 items-center gap-2 min-w-0">
                  <span
                    v-if="entry.isRest"
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
                  <span class="truncate text-sm text-white">{{ entry.label }}</span>
                  <span
                    v-if="!entry.isRest && entry.exercises.length"
                    class="ml-auto shrink-0 text-xs text-[#a0a09a] tabular-nums"
                  >
                    {{ entry.exercises.length }} exercise{{
                      entry.exercises.length === 1 ? '' : 's'
                    }}
                  </span>
                </div>
                <ChevronDown
                  v-if="!entry.isRest && entry.exercises.length"
                  class="h-4 w-4 shrink-0 text-[#a0a09a] transition-transform"
                  :class="expandedScheduleEntryKey === scheduleEntryKey(entry) ? 'rotate-180' : ''"
                />
              </button>

              <div
                v-if="expandedScheduleEntryKey === scheduleEntryKey(entry)"
                class="rounded-b-md border border-t border-[#ff6f14]/40 bg-[#0f0f0e] px-4 py-3"
              >
                <h5 class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#a0a09a]">
                  Exercises
                </h5>
                <ul class="flex flex-col divide-y divide-[#2a2a28]">
                  <li
                    v-for="ex in entry.exercises"
                    :key="ex.id"
                    class="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0"
                  >
                    <span class="truncate text-sm font-medium text-white">
                      {{ ex.exerciseName }}
                    </span>
                    <span class="shrink-0 text-sm text-[#d4d4cf] tabular-nums">
                      {{ ex.sets }} × {{ ex.reps }}
                      <template v-if="ex.weight != null">
                        <span class="text-[#a0a09a]">·</span>
                        {{ ex.weight }}{{ ex.weightUnit }}
                      </template>
                      <span class="text-[#a0a09a]">·</span>
                      <span class="text-[#a0a09a]">{{ ex.restSeconds }}s rest</span>
                    </span>
                  </li>
                </ul>
              </div>
            </li>
          </ul>
        </section>

        <section
          v-if="plan.weeklyPlans?.length || plan.flatDays?.length"
          class="flex flex-col gap-3"
        >
          <h3 class="text-xs font-semibold uppercase text-[#a0a09a]">Plan structure</h3>

          <ul v-if="plan.weeklyPlans?.length" class="flex flex-col gap-3">
            <li
              v-for="wp in plan.weeklyPlans"
              :key="wp.id"
              class="flex flex-col gap-2 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-3 py-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <span class="flex-1 truncate text-sm font-medium text-white">
                  {{ wp.label || 'Unnamed week' }}
                </span>
                <span
                  class="shrink-0 rounded-full bg-[#2a2a28] px-2 py-0.5 text-xs text-[#d4d4cf] tabular-nums"
                >
                  ×{{ wp.weekFrequency }} wk
                </span>
                <span class="shrink-0 text-xs text-[#a0a09a]">
                  {{ wp.days.filter((d) => !d.isRest).length }} workout ·
                  {{ wp.days.filter((d) => d.isRest).length }} rest
                </span>
                <button
                  v-if="
                    canSaveWeeklyAsTemplate(wp) &&
                    showingWeeklyInputId !== wp.id &&
                    !weeklySuccessMessage[wp.id]
                  "
                  type="button"
                  class="flex shrink-0 items-center gap-1 rounded-md border border-[#ff6f14]/60 bg-[#ff6f14]/5 px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#ff6f14]/15 disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="weeklySubmittingId !== null"
                  @click="startSaveWeeklyAsTemplate(wp)"
                >
                  <Bookmark class="h-3 w-3" />
                  Save as template
                </button>
                <span
                  v-else-if="weeklySuccessMessage[wp.id]"
                  class="shrink-0 text-xs text-emerald-300"
                >
                  Saved
                </span>
              </div>

              <div
                v-if="showingWeeklyInputId === wp.id"
                class="flex flex-col gap-2 rounded-md border border-[#ff6f14]/30 bg-[#ff6f14]/5 px-3 py-2"
              >
                <label class="text-[11px] uppercase text-[#a0a09a]"> Template label </label>
                <div class="flex items-end gap-2">
                  <Input
                    v-model="weeklyTitleInputs[wp.id]"
                    class="flex-1 bg-[#2a2a28] border-[#3a3a37] text-sm text-white"
                    aria-label="Weekly template label"
                  />
                  <button
                    type="button"
                    class="flex shrink-0 items-center gap-1 rounded-md border border-[#3a3a37] px-2.5 py-1 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                    :disabled="weeklySubmittingId !== null"
                    @click="cancelSaveWeeklyAsTemplate"
                  >
                    <X class="h-3 w-3" />
                    Cancel
                  </button>
                  <button
                    type="button"
                    class="flex shrink-0 items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-2.5 py-1 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
                    :disabled="weeklySubmittingId !== null || !weeklyTitleInputs[wp.id]?.trim()"
                    @click="handleSaveWeeklyAsTemplate(wp)"
                  >
                    <Check class="h-3 w-3" />
                    {{ weeklySubmittingId === wp.id ? 'Saving…' : 'Save' }}
                  </button>
                </div>
                <p v-if="weeklySubmitError[wp.id]" class="text-xs text-rose-300">
                  {{ weeklySubmitError[wp.id] }}
                </p>
              </div>

              <ul v-if="wp.days?.length" class="flex flex-col gap-1.5 pt-1">
                <li v-for="day in wp.days" :key="day.id" class="flex flex-col">
                  <button
                    type="button"
                    class="flex w-full items-center gap-3 rounded-md border border-[#3a3a37]/70 bg-[#181818] px-3 py-2 text-left transition-colors"
                    :class="[
                      day.isRest || day.exercises.length === 0
                        ? 'cursor-default'
                        : 'hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28]',
                      expandedDayKey === dayKey(day, wp.id) ? 'rounded-b-none border-b-0' : '',
                    ]"
                    :aria-expanded="expandedDayKey === dayKey(day, wp.id)"
                    @click="toggleDay(day, wp.id)"
                  >
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
                    <span class="flex-1 truncate text-sm text-white">
                      {{ day.label }}
                    </span>
                    <span
                      v-if="!day.isRest && day.exercises.length"
                      class="shrink-0 text-xs text-[#a0a09a] tabular-nums"
                    >
                      {{ day.exercises.length }} exercise{{ day.exercises.length === 1 ? '' : 's' }}
                    </span>
                    <ChevronDown
                      v-if="!day.isRest && day.exercises.length"
                      class="h-4 w-4 shrink-0 text-[#a0a09a] transition-transform"
                      :class="expandedDayKey === dayKey(day, wp.id) ? 'rotate-180' : ''"
                    />
                  </button>

                  <div
                    v-if="expandedDayKey === dayKey(day, wp.id)"
                    class="rounded-b-md border border-t border-[#ff6f14]/40 bg-[#0f0f0e] px-4 py-3"
                  >
                    <h5
                      class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#a0a09a]"
                    >
                      Exercises
                    </h5>
                    <ul class="flex flex-col divide-y divide-[#2a2a28]">
                      <li
                        v-for="ex in day.exercises"
                        :key="ex.id"
                        class="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0"
                      >
                        <span class="truncate text-sm font-medium text-white">
                          {{ ex.exerciseName }}
                        </span>
                        <span class="shrink-0 text-sm text-[#d4d4cf] tabular-nums">
                          {{ ex.sets }} × {{ ex.reps }}
                          <template v-if="ex.weight != null">
                            <span class="text-[#a0a09a]">·</span>
                            {{ ex.weight }}{{ ex.weightUnit }}
                          </template>
                          <span class="text-[#a0a09a]">·</span>
                          <span class="text-[#a0a09a]">{{ ex.restSeconds }}s rest</span>
                        </span>
                      </li>
                    </ul>
                  </div>
                </li>
              </ul>
            </li>
          </ul>

          <!-- Flat-mode schedule. Same expansion pattern, but the days
               hang directly off the plan rather than off a weekly. -->
          <ul v-else-if="plan.flatDays?.length" class="flex flex-col gap-1.5">
            <li v-for="day in plan.flatDays" :key="day.id" class="flex flex-col">
              <button
                type="button"
                class="flex w-full items-center gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-3 py-2 text-left transition-colors"
                :class="[
                  day.isRest || day.exercises.length === 0
                    ? 'cursor-default'
                    : 'hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28]',
                  expandedDayKey === dayKey(day, null) ? 'rounded-b-none border-b-0' : '',
                ]"
                :aria-expanded="expandedDayKey === dayKey(day, null)"
                @click="toggleDay(day, null)"
              >
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
                <span class="flex-1 truncate text-sm text-white">{{ day.label }}</span>
                <span
                  v-if="!day.isRest && day.exercises.length"
                  class="shrink-0 text-xs text-[#a0a09a] tabular-nums"
                >
                  {{ day.exercises.length }} exercise{{ day.exercises.length === 1 ? '' : 's' }}
                </span>
                <ChevronDown
                  v-if="!day.isRest && day.exercises.length"
                  class="h-4 w-4 shrink-0 text-[#a0a09a] transition-transform"
                  :class="expandedDayKey === dayKey(day, null) ? 'rotate-180' : ''"
                />
              </button>

              <div
                v-if="expandedDayKey === dayKey(day, null)"
                class="rounded-b-md border border-t border-[#ff6f14]/40 bg-[#0f0f0e] px-4 py-3"
              >
                <h5 class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[#a0a09a]">
                  Exercises
                </h5>
                <ul class="flex flex-col divide-y divide-[#2a2a28]">
                  <li
                    v-for="ex in day.exercises"
                    :key="ex.id"
                    class="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0"
                  >
                    <span class="truncate text-sm font-medium text-white">
                      {{ ex.exerciseName }}
                    </span>
                    <span class="shrink-0 text-sm text-[#d4d4cf] tabular-nums">
                      {{ ex.sets }} × {{ ex.reps }}
                      <template v-if="ex.weight != null">
                        <span class="text-[#a0a09a]">·</span>
                        {{ ex.weight }}{{ ex.weightUnit }}
                      </template>
                      <span class="text-[#a0a09a]">·</span>
                      <span class="text-[#a0a09a]">{{ ex.restSeconds }}s rest</span>
                    </span>
                  </li>
                </ul>
              </div>
            </li>
          </ul>
        </section>
      </div>

      <div class="flex flex-col gap-2 border-t border-[#3a3a37] bg-[#181818] px-4 py-3 sm:px-6">
        <p
          v-if="successMessage"
          class="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200"
        >
          {{ successMessage }}
        </p>
        <p
          v-if="submitError"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          {{ submitError }}
        </p>

        <div v-if="showingTitleInput" class="flex items-end gap-2">
          <div class="flex flex-1 flex-col gap-1">
            <label class="text-xs text-[#a0a09a]" for="save-as-template-title">
              Template title
            </label>
            <Input
              id="save-as-template-title"
              v-model="newTitle"
              class="bg-[#2a2a28] border-[#3a3a37] text-sm text-white"
            />
          </div>
          <button
            type="button"
            class="flex shrink-0 items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="submitting"
            @click="cancelSaveAsTemplate"
          >
            <X class="h-3.5 w-3.5" />
            Cancel
          </button>
          <button
            type="button"
            class="flex shrink-0 items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="submitting || !newTitle.trim()"
            @click="handleSaveAsTemplate"
          >
            <Check class="h-3.5 w-3.5" />
            {{ submitting ? 'Saving…' : 'Save' }}
          </button>
        </div>

        <div v-else class="flex items-center justify-between gap-2">
          <button
            v-if="canSaveAsTemplate"
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14]/60 bg-[#ff6f14]/5 px-3 py-1.5 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#ff6f14]/15"
            @click="startSaveAsTemplate"
          >
            <Bookmark class="h-3.5 w-3.5" />
            Save as template
          </button>
          <span v-else class="text-xs text-[#a0a09a]">
            This structure already matches an existing template.
          </span>
          <button
            type="button"
            class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
            @click="open = false"
          >
            Close
          </button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
