/**
 * Structural fingerprinting for "is this live entity already a template?".
 *
 * The post-hoc "Save as template" buttons (B.3) hide themselves when the
 * structure they would promote already exists in the templates store —
 * otherwise the gallery clutters with duplicates. We compare canonical
 * fingerprints rather than ids, so a user-edited copy that happens to land
 * back on the original structure is recognised as already-a-template.
 *
 * The fingerprint omits metadata that's allowed to differ without changing
 * the *content*: title / label, image, archived flag, dates, ids. Only the
 * structural fields count.
 */
import type { Plan } from '@/types/plan'
import type { PlanTemplate, WeeklySplitTemplate } from '@/types/template'
import type { WeeklyPlan } from '@/types/weeklyPlan'

interface FingerprintExercise {
  exerciseName: string
  sets: number
  reps: number
  weight: number | null
  weightUnit: string
  restSeconds: number
  orderIndex: number
}

interface FingerprintDay {
  isRest: boolean
  orderIndex: number
  label: string
  exercises: FingerprintExercise[]
}

interface FingerprintWeekly {
  weekFrequency: number
  orderIndex: number
  days: FingerprintDay[]
}

interface FingerprintPlan {
  duration: number
  durationType: string
  workoutDaysPerWeek: number | null
  weeklyPlans: FingerprintWeekly[] | null
  flatDays: FingerprintDay[] | null
}

const exerciseFP = (e: {
  exerciseName: string
  sets: number
  reps: number
  weight?: number | null
  weightUnit: string
  restSeconds: number
  orderIndex: number
}): FingerprintExercise => ({
  exerciseName: e.exerciseName,
  sets: e.sets,
  reps: e.reps,
  weight: e.weight ?? null,
  weightUnit: e.weightUnit,
  restSeconds: e.restSeconds,
  orderIndex: e.orderIndex,
})

const dayFP = (d: {
  label: string
  isRest: boolean
  orderIndex: number
  exercises: Array<{
    exerciseName: string
    sets: number
    reps: number
    weight?: number | null
    weightUnit: string
    restSeconds: number
    orderIndex: number
  }>
}): FingerprintDay => ({
  isRest: d.isRest,
  orderIndex: d.orderIndex,
  label: d.label,
  exercises: d.exercises.map(exerciseFP).sort((a, b) => a.orderIndex - b.orderIndex),
})

export const planFingerprint = (plan: Plan): string => {
  const fp: FingerprintPlan = {
    duration: plan.duration,
    durationType: plan.durationType,
    workoutDaysPerWeek: plan.workoutDaysPerWeek ?? null,
    weeklyPlans:
      plan.weeklyPlans?.map((wp): FingerprintWeekly => ({
        weekFrequency: wp.weekFrequency,
        orderIndex: wp.orderIndex,
        days: wp.days
          .map(dayFP)
          .sort((a, b) => a.orderIndex - b.orderIndex),
      })) ?? null,
    flatDays: plan.flatDays?.map(dayFP).sort((a, b) => a.orderIndex - b.orderIndex) ?? null,
  }
  return JSON.stringify(fp)
}

export const planTemplateFingerprint = (template: PlanTemplate): string => {
  const fp: FingerprintPlan = {
    duration: template.duration,
    durationType: template.durationType,
    workoutDaysPerWeek: template.workoutDaysPerWeek ?? null,
    weeklyPlans:
      template.weeklyPlans?.map((entry): FingerprintWeekly => ({
        weekFrequency: entry.weekFrequency,
        orderIndex: entry.orderIndex,
        days: (entry.days ?? [])
          .map((d) =>
            dayFP({
              label: d.label,
              isRest: d.isRest ?? false,
              orderIndex: d.orderIndex ?? 0,
              exercises: (d.exercises ?? []).map((e) => ({
                exerciseName: e.exerciseName,
                sets: e.sets ?? 3,
                reps: e.reps ?? 10,
                weight: e.weight ?? null,
                weightUnit: e.weightUnit ?? 'kg',
                restSeconds: e.restSeconds ?? 60,
                orderIndex: e.orderIndex ?? 0,
              })),
            }),
          )
          .sort((a, b) => a.orderIndex - b.orderIndex),
      })) ?? null,
    flatDays:
      template.flatDays
        ?.map((d) =>
          dayFP({
            label: d.label,
            isRest: d.isRest ?? false,
            orderIndex: d.orderIndex ?? 0,
            exercises: (d.exercises ?? []).map((e) => ({
              exerciseName: e.exerciseName,
              sets: e.sets ?? 3,
              reps: e.reps ?? 10,
              weight: e.weight ?? null,
              weightUnit: e.weightUnit ?? 'kg',
              restSeconds: e.restSeconds ?? 60,
              orderIndex: e.orderIndex ?? 0,
            })),
          }),
        )
        .sort((a, b) => a.orderIndex - b.orderIndex) ?? null,
  }
  return JSON.stringify(fp)
}

export const planMatchesAnyTemplate = (
  plan: Plan,
  templates: PlanTemplate[],
): boolean => {
  const fp = planFingerprint(plan)
  return templates.some((t) => planTemplateFingerprint(t) === fp)
}

const weeklyFingerprintFromDays = (days: FingerprintDay[]): string =>
  JSON.stringify(days.sort((a, b) => a.orderIndex - b.orderIndex))

export const weeklyFingerprint = (week: WeeklyPlan): string =>
  weeklyFingerprintFromDays(week.days.map(dayFP))

export const weeklySplitTemplateFingerprint = (
  template: WeeklySplitTemplate,
): string =>
  weeklyFingerprintFromDays(
    template.days.map((d) =>
      dayFP({
        label: d.label,
        isRest: d.isRest ?? false,
        orderIndex: d.orderIndex ?? 0,
        exercises: (d.exercises ?? []).map((e) => ({
          exerciseName: e.exerciseName,
          sets: e.sets ?? 3,
          reps: e.reps ?? 10,
          weight: e.weight ?? null,
          weightUnit: e.weightUnit ?? 'kg',
          restSeconds: e.restSeconds ?? 60,
          orderIndex: e.orderIndex ?? 0,
        })),
      }),
    ),
  )

export const weeklyMatchesAnyTemplate = (
  week: WeeklyPlan,
  templates: WeeklySplitTemplate[],
): boolean => {
  const fp = weeklyFingerprint(week)
  return templates.some((t) => weeklySplitTemplateFingerprint(t) === fp)
}
