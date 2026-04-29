export type DurationType = 'days' | 'weeks' | 'months' | 'years'
export type WeightUnit = 'kg' | 'lbs'

export interface ExerciseAssignment {
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

export interface PlanDay {
  id: string
  label: string
  isRest: boolean
  orderIndex: number
  exercises: ExerciseAssignment[]
}

export interface WeeklyWorkoutPlan {
  id: string
  planId?: string
  label: string
  weekFrequency: number
  orderIndex: number
  days: PlanDay[]
}

export interface Plan {
  id: string
  title: string
  duration: number
  durationType: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  archived: boolean
  userCount: number
  weeklyPlans?: WeeklyWorkoutPlan[] | null
  flatDays?: PlanDay[] | null
}

export interface ExerciseAssignmentCreate {
  exerciseId?: string | null
  exerciseName: string
  sets?: number
  reps?: number
  weight?: number | null
  weightUnit?: WeightUnit
  restSeconds?: number
  orderIndex?: number
}

export interface PlanDayCreate {
  label: string
  isRest?: boolean
  orderIndex?: number
  exercises?: ExerciseAssignmentCreate[]
}

export interface WeeklyWorkoutPlanCreate {
  label: string
  weekFrequency?: number
  orderIndex?: number
  days?: PlanDayCreate[]
}

export interface WeeklyWorkoutPlanUpdate {
  label?: string
  weekFrequency?: number
  orderIndex?: number
  days?: PlanDayCreate[]
}

export interface PlanCreate {
  title: string
  duration: number
  durationType: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  weeklyPlans?: WeeklyWorkoutPlanCreate[] | null
  flatDays?: PlanDayCreate[] | null
}

export interface PlanUpdate {
  title?: string
  duration?: number
  durationType?: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  weeklyPlans?: WeeklyWorkoutPlanCreate[] | null
  flatDays?: PlanDayCreate[] | null
}
