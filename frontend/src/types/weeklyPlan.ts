import type { WeightUnit } from './plan'

export interface WeeklyPlanExercise {
  id: string
  exerciseId?: string | null
  exerciseName: string
  sets: number
  reps: number
  weight?: number | null
  weightUnit: WeightUnit
  restSeconds: number
  orderIndex: number
}

export interface WeeklyPlanDay {
  id: string
  label: string
  isRest: boolean
  orderIndex: number
  exercises: WeeklyPlanExercise[]
}

export interface WeeklyPlan {
  id: string
  label: string
  days: WeeklyPlanDay[]
}
