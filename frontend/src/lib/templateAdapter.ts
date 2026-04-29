/**
 * Converters between the gallery's ``PlanTemplate`` shape (JSON-storage
 * native) and the live ``Plan`` shape (normalised). Used by ``PlanDialog``
 * and ``usePlanForm.loadPlan`` so the same form code can edit a template.
 *
 * After the join-table collapse, a live ``Plan`` carries
 * ``weeklyPlans: WeeklyWorkoutPlan[]`` directly — each weekly owns its
 * ``weekFrequency`` and ``orderIndex``. The template's JSON shape
 * (``PlanTemplateWeeklyEntry``) is already flat, so the conversion is
 * essentially a one-to-one field copy.
 */
import type {
  ExerciseAssignment,
  Plan,
  PlanCreate,
  PlanDay,
  WeeklyWorkoutPlan,
  WeightUnit,
} from '@/types/plan'
import type { PlanTemplate, PlanTemplateUpdate } from '@/types/template'
import { createId } from '@/components/plan-form/ids'

const synthExercises = (
  raw: Array<Partial<ExerciseAssignment>> | undefined,
): ExerciseAssignment[] =>
  (raw ?? []).map((e, ei) => ({
    id: createId(),
    exerciseId: e.exerciseId ?? null,
    exerciseName: e.exerciseName ?? '',
    sets: e.sets ?? 3,
    reps: e.reps ?? 10,
    weight: e.weight ?? null,
    weightUnit: ((e.weightUnit as WeightUnit | undefined) ?? 'kg'),
    restSeconds: e.restSeconds ?? 60,
    orderIndex: e.orderIndex ?? ei,
  }))

const synthDays = (raw: Array<Partial<PlanDay>> | undefined): PlanDay[] =>
  (raw ?? []).map((d, di) => ({
    id: createId(),
    label: d.label ?? `Day ${di + 1}`,
    isRest: d.isRest ?? false,
    orderIndex: d.orderIndex ?? di,
    exercises: synthExercises(d.exercises as Array<Partial<ExerciseAssignment>> | undefined),
  }))

/** PlanTemplate → Plan-shaped object for usePlanForm + PlanDialog rendering. */
export const templateToPlan = (template: PlanTemplate): Plan => {
  const weeklyPlans: WeeklyWorkoutPlan[] = (template.weeklyPlans ?? []).map(
    (entry, i) => ({
      id: createId(),
      planId: template.id,
      label: entry.label ?? `Weekly Workout Plan ${i + 1}`,
      weekFrequency: entry.weekFrequency ?? 1,
      orderIndex: entry.orderIndex ?? i,
      days: synthDays(entry.days as Array<Partial<PlanDay>> | undefined),
    }),
  )

  return {
    id: template.id,
    title: template.title,
    duration: template.duration,
    durationType: template.durationType,
    imageUrl: template.imageUrl ?? null,
    workoutDaysPerWeek: template.workoutDaysPerWeek ?? null,
    archived: template.archived,
    userCount: 0,
    weeklyPlans: weeklyPlans.length ? weeklyPlans : null,
    flatDays: template.flatDays ? synthDays(template.flatDays as Array<Partial<PlanDay>>) : null,
  }
}

/** PlanCreate (built by usePlanForm.buildPlanPayload) → PlanTemplateUpdate
 * body. After the join-table collapse the live ``weeklyPlans`` and the
 * template's ``weeklyPlans`` JSON are nearly identical — each entry
 * carries ``label``, ``days``, ``weekFrequency``, ``orderIndex``. The
 * template adds an optional ``weeklySplitTemplateId`` reference, which
 * the form-create path doesn't populate.
 */
export const planPayloadToTemplateUpdate = (payload: PlanCreate): PlanTemplateUpdate => {
  const update: PlanTemplateUpdate = {
    title: payload.title,
    duration: payload.duration,
    durationType: payload.durationType,
    imageUrl: payload.imageUrl,
    workoutDaysPerWeek: payload.workoutDaysPerWeek,
  }

  if (payload.weeklyPlans !== undefined) {
    update.weeklyPlans = (payload.weeklyPlans ?? []).map((e, i) => ({
      weeklySplitTemplateId: null,
      label: e.label,
      days: (e.days ?? null) as never,
      weekFrequency: e.weekFrequency ?? 1,
      orderIndex: e.orderIndex ?? i,
    }))
  }
  if (payload.flatDays !== undefined) {
    update.flatDays = payload.flatDays
  }
  return update
}
