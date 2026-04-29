<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FilePlus,
  Library,
  PartyPopper,
} from 'lucide-vue-next'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { providePlanForm } from '@/components/plan-form/usePlanForm'
import StepOneBasics from '@/components/plan-form/StepOneBasics.vue'
import StepTwoDays from '@/components/plan-form/StepTwoDays.vue'
import PlanEditForm from '@/components/PlanEditForm.vue'
import AssignNowPanel from '@/components/AssignNowPanel.vue'
import { usePlanTemplatesStore } from '@/stores/planTemplates'
import { usePlansStore } from '@/stores/plans'
import { templateToPlan } from '@/lib/templateAdapter'
import axios from 'axios'
import type { Plan } from '@/types/plan'

const props = defineProps<{
  open: boolean
  preselectedUserIds?: string[]
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

type Path = 'custom' | 'existing'
type Step =
  | 'choose-path'
  | 'custom-basics'
  | 'custom-workouts'
  | 'existing-pick'
  | 'existing-review'
  | 'pick-users'
  | 'done'

const internalOpen = computed({
  get: () => props.open,
  set: (v) => emit('update:open', v),
})

const plansStore = usePlanTemplatesStore()
const livePlansStore = usePlansStore()
const { templates: plans } = storeToRefs(plansStore)

const form = providePlanForm()

const step = ref<Step>('choose-path')
const path = ref<Path | null>(null)
const pickedExistingPlanId = ref<string | null>(null)
const finalPlanTitle = ref('')

const stepOrder = computed<Step[]>(() => {
  if (path.value === 'custom') {
    return ['choose-path', 'custom-basics', 'custom-workouts', 'pick-users', 'done']
  }
  if (path.value === 'existing') {
    return ['choose-path', 'existing-pick', 'existing-review', 'pick-users', 'done']
  }
  return ['choose-path']
})

const currentIndex = computed(() => stepOrder.value.indexOf(step.value))
const totalSteps = computed(() => stepOrder.value.length - 1)
const progressPercent = computed(() =>
  totalSteps.value === 0 ? 0 : (currentIndex.value / totalSteps.value) * 100,
)

const stepTitle = computed(() => {
  switch (step.value) {
    case 'choose-path':
      return 'Pick a starting point'
    case 'custom-basics':
      return 'Plan basics'
    case 'custom-workouts':
      return 'Plan workouts'
    case 'existing-pick':
      return 'Pick a template plan'
    case 'existing-review':
      return 'Review & edit'
    case 'pick-users':
      return 'Assign to users'
    case 'done':
      return 'Done'
    default:
      return ''
  }
})

const canAdvance = computed(() => {
  switch (step.value) {
    case 'choose-path':
      return path.value !== null
    case 'custom-basics':
      return form.isStepValid(1) && !plansStore.titleExists(form.name.value.trim())
    case 'custom-workouts':
      return form.isStepValid(2)
    case 'existing-pick':
      return pickedExistingPlanId.value !== null
    case 'existing-review':
      return form.isStepValid(1) && form.isStepValid(2)
    default:
      return true
  }
})

const next = () => {
  if (!canAdvance.value) return
  switch (step.value) {
    case 'choose-path':
      if (path.value === 'custom') step.value = 'custom-basics'
      else step.value = 'existing-pick'
      break
    case 'custom-basics':
      step.value = 'custom-workouts'
      break
    case 'custom-workouts':
      step.value = 'pick-users'
      break
    case 'existing-pick':
      hydrateFromPickedPlan()
      step.value = 'existing-review'
      break
    case 'existing-review':
      step.value = 'pick-users'
      break
  }
}

const back = () => {
  const prevStep = stepOrder.value[currentIndex.value - 1]
  if (prevStep) step.value = prevStep
}

const hydrateFromPickedPlan = () => {
  if (!pickedExistingPlanId.value) return
  const t = plansStore.getById(pickedExistingPlanId.value)
  if (t) form.loadPlan(templateToPlan(t))
}

const personalPlanTitle = (): string => form.name.value.trim()

const prepareAssignment = async (): Promise<string> => {
  const planPayload = form.buildPlanPayload()
  planPayload.title = personalPlanTitle()

  const res = await axios.post<Plan>(`${import.meta.env.VITE_API_URL}/api/plans`, planPayload)
  const newPlan = res.data
  livePlansStore.ingestPlan(newPlan)
  finalPlanTitle.value = newPlan.title
  return newPlan.id
}

const onAssignDone = () => {
  step.value = 'done'
}

const closeDialog = () => {
  internalOpen.value = false
}

watch(internalOpen, (isOpen) => {
  if (!isOpen) {
    setTimeout(() => {
      form.reset()
      step.value = 'choose-path'
      path.value = null
      pickedExistingPlanId.value = null
      finalPlanTitle.value = ''
    }, 250)
  }
})
</script>

<template>
  <Dialog v-model:open="internalOpen">
    <DialogContent
      class="dark sm:max-w-3xl max-h-[90vh] overflow-y-auto bg-[#181818] text-white border-[#3a3a37] scrollbar-thin"
    >
      <DialogHeader>
        <DialogTitle class="text-2xl text-white">{{ stepTitle }}</DialogTitle>
      </DialogHeader>

      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between text-xs text-[#a0a09a]">
          <span class="font-medium uppercase">
            Step {{ Math.max(1, currentIndex) }} of {{ totalSteps === 0 ? 4 : totalSteps }}
          </span>
          <span>{{ Math.round(progressPercent) }}%</span>
        </div>
        <Progress
          :model-value="progressPercent"
          class="h-1.5 bg-[#2a2a28] *:data-[slot=progress-indicator]:bg-[#ff6f14]"
        />
      </div>

      <template v-if="step === 'choose-path'">
        <div class="flex flex-col gap-3">
          <p class="text-sm text-[#d4d4cf]">How do you want to build the plan you're assigning?</p>
          <div class="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              class="flex flex-col items-start gap-2 rounded-md border-2 px-4 py-4 text-left transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
              :class="
                path === 'existing'
                  ? 'border-[#ff6f14] bg-[#ff6f14]/10'
                  : 'border-[#3a3a37] bg-[#1f1f1d] hover:border-[#55554f]'
              "
              @click="path = 'existing'"
            >
              <Library class="h-5 w-5 text-[#ff6f14]" />
              <span class="text-sm font-semibold text-white">Use an existing template</span>
              <span class="text-xs text-[#a0a09a]">
                Pick from your saved templates. You can review or modify before assigning.
              </span>
            </button>
            <button
              type="button"
              class="flex flex-col items-start gap-2 rounded-md border-2 px-4 py-4 text-left transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
              :class="
                path === 'custom'
                  ? 'border-[#ff6f14] bg-[#ff6f14]/10'
                  : 'border-[#3a3a37] bg-[#1f1f1d] hover:border-[#55554f]'
              "
              @click="path = 'custom'"
            >
              <FilePlus class="h-5 w-5 text-[#ff6f14]" />
              <span class="text-sm font-semibold text-white">Build a custom plan</span>
              <span class="text-xs text-[#a0a09a]">
                Author a new plan from scratch. You can promote it to a template later.
              </span>
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="step === 'custom-basics'">
        <StepOneBasics />
        <p
          v-if="form.name.value.trim() && plansStore.titleExists(form.name.value.trim())"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          A plan named "{{ form.name.value }}" already exists. Pick a different name.
        </p>
      </template>

      <template v-else-if="step === 'custom-workouts'">
        <StepTwoDays />
      </template>

      <template v-else-if="step === 'existing-pick'">
        <div class="flex flex-col gap-2">
          <p class="text-sm text-[#d4d4cf]">Pick the template you want to assign:</p>
          <ul
            class="flex flex-col gap-1.5 max-h-96 overflow-y-auto rounded-md border border-[#3a3a37] bg-[#1f1f1d] p-2 scrollbar-thin"
          >
            <p v-if="!plans.length" class="py-4 text-center text-xs text-[#a0a09a]">
              No templates yet. Switch back and pick "Build a custom plan."
            </p>
            <button
              v-for="p in plans"
              :key="p.id"
              type="button"
              class="flex items-center gap-3 rounded-md border-2 px-3 py-2 text-left transition-colors hover:cursor-pointer focus:outline-none focus:ring-2"
              :class="
                pickedExistingPlanId === p.id
                  ? 'border-[#ff6f14] bg-[#ff6f14]/10'
                  : 'border-transparent hover:border-[#55554f] hover:bg-[#2a2a28]'
              "
              @click="pickedExistingPlanId = p.id"
            >
              <CheckCircle2
                v-if="pickedExistingPlanId === p.id"
                class="h-4 w-4 shrink-0 text-[#ff6f14]"
              />
              <span class="flex-1 truncate text-sm font-medium text-white">{{ p.title }}</span>
              <span
                class="shrink-0 rounded-full border border-[#ff6f14] bg-[#1f1f1d] px-2 py-0.5 text-xs text-[#ff6f14]"
              >
                {{ p.duration }} {{ p.durationType }}
              </span>
            </button>
          </ul>
        </div>
      </template>

      <template v-else-if="step === 'existing-review'">
        <p class="text-xs text-[#a0a09a]">
          Edit anything you want — your changes stay private to this assignment unless you promote
          the result to a template later.
        </p>
        <PlanEditForm />
      </template>

      <template v-else-if="step === 'pick-users'">
        <AssignNowPanel
          :prepare-assignment="prepareAssignment"
          :preselected-user-ids="preselectedUserIds"
          @done="onAssignDone"
        />
      </template>

      <template v-else-if="step === 'done'">
        <div class="flex flex-col items-center gap-3 py-6 text-center">
          <PartyPopper class="h-10 w-10 text-[#ff6f14]" />
          <p class="text-base font-medium text-white">All done.</p>
          <p class="text-xs text-[#a0a09a]">{{ finalPlanTitle }} has been processed.</p>
        </div>
      </template>

      <div
        v-if="!['pick-users', 'done'].includes(step)"
        class="mt-2 flex items-center justify-between"
      >
        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="currentIndex <= 0"
          @click="back"
        >
          <ChevronLeft class="h-3.5 w-3.5" />
          Back
        </button>
        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!canAdvance"
          @click="next"
        >
          Next
          <ChevronRight class="h-3.5 w-3.5" />
        </button>
      </div>

      <div v-if="step === 'done'" class="mt-2 flex items-center justify-end">
        <button
          type="button"
          class="rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
          @click="closeDialog"
        >
          Close
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>
