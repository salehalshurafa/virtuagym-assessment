<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { CalendarIcon, Send, X } from 'lucide-vue-next'
import { parseDate } from '@internationalized/date'
import type { DateValue } from 'reka-ui'
import { Calendar } from '@/components/ui/calendar'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import BulkUserSelect from '@/components/BulkUserSelect.vue'
import AssignmentConflictPrompt, {
  type ConflictDecision,
  type ConflictInfo,
} from '@/components/AssignmentConflictPrompt.vue'
import PartialResultsBanner, { type ResultRow } from '@/components/PartialResultsBanner.vue'
import axios from 'axios'
import { useUsersStore } from '@/stores/users'
import type { BulkAssignResult } from '@/stores/users'
import { useActivePlansStore, type ActivePlanRow } from '@/stores/activePlans'
import { usePlansStore } from '@/stores/plans'

const props = defineProps<{
  planId?: string
  prepareAssignment?: () => Promise<string>
  preselectedUserIds?: string[]
}>()
const emit = defineEmits<{ done: [] }>()

const usersStore = useUsersStore()
const { activeUsers } = storeToRefs(usersStore)
const activePlansStore = useActivePlansStore()
const livePlansStore = usePlansStore()

type Phase = 'pick' | 'resolve' | 'results'

const phase = ref<Phase>('pick')
const startDate = ref<DateValue | undefined>(parseDate(todayIso()))
const datePopoverOpen = ref(false)
const selectedUserIds = ref<string[]>([...(props.preselectedUserIds ?? [])])
const pendingConflicts = ref<ConflictInfo[]>([])
const lastResults = ref<BulkAssignResult[]>([])
const submitting = ref(false)

function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const startDateDisplay = computed(() => {
  const d = startDate.value
  if (!d) return ''
  return new Date(d.year, d.month - 1, d.day).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
})

const dateValueToIso = (d: { year: number; month: number; day: number }): string =>
  `${d.year}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`

watch(
  () => startDate.value,
  (v) => {
    if (v) datePopoverOpen.value = false
  },
)

const detectConflicts = (userIds: string[]): ConflictInfo[] => {
  const conflicts: ConflictInfo[] = []
  for (const id of userIds) {
    const user = usersStore.getById(id)
    const status = user?.latestPlan?.status
    if (status === 'in-progress' || status === 'paused') {
      conflicts.push({
        userId: id,
        userName: `${user!.firstName} ${user!.lastName}`,
        currentPlanTitle: user!.latestPlan!.planTitle,
        currentPlanStatus: status,
      })
    }
  }
  return conflicts
}

interface BulkAssignResponse {
  planId: string
  results: BulkAssignResult[]
}

const planCreateError = ref<string | null>(null)

const runAssignment = async (forceReplaceUserIds: string[], skippedUserIds: string[] = []) => {
  if (!startDate.value || submitting.value) return
  const finalUserIds = selectedUserIds.value.filter((id) => !skippedUserIds.includes(id))
  const startIso = dateValueToIso(startDate.value)
  const apiBase = import.meta.env.VITE_API_URL

  submitting.value = true
  planCreateError.value = null
  try {
    let resolvedPlanId = props.planId ?? null
    if (!resolvedPlanId && props.prepareAssignment) {
      try {
        resolvedPlanId = await props.prepareAssignment()
      } catch (err) {
        console.error('prepareAssignment failed', err)
        planCreateError.value = "We couldn't save the plan. Please try again later."
        submitting.value = false
        return
      }
    }
    if (!resolvedPlanId) {
      planCreateError.value = 'No plan id available. Pass either planId or prepareAssignment.'
      submitting.value = false
      return
    }

    let apiResults: BulkAssignResult[] = []
    if (finalUserIds.length > 0) {
      const res = await axios.post<BulkAssignResponse>(`${apiBase}/api/assignments/bulk`, {
        planId: resolvedPlanId,
        startDate: startIso,
        userIds: finalUserIds,
        forceReplaceUserIds,
      })
      apiResults = res.data.results
    }

    const successfulResults = apiResults.filter((r) => r.success)

    await Promise.all(
      successfulResults.map((r) => usersStore.refetchUser(r.userId).catch(() => undefined)),
    )

    if (successfulResults.length > 0) {
      const livePlan = livePlansStore.getById(resolvedPlanId)
      if (livePlan) {
        const newAssignees = successfulResults
          .map((r) => usersStore.getById(r.userId))
          .filter((u): u is NonNullable<typeof u> => !!u)
          .map((u) => ({
            id: u.id,
            firstName: u.firstName,
            lastName: u.lastName,
          }))

        const existingRow = activePlansStore.items.find((r) => r.id === livePlan.id)
        const mergedAssignees = existingRow
          ? [
              ...existingRow.assignees.filter((a) => !newAssignees.some((n) => n.id === a.id)),
              ...newAssignees,
            ]
          : newAssignees

        const optimisticRow: ActivePlanRow = {
          ...livePlan,
          assignees: mergedAssignees,
          statusSummary: existingRow?.statusSummary ?? 'in-progress',
        }
        activePlansStore.ingestActivePlan(optimisticRow)
      }
      activePlansStore.refresh().catch(() => undefined)
    }

    const merged: BulkAssignResult[] = [
      ...apiResults,
      ...skippedUserIds.map((id) => ({
        userId: id,
        success: false,
        reason: 'SKIPPED_BY_USER',
      })),
    ]
    lastResults.value = merged
    phase.value = 'results'
  } catch (err) {
    console.error('bulk assign failed', err)
    lastResults.value = [
      ...finalUserIds.map((id) => ({
        userId: id,
        success: false,
        reason: 'API_ERROR',
      })),
      ...skippedUserIds.map((id) => ({
        userId: id,
        success: false,
        reason: 'SKIPPED_BY_USER',
      })),
    ]
    phase.value = 'results'
  } finally {
    submitting.value = false
  }
}

