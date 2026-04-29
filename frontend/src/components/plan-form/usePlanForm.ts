import { computed, inject, provide, ref, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import type { DurationType, Plan, PlanCreate, PlanDay, WeeklyWorkoutPlanCreate } from '@/types/plan'
import type { WeeklyPlan } from '@/types/weeklyPlan'
import { fileToDataUrl } from '@/lib/images'
import { createId } from './ids'

export type WeeklyOrigin = 'fresh' | 'from-template' | 'from-template-modified'

export interface WeeklyEntry {
  id: string
  label: string
  weekFrequency: number
  days: PlanDay[]
  origin: WeeklyOrigin
  sourceTemplateId?: string
  baseline?: string
}

export interface PlanFormState {
  name: Ref<string>
  imageFile: Ref<File | null>
  imagePreviewUrl: Ref<string>
  duration: Ref<number | null>
  durationType: Ref<DurationType>
  workoutDaysPerWeek: Ref<number | null>

  showWeeklyDaysQuestion: ComputedRef<boolean>
  isWeeklyMode: ComputedRef<boolean>
  totalDays: ComputedRef<number>
  totalWeeks: ComputedRef<number>

  weeklyPlans: Ref<WeeklyEntry[]>
  flatDays: Ref<PlanDay[]>

  rotationCycleLength: ComputedRef<number>

  setImageFile: (file: File | null) => Promise<void>
  imageError: Ref<string | null>
  initStep2: () => void
  toggleRest: (day: PlanDay) => void
  addExercise: (day: PlanDay) => void
  removeExercise: (day: PlanDay, exerciseId: string) => void
  copyDay: (sourceDayId: string, targetDayId: string, weeklyPlanId?: string) => void
  addWeeklyPlan: () => string
  removeWeeklyPlan: (planId: string) => void
  applyTemplate: (weekId: string, template: WeeklyPlan) => void
  isWeekModified: (weekId: string) => boolean
  getWeekStatus: (weekId: string) => WeeklyOrigin

  isStepValid: (step: number) => boolean
  changesMade: ComputedRef<boolean>
  reset: () => void
  loadPlan: (plan: Plan) => void
  buildPlanPayload: () => PlanCreate
}

const PlanFormKey: InjectionKey<PlanFormState> = Symbol('PlanForm')

const createEmptyDay = (label: string, orderIndex: number): PlanDay => ({
  id: createId(),
  label,
  isRest: false,
  orderIndex,
  exercises: [],
})

const createEmptyWeeklyEntry = (label: string): WeeklyEntry => ({
  id: createId(),
  label,
  weekFrequency: 1,
  days: Array.from({ length: 7 }, (_, i) => createEmptyDay(`Day ${i + 1}`, i)),
  origin: 'fresh',
})

const cloneStructure = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const weekSnapshot = (entry: { label: string; weekFrequency: number; days: PlanDay[] }): string =>
  JSON.stringify({
    label: entry.label,
    weekFrequency: entry.weekFrequency,
    days: entry.days.map((d) => ({
      label: d.label,
      isRest: d.isRest,
      orderIndex: d.orderIndex,
      exercises: d.exercises.map((e) => ({
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
  })

const dayToCreate = (d: PlanDay, orderIndex: number) => ({
  label: d.label,
  isRest: d.isRest,
  orderIndex,
  exercises: d.exercises.map((e, i) => ({
    exerciseId: e.exerciseId ?? null,
    exerciseName: e.exerciseName,
    sets: e.sets,
    reps: e.reps,
    weight: e.weight ?? null,
    weightUnit: e.weightUnit,
    restSeconds: e.restSeconds,
    orderIndex: i,
  })),
})

export const providePlanForm = (): PlanFormState => {
  const name = ref('')
  const imageFile = ref<File | null>(null)
  const imagePreviewUrl = ref('')
  const duration = ref<number | null>(null)
  const durationType = ref<DurationType>('weeks')
  const workoutDaysPerWeek = ref<number | null>(null)

  const weeklyPlans = ref<WeeklyEntry[]>([])
  const flatDays = ref<PlanDay[]>([])

  const imageError = ref<string | null>(null)

  const originalPlanInfo = ref<string | null>(null)

  const showWeeklyDaysQuestion = computed(() => {
    const d = duration.value ?? 0
    if (d <= 0) return false
    if (durationType.value !== 'days') return true
    return d % 7 === 0
  })

  const isWeeklyMode = computed(
    () => showWeeklyDaysQuestion.value && workoutDaysPerWeek.value !== null,
  )

  const totalDays = computed(() => {
    const d = duration.value ?? 0
    switch (durationType.value) {
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
    const d = duration.value ?? 0
    switch (durationType.value) {
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

  const rotationCycleLength = computed(() =>
    weeklyPlans.value.reduce((sum, p) => sum + Math.max(1, p.weekFrequency), 0),
  )

  const setImageFile = async (file: File | null) => {
    imageError.value = null
    if (file === null) {
      imageFile.value = null
      imagePreviewUrl.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      imageFile.value = file
      imagePreviewUrl.value = dataUrl
    } catch (err) {
      imageError.value = (err as Error).message
      imageFile.value = null
      imagePreviewUrl.value = ''
    }
  }

  const initStep2 = () => {
    if (isWeeklyMode.value) {
      if (weeklyPlans.value.length === 0) {
        weeklyPlans.value = [createEmptyWeeklyEntry('Weekly Workout Plan 1')]
      }
      flatDays.value = []
    } else {
      if (flatDays.value.length !== totalDays.value) {
        flatDays.value = Array.from({ length: totalDays.value }, (_, i) =>
          createEmptyDay(`Day ${i + 1}`, i),
        )
      }
      weeklyPlans.value = []
    }
  }

  const toggleRest = (day: PlanDay) => {
    day.isRest = !day.isRest
    if (day.isRest) day.exercises = []
  }

  const addExercise = (day: PlanDay) => {
    day.exercises.push({
      id: createId(),
      exerciseId: null,
      exerciseName: '',
      sets: 3,
      reps: 10,
      weight: null,
      weightUnit: 'kg',
      restSeconds: 60,
      orderIndex: day.exercises.length,
    })
  }

  const removeExercise = (day: PlanDay, exerciseId: string) => {
    day.exercises = day.exercises.filter((e) => e.id !== exerciseId)
  }

  const findDayInWeeklyPlan = (weeklyPlanId: string, dayId: string): PlanDay | undefined => {
    const plan = weeklyPlans.value.find((p) => p.id === weeklyPlanId)
    return plan?.days.find((d) => d.id === dayId)
  }

  const copyDay = (sourceDayId: string, targetDayId: string, weeklyPlanId?: string) => {
    if (!sourceDayId || !targetDayId) return

    let source: PlanDay | undefined
    let target: PlanDay | undefined
    if (weeklyPlanId) {
      source = findDayInWeeklyPlan(weeklyPlanId, sourceDayId)
      target = findDayInWeeklyPlan(weeklyPlanId, targetDayId)
    } else {
      source = flatDays.value.find((d) => d.id === sourceDayId)
      target = flatDays.value.find((d) => d.id === targetDayId)
    }

    if (!source || !target || source.id === target.id) return

    target.isRest = source.isRest
    target.exercises = source.exercises.map((e) => ({ ...e, id: createId() }))
  }

  const addWeeklyPlan = (): string => {
    const next = createEmptyWeeklyEntry(`Weekly Workout Plan ${weeklyPlans.value.length + 1}`)
    weeklyPlans.value = [...weeklyPlans.value, next]
    return next.id
  }

  const removeWeeklyPlan = (planId: string) => {
    if (weeklyPlans.value.length <= 1) return
    weeklyPlans.value = weeklyPlans.value
      .filter((p) => p.id !== planId)
      .map((p, i) => ({ ...p, label: `Weekly Workout Plan ${i + 1}` }))
  }

  const applyTemplate = (weekId: string, template: WeeklyPlan) => {
    const idx = weeklyPlans.value.findIndex((p) => p.id === weekId)
    if (idx === -1) return
    const previous = weeklyPlans.value[idx]
    if (!previous) return
    const days: PlanDay[] = template.days.map((d, i) => ({
      id: createId(),
      label: d.label,
      isRest: d.isRest,
      orderIndex: i,
      exercises: d.exercises.map((e, ei) => ({
        id: createId(),
        exerciseId: e.exerciseId ?? null,
        exerciseName: e.exerciseName,
        sets: e.sets,
        reps: e.reps,
        weight: e.weight ?? null,
        weightUnit: e.weightUnit,
        restSeconds: e.restSeconds,
        orderIndex: ei,
      })),
    }))
    const next: WeeklyEntry = {
      id: previous.id,
      label: template.label,
      weekFrequency: previous.weekFrequency,
      days,
      origin: 'from-template',
      sourceTemplateId: template.id,
    }
    next.baseline = weekSnapshot(next)
    const copy = [...weeklyPlans.value]
    copy[idx] = next
    weeklyPlans.value = copy
  }

  const isWeekModified = (weekId: string): boolean => {
    const w = weeklyPlans.value.find((p) => p.id === weekId)
    if (!w || w.origin === 'fresh' || !w.baseline) return false
    return weekSnapshot(w) !== w.baseline
  }

  const getWeekStatus = (weekId: string): WeeklyOrigin => {
    const w = weeklyPlans.value.find((p) => p.id === weekId)
    if (!w) return 'fresh'
    if (w.origin === 'fresh') return 'fresh'
    return isWeekModified(weekId) ? 'from-template-modified' : 'from-template'
  }

  const isStepValid = (step: number) => {
    if (step === 1) {
      if (name.value.trim() === '') return false
      if ((duration.value ?? 0) <= 0) return false
      if (showWeeklyDaysQuestion.value) {
        const n = workoutDaysPerWeek.value
        if (n === null || n < 1 || n > 7) return false
      }
      return true
    }
    if (step === 2) {
      if (isWeeklyMode.value) {
        if (weeklyPlans.value.length === 0) return false
        if (weeklyPlans.value.some((p) => p.weekFrequency < 1)) return false
        const allDays = weeklyPlans.value.flatMap((p) => p.days)
        return allDays.every(
          (d) =>
            d.isRest ||
            (d.exercises.length > 0 && d.exercises.every((e) => e.exerciseName.trim() !== '')),
        )
      }
      if (flatDays.value.length === 0) return false
      return flatDays.value.every(
        (d) =>
          d.isRest ||
          (d.exercises.length > 0 && d.exercises.every((e) => e.exerciseName.trim() !== '')),
      )
    }
    return true
  }

  const reset = () => {
    name.value = ''

    void setImageFile(null)
    imagePreviewUrl.value = ''
    duration.value = null
    durationType.value = 'weeks'
    workoutDaysPerWeek.value = null
    weeklyPlans.value = []
    flatDays.value = []
    imageError.value = null
    originalPlanInfo.value = null
  }

  const buildPlanPayload = (): PlanCreate => {
    const payload: PlanCreate = {
      title: name.value.trim(),
      duration: duration.value ?? 0,
      durationType: durationType.value,
      imageUrl: imagePreviewUrl.value || null,
      workoutDaysPerWeek: workoutDaysPerWeek.value ?? undefined,
    }
    if (isWeeklyMode.value) {
      payload.weeklyPlans = weeklyPlans.value.map(
        (entry, i): WeeklyWorkoutPlanCreate => ({
          label: entry.label,
          weekFrequency: entry.weekFrequency,
          orderIndex: i,
          days: entry.days.map((d, di) => dayToCreate(d, di)),
        }),
      )
    } else {
      payload.flatDays = flatDays.value.map((d, di) => dayToCreate(d, di))
    }
    return payload
  }

  const changesMade = computed(() => {
    if (originalPlanInfo.value === null) return true
    return JSON.stringify(buildPlanPayload()) !== originalPlanInfo.value
  })

  const loadPlan = (plan: Plan) => {
    reset()
    name.value = plan.title
    duration.value = plan.duration
    durationType.value = plan.durationType
    workoutDaysPerWeek.value = plan.workoutDaysPerWeek ?? null
    if (plan.imageUrl) {
      imagePreviewUrl.value = plan.imageUrl
    }
    if (plan.weeklyPlans?.length) {
      weeklyPlans.value = plan.weeklyPlans.map((wp, i) => {
        const days: PlanDay[] = (wp.days ?? []).map((d, di) => ({
          id: createId(),
          label: d.label,
          isRest: d.isRest,
          orderIndex: di,
          exercises: d.exercises.map((e, ei) => ({
            id: createId(),
            exerciseId: e.exerciseId ?? null,
            exerciseName: e.exerciseName,
            sets: e.sets,
            reps: e.reps,
            weight: e.weight ?? null,
            weightUnit: e.weightUnit,
            restSeconds: e.restSeconds,
            orderIndex: ei,
          })),
        }))
        const entry: WeeklyEntry = {
          id: createId(),
          label: wp.label || `Weekly Workout Plan ${i + 1}`,
          weekFrequency: wp.weekFrequency,
          days,
          origin: 'from-template',
          sourceTemplateId: wp.id,
        }
        entry.baseline = weekSnapshot(entry)
        return entry
      })
    }
    if (plan.flatDays?.length) {
      flatDays.value = plan.flatDays.map((d, di) => ({
        id: createId(),
        label: d.label,
        isRest: d.isRest,
        orderIndex: di,
        exercises: d.exercises.map((e, ei) => ({
          id: createId(),
          exerciseId: e.exerciseId ?? null,
          exerciseName: e.exerciseName,
          sets: e.sets,
          reps: e.reps,
          weight: e.weight ?? null,
          weightUnit: e.weightUnit,
          restSeconds: e.restSeconds,
          orderIndex: ei,
        })),
      }))
    }
    originalPlanInfo.value = JSON.stringify(buildPlanPayload())
  }

  const state: PlanFormState = {
    name,
    imageFile,
    imagePreviewUrl,
    imageError,
    duration,
    durationType,
    workoutDaysPerWeek,
    showWeeklyDaysQuestion,
    isWeeklyMode,
    totalDays,
    totalWeeks,
    weeklyPlans,
    flatDays,
    rotationCycleLength,
    setImageFile,
    initStep2,
    toggleRest,
    addExercise,
    removeExercise,
    copyDay,
    addWeeklyPlan,
    removeWeeklyPlan,
    applyTemplate,
    isWeekModified,
    getWeekStatus,
    isStepValid,
    changesMade,
    reset,
    loadPlan,
    buildPlanPayload,
  }

  provide(PlanFormKey, state)
  return state
}

export const usePlanForm = (): PlanFormState => {
  const state = inject(PlanFormKey)
  if (!state) {
    throw new Error('usePlanForm must be called inside a component that called providePlanForm')
  }
  return state
}
