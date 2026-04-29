<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, ChevronLeft, ChevronRight, PartyPopper, Plus, Send } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import StepOneBasics from '@/components/plan-form/StepOneBasics.vue'
import StepTwoDays from '@/components/plan-form/StepTwoDays.vue'
import { providePlanForm } from '@/components/plan-form/usePlanForm'
import { usePlanTemplatesStore } from '@/stores/planTemplates'
import AssignNowPanel from '@/components/AssignNowPanel.vue'
import { planPayloadToTemplateUpdate, templateToPlan } from '@/lib/templateAdapter'
import type { PlanTemplate } from '@/types/template'

const props = defineProps<{
  prefill?: PlanTemplate | null
  open?: boolean
  noTrigger?: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const TOTAL_STEPS = 2

type Phase = 'wizard' | 'success' | 'assign'

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

const open = internalOpen

const currentStep = ref(1)
const phase = ref<Phase>('wizard')
const savedPlanId = ref<string | null>(null)
const savedPlanTitle = ref('')
const submitting = ref(false)
const saveError = ref<string | null>(null)

const form = providePlanForm()
const plansStore = usePlanTemplatesStore()

const progressPercent = computed(() => (currentStep.value / TOTAL_STEPS) * 100)
const canAdvance = computed(() => form.isStepValid(currentStep.value))
const isLastStep = computed(() => currentStep.value === TOTAL_STEPS)

const titleConflict = computed(() => {
  const t = form.name.value.trim()
  if (!t) return false
  return plansStore.titleExists(t)
})

const canSave = computed(
  () => canAdvance.value && form.isStepValid(1) && form.isStepValid(2) && !titleConflict.value,
)

const nextStep = () => {
  if (canAdvance.value && currentStep.value < TOTAL_STEPS) currentStep.value++
}
const prevStep = () => {
  if (currentStep.value > 1) currentStep.value--
}

const handleSave = () => {
  if (!canSave.value || submitting.value) return
  commitPlan()
}

const commitPlan = async () => {
  if (submitting.value) return
  submitting.value = true
  saveError.value = null
  try {
    const planPayload = form.buildPlanPayload()
    const templatePayload = {
      title: planPayload.title,
      duration: planPayload.duration,
      durationType: planPayload.durationType,
      imageUrl: planPayload.imageUrl,
      workoutDaysPerWeek: planPayload.workoutDaysPerWeek,
      ...planPayloadToTemplateUpdate(planPayload),
    }

    const res = await axios.post<PlanTemplate>(
      `${import.meta.env.VITE_API_URL}/api/plan-templates`,
      templatePayload,
    )
    plansStore.ingestTemplate(res.data)
    savedPlanId.value = res.data.id
    savedPlanTitle.value = res.data.title
    phase.value = 'success'
  } catch (err) {
    console.error('failed to save plan template', err)
    saveError.value = "We couldn't save the plan template. Please try again later."
  } finally {
    submitting.value = false
  }
}

const goToAssign = () => {
  phase.value = 'assign'
}

const onAssignDone = () => {
  closeDialog()
}

const closeDialog = () => {
  open.value = false
}

watch(open, (isOpen) => {
  if (isOpen) {
    if (props.prefill) {
      form.loadPlan(templateToPlan(props.prefill))
      const baseTitle = (props.prefill.title ?? '').trim() || 'Untitled plan'
      form.name.value = baseTitle.endsWith('(copy)') ? baseTitle : `${baseTitle} (copy)`
    }
  } else {
    form.reset()
    currentStep.value = 1
    phase.value = 'wizard'
    savedPlanId.value = null
    savedPlanTitle.value = ''
    submitting.value = false
    saveError.value = null
  }
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger v-if="!noTrigger" as-child>
      <button
        type="button"
        class="flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
        aria-label="Add plan"
      >
        <Plus class="h-3.5 w-3.5" />
        Add
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-3xl max-h-[90vh] overflow-y-auto bg-[#181818] text-white border-[#3a3a37] scrollbar-thin"
    >
      <template v-if="phase === 'wizard'">
        <DialogHeader>
          <DialogTitle class="text-2xl text-white">
            {{ prefill ? 'Fork plan template' : 'New Workout Plan' }}
          </DialogTitle>
        </DialogHeader>

        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between text-xs text-[#a0a09a]">
            <span class="font-medium uppercase">Step {{ currentStep }} of {{ TOTAL_STEPS }}</span>
            <span>{{ Math.round(progressPercent) }}%</span>
          </div>
          <Progress
            :model-value="progressPercent"
            class="h-1.5 bg-[#2a2a28] *:data-[slot=progress-indicator]:bg-[#ff6f14]"
          />
        </div>

        <StepOneBasics v-if="currentStep === 1" />
        <StepTwoDays v-else-if="currentStep === 2" />

        <p
          v-if="currentStep === 1 && titleConflict"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          A plan named "{{ form.name.value }}" already exists. Pick a different name.
        </p>

        <div class="mt-2 flex items-center justify-between">
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            :disabled="currentStep === 1"
            @click="prevStep"
          >
            <ChevronLeft class="h-3.5 w-3.5" />
            Back
          </button>
          <button
            v-if="!isLastStep"
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canAdvance || titleConflict"
            @click="nextStep"
          >
            Next
            <ChevronRight class="h-3.5 w-3.5" />
          </button>
          <button
            v-else
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canSave || submitting"
            @click="handleSave"
          >
            <Check class="h-3.5 w-3.5" />
            {{ submitting ? 'Saving…' : 'Save plan' }}
          </button>
        </div>
        <p
          v-if="saveError"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          {{ saveError }}
        </p>
      </template>

      <template v-else-if="phase === 'success'">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2 text-2xl text-white">
            <PartyPopper class="h-6 w-6 text-[#ff6f14]" />
            Plan saved
          </DialogTitle>
        </DialogHeader>
        <div class="flex flex-col gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3">
          <p class="text-sm text-white">
            <strong>{{ savedPlanTitle }}</strong> is now available as a template. What's next?
          </p>
          <ul class="flex flex-col gap-1 text-xs text-[#a0a09a]">
            <li>Assign it to one or more users now, or</li>
            <li>Just close — the plan is saved and re-usable.</li>
          </ul>
        </div>

        <div class="mt-2 flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
            @click="closeDialog"
          >
            Done
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
            @click="goToAssign"
          >
            <Send class="h-3.5 w-3.5" />
            Assign now
          </button>
        </div>
      </template>

      <template v-else-if="phase === 'assign' && savedPlanId">
        <DialogHeader>
          <DialogTitle class="text-2xl text-white">Assign "{{ savedPlanTitle }}"</DialogTitle>
        </DialogHeader>
        <AssignNowPanel :plan-id="savedPlanId" @done="onAssignDone" />
      </template>
    </DialogContent>
  </Dialog>
</template>