const onSubmit = async () => {
  if (!startDate.value || selectedUserIds.value.length === 0) return
  const conflicts = detectConflicts(selectedUserIds.value)
  if (conflicts.length === 0) {
    await runAssignment([])
    return
  }
  pendingConflicts.value = conflicts
  phase.value = 'resolve'
}

const onConflictsDecided = async (decisions: Record<string, ConflictDecision>) => {
  const force: string[] = []
  const skip: string[] = []
  for (const [userId, decision] of Object.entries(decisions)) {
    if (decision === 'force') force.push(userId)
    else skip.push(userId)
  }
  await runAssignment(force, skip)
}

const onConflictsCancelled = () => {
  phase.value = 'pick'
  pendingConflicts.value = []
}

const resultRows = computed<ResultRow[]>(() =>
  lastResults.value.map((r) => {
    const user = usersStore.getById(r.userId)
    const label = user ? `${user.firstName} ${user.lastName}` : r.userId
    if (r.success) {
      return { label, success: true }
    }
    let detail = r.reason ?? 'Unknown error'
    if (r.reason === 'CONFLICT_ACTIVE_PLAN' && r.conflictWith) {
      detail = `On "${r.conflictWith.planTitle}"`
    } else if (r.reason === 'SKIPPED_BY_USER') {
      detail = 'Skipped'
    } else if (r.reason === 'DB_ERROR') {
      detail = "Couldn't be saved — try again"
    } else if (r.reason === 'API_ERROR') {
      detail = 'Network error'
    } else if (r.reason === 'USER_NOT_FOUND') {
      detail = 'User no longer exists'
    }
    return { label, success: false, detail }
  }),
)

const reset = () => {
  phase.value = 'pick'
  selectedUserIds.value = [...(props.preselectedUserIds ?? [])]
  pendingConflicts.value = []
  lastResults.value = []
  startDate.value = parseDate(todayIso())
}

const onDone = () => {
  emit('done')
  reset()
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <template v-if="phase === 'pick'">
      <section class="flex flex-col gap-2">
        <label class="text-sm font-medium text-white">Start date</label>
        <div class="flex items-center gap-2">
          <Popover v-model:open="datePopoverOpen">
            <PopoverTrigger as-child>
              <div class="relative w-56">
                <Input
                  :model-value="startDateDisplay"
                  readonly
                  placeholder="Pick a start date"
                  aria-label="Pick a start date"
                  class="cursor-pointer bg-[#2a2a28] border-[#3a3a37] pr-9 text-white"
                />
                <span
                  class="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-[#a0a09a]"
                >
                  <CalendarIcon class="h-3.5 w-3.5" />
                </span>
              </div>
            </PopoverTrigger>
            <PopoverContent
              class="dark w-auto p-2 bg-[#181818] text-white border-[#3a3a37]"
              align="start"
            >
              <Calendar
                class="flex flex-col gap-5"
                :model-value="startDate as unknown as never"
                @update:model-value="(v) => (startDate = v as DateValue | undefined)"
              />
            </PopoverContent>
          </Popover>
          <button
            v-if="startDate"
            type="button"
            class="grid h-9 w-9 place-items-center rounded-md border border-[#3a3a37] text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
            aria-label="Clear start date"
            @click="startDate = undefined"
          >
            <X class="h-3.5 w-3.5" />
          </button>
        </div>
      </section>

      <section class="flex flex-col gap-2">
        <label class="text-sm font-medium text-white">Assign to users</label>
        <BulkUserSelect v-model="selectedUserIds" :users="activeUsers" />
      </section>

      <p
        v-if="planCreateError"
        class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
      >
        {{ planCreateError }}
      </p>

      <div class="flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
          @click="emit('done')"
        >
          Skip for now
        </button>
        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!startDate || selectedUserIds.length === 0 || submitting"
          @click="onSubmit"
        >
          <Send class="h-3.5 w-3.5" />
          {{
            submitting
              ? 'Assigning…'
              : `Assign ${selectedUserIds.length} user${selectedUserIds.length === 1 ? '' : 's'}`
          }}
        </button>
      </div>
    </template>

    <template v-else-if="phase === 'resolve'">
      <AssignmentConflictPrompt
        :conflicts="pendingConflicts"
        :submitting="submitting"
        @decided="onConflictsDecided"
        @cancel="onConflictsCancelled"
      />
    </template>

    <template v-else>
      <PartialResultsBanner
        :results="resultRows"
        :success-heading="`Assigned ${resultRows.filter((r) => r.success).length} user${
          resultRows.filter((r) => r.success).length === 1 ? '' : 's'
        }.`"
      />
      <div class="flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
          @click="reset"
        >
          Assign more
        </button>
        <button
          type="button"
          class="rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
          @click="onDone"
        >
          Done
        </button>
      </div>
    </template>
  </div>
</template>
