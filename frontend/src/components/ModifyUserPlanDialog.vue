<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, ChevronLeft, PartyPopper } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import PlanEditForm from '@/components/PlanEditForm.vue'
import { providePlanForm } from '@/components/plan-form/usePlanForm'
import { usePlansStore } from '@/stores/plans'
import { useUsersStore } from '@/stores/users'
import { useActivePlansStore } from '@/stores/activePlans'
import type { Plan } from '@/types/plan'

const props = defineProps<{ userId: string; open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const plansStore = usePlansStore()
const usersStore = useUsersStore()
const activePlansStore = useActivePlansStore()
const form = providePlanForm()

const internalOpen = computed({
  get: () => props.open,
  set: (v) => emit('update:open', v),
})

type Phase = 'edit' | 'apply-question' | 'done'
const phase = ref<Phase>('edit')

const applyToOthers = ref<boolean | null>(null)

const finalPlanTitle = ref('')

const submitting = ref(false)
const submitError = ref<string | null>(null)

const user = computed(() => usersStore.getById(props.userId))

const currentPlan = computed<Plan | null>(() => {
  const lp = user.value?.latestPlan
  if (!lp) return null
  return {
    id: lp.planId,
    title: lp.planTitle,
    duration: lp.duration,
    durationType: lp.durationType,
    imageUrl: lp.imageUrl ?? null,
    workoutDaysPerWeek: lp.workoutDaysPerWeek ?? null,
    archived: false,
    userCount: 0,
    weeklyPlans: lp.weeklyPlans
      ? lp.weeklyPlans.map((wp) => ({
          id: wp.id,
          planId: wp.planId,
          label: wp.label,
          weekFrequency: wp.weekFrequency,
          orderIndex: wp.orderIndex,
          days: wp.days.map((d) => ({
            id: d.id,
            label: d.label,
            isRest: d.isRest,
            orderIndex: d.orderIndex,
            exercises: d.exercises.map((e) => ({
              id: e.id,
              exerciseId: e.exerciseId ?? null,
              exerciseName: e.exerciseName,
              sets: e.sets,
              reps: e.reps,
              weight: e.weight ?? null,
              weightUnit: e.weightUnit,
              restSeconds: e.restSeconds,
              orderIndex: e.orderIndex,
            })),
          })),
        }))
      : null,
    flatDays: lp.flatDays
      ? lp.flatDays.map((d) => ({
          id: d.id,
          label: d.label,
          isRest: d.isRest,
          orderIndex: d.orderIndex,
          exercises: d.exercises.map((e) => ({
            id: e.id,
            exerciseId: e.exerciseId ?? null,
            exerciseName: e.exerciseName,
            sets: e.sets,
            reps: e.reps,
            weight: e.weight ?? null,
            weightUnit: e.weightUnit,
            restSeconds: e.restSeconds,
            orderIndex: e.orderIndex,
          })),
        }))
      : null,
  }
})

const otherAssignees = computed(() => {
  const planId = user.value?.latestPlan?.planId
  if (!planId) return []
  return usersStore.users.filter(
    (u) =>
      u.id !== props.userId &&
      !u.removed &&
      u.latestPlan?.planId === planId &&
      (u.latestPlan?.status === 'in-progress' || u.latestPlan?.status === 'paused'),
  )
})

const hasOtherAssignees = computed(() => otherAssignees.value.length > 0)

const resetState = () => {
  phase.value = 'edit'
  applyToOthers.value = null
  finalPlanTitle.value = ''
  submitting.value = false
  submitError.value = null
}

watch(
  () => [props.open, props.userId],
  ([isOpen]) => {
    if (isOpen && currentPlan.value) {
      form.loadPlan(currentPlan.value)
      resetState()
    }
  },
  { immediate: true },
)

const formIsValid = computed(() => form.isStepValid(1) && form.isStepValid(2))

const onProceedToSave = () => {
  if (!formIsValid.value) return
  if (!form.changesMade.value) {
    internalOpen.value = false
    return
  }

  if (!hasOtherAssignees.value) {
    void runApplyToAll()
    return
  }

  phase.value = 'apply-question'
}

const backToEdit = () => {
  phase.value = 'edit'
  submitError.value = null
}

const canConfirm = computed(() => {
  if (submitting.value) return false
  if (applyToOthers.value === null) return false
  return true
})

const buildPersonalTitle = (): string => {
  const u = user.value
  if (!u || !u.latestPlan) return form.name.value.trim()
  const userSuffix = ` — ${u.firstName} ${u.lastName}`
  const newBase = (form.name.value.trim() || u.latestPlan.planTitle).trim()
  const baseWithoutSuffix = newBase.endsWith(userSuffix)
    ? newBase.slice(0, -userSuffix.length).trimEnd()
    : newBase
  return `${baseWithoutSuffix}${userSuffix}`
}

const runApplyToAll = async () => {
  const u = user.value
  if (!u || !u.latestPlan) return
  const lp = u.latestPlan
  const apiBase = import.meta.env.VITE_API_URL

  submitting.value = true
  submitError.value = null
  try {
    const payload = form.buildPlanPayload()
    payload.title = (form.name.value.trim() || lp.planTitle).trim()

    const res = await axios.patch<Plan>(`${apiBase}/api/plans/${lp.planId}`, payload)
    plansStore.ingestPlan(res.data)

    const refetchIds = [u.id, ...otherAssignees.value.map((o) => o.id)]
    await Promise.all(refetchIds.map((id) => usersStore.refetchUser(id).catch(() => undefined)))
    activePlansStore.refresh().catch(() => undefined)
    finalPlanTitle.value = res.data.title
    phase.value = 'done'
  } catch (err) {
    console.error('failed to apply plan modifications (all)', err)
    submitError.value = "We couldn't save your changes. Please try again later."
  } finally {
    submitting.value = false
  }
}

const runApplyToCurrentOnly = async () => {
  const u = user.value
  if (!u || !u.latestPlan) return
  const lp = u.latestPlan
  const apiBase = import.meta.env.VITE_API_URL

  submitting.value = true
  submitError.value = null
  try {
    const payload = form.buildPlanPayload()
    payload.title = buildPersonalTitle()

    const planRes = await axios.post<Plan>(`${apiBase}/api/plans`, payload)
    const newPlan = planRes.data
    plansStore.ingestPlan(newPlan)

    await axios.post(`${apiBase}/api/assignments/repoint-multi`, {
      planId: newPlan.id,
      assignmentIds: [lp.id],
    })

    await usersStore.refetchUser(u.id).catch(() => undefined)
    activePlansStore.refresh().catch(() => undefined)
    finalPlanTitle.value = newPlan.title
    phase.value = 'done'
  } catch (err) {
    console.error('failed to apply plan modifications (single)', err)
    submitError.value = "We couldn't save your changes. Please try again later."
  } finally {
    submitting.value = false
  }
}

const onConfirm = async () => {
  if (!canConfirm.value) return
  if (applyToOthers.value === true) {
    await runApplyToAll()
  } else if (applyToOthers.value === false) {
    await runApplyToCurrentOnly()
  }
}

const closeDialog = () => {
  internalOpen.value = false
}
</script>

<template>
  <Dialog v-model:open="internalOpen">
    <DialogContent
      v-if="user"
      class="dark sm:max-w-3xl max-h-[90vh] overflow-y-auto bg-[#181818] text-white border-[#3a3a37] scrollbar-thin"
    >
      <DialogHeader>
        <DialogTitle class="text-2xl text-white">
          <template v-if="phase === 'edit'">
            Modify plan for {{ user.firstName }} {{ user.lastName }}
          </template>
          <template v-else-if="phase === 'apply-question'">Apply to everyone?</template>
          <template v-else>Done</template>
        </DialogTitle>
      </DialogHeader>

      <template v-if="phase === 'edit'">
        <p class="text-xs text-[#a0a09a]">
          Editing
          <strong class="text-[#d4d4cf]">{{ user.latestPlan?.planTitle ?? '—' }}</strong
          >.
          <template v-if="hasOtherAssignees">
            {{
              otherAssignees.length === 1
                ? 'One other user is'
                : `${otherAssignees.length} other users are`
            }}
            currently on this plan — you'll choose next whether to apply the change to all of them
            or just to {{ user.firstName }}.
          </template>
          <template v-else>
            {{ user.firstName }} is the only user on this plan, so the change updates the live plan
            and assignment in place. Use "Save as template" from the active-plans dialog if you want
            a reusable copy for the gallery.
          </template>
        </p>
        <PlanEditForm />

        <p
          v-if="submitError && phase === 'edit'"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          {{ submitError }}
        </p>

        <div class="mt-2 flex items-center justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="submitting"
            @click="closeDialog"
          >
            Cancel
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!formIsValid || !form.changesMade.value || submitting"
            @click="onProceedToSave"
          >
            <Check class="h-3.5 w-3.5" />
            {{ submitting ? 'Saving…' : hasOtherAssignees ? 'Save modifications' : 'Save' }}
          </button>
        </div>
        <p v-if="!form.changesMade.value" class="text-right text-xs text-[#a0a09a]">
          Make a change to enable saving.
        </p>
      </template>

      <template v-else-if="phase === 'apply-question'">
        <section
          class="flex flex-col gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3"
        >
          <p class="text-sm font-medium text-white">
            <strong class="text-[#d4d4cf]">{{ user.latestPlan?.planTitle }}</strong> is currently
            assigned to
            {{
              otherAssignees.length === 1
                ? 'one other user'
                : `${otherAssignees.length} other users`
            }}
            besides {{ user.firstName }}. Should the change apply to everyone, or just to
            {{ user.firstName }}?
          </p>
          <ul class="flex flex-col gap-1 pl-2">
            <li v-for="o in otherAssignees" :key="o.id" class="text-xs text-[#a0a09a]">
              · {{ o.firstName }} {{ o.lastName }}
            </li>
          </ul>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md border-2 px-3 py-1.5 text-xs font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
              :class="
                applyToOthers === true
                  ? 'border-[#ff6f14] bg-[#ff6f14] text-white'
                  : 'border-[#ff6f14]/60 bg-[#ff6f14]/5 text-[#ff6f14] hover:bg-[#ff6f14]/15'
              "
              @click="applyToOthers = true"
            >
              <Check v-if="applyToOthers === true" class="h-3.5 w-3.5" />
              Apply to everyone
            </button>
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md border-2 px-3 py-1.5 text-xs font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
              :class="
                applyToOthers === false
                  ? 'border-white bg-white text-[#181818]'
                  : 'border-[#3a3a37]/60 bg-[#1f1f1d] text-[#d4d4cf] hover:bg-[#2a2a28]'
              "
              @click="applyToOthers = false"
            >
              <Check v-if="applyToOthers === false" class="h-3.5 w-3.5" />
              Only {{ user.firstName }}
            </button>
          </div>
          <p class="text-xs text-[#a0a09a]">
            <template v-if="applyToOthers === true">
              The existing live plan record will be updated and every active assignee will see the
              new structure on their next sync.
            </template>
            <template v-else-if="applyToOthers === false">
              A fresh personal plan will be created for {{ user.firstName }}, and only their
              assignment will be re-pointed at it. Other assignees stay on the original plan.
            </template>
            <template v-else>Pick an option to continue.</template>
          </p>
        </section>

        <p
          v-if="submitError"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          {{ submitError }}
        </p>

        <div class="mt-2 flex items-center justify-between gap-2">
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="submitting"
            @click="backToEdit"
          >
            <ChevronLeft class="h-3.5 w-3.5" />
            Back to edit
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canConfirm"
            @click="onConfirm"
          >
            <Check class="h-3.5 w-3.5" />
            {{ submitting ? 'Applying…' : 'Apply changes' }}
          </button>
        </div>
      </template>

      <template v-else>
        <div class="flex flex-col items-center gap-3 py-6 text-center">
          <PartyPopper class="h-10 w-10 text-[#ff6f14]" />
          <p class="text-base font-medium text-white">Modifications applied.</p>
          <p class="text-xs text-[#a0a09a]">
            <template v-if="applyToOthers === false">
              {{ user.firstName }} is now on
              <strong class="text-[#d4d4cf]">{{ finalPlanTitle }}</strong
              >. Other users are unaffected.
            </template>
            <template v-else-if="applyToOthers === true">
              Applied to {{ otherAssignees.length + 1 }} users on this plan.
            </template>
            <template v-else>
              Updated <strong class="text-[#d4d4cf]">{{ finalPlanTitle }}</strong> in place.
            </template>
          </p>
        </div>
        <div class="mt-2 flex items-center justify-end">
          <button
            type="button"
            class="rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
            @click="closeDialog"
          >
            Close
          </button>
        </div>
      </template>
    </DialogContent>
  </Dialog>
</template>
