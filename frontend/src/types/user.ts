import type { DurationType, Plan, WeightUnit } from './plan'

export type PlanStatus = 'in-progress' | 'completed' | 'cancelled' | 'paused'

export interface UserPlanAssignment {
  id: string
  userId: string
  startDate: Date
  endDate: Date
  status: PlanStatus
  remainingDays: number
  user: User
  plan: Plan
}

export interface UserPlanAssignmentRead {
  id: string
  userId: string
  planId: string
  planTitle: string
  startDate: Date
  endDate: Date
  status: PlanStatus
  remainingDays: number
  assignedAt?: string
  assignedByName?: string | null
  assignedByEmail?: string | null
}

export interface UserLatestPlanExercise {
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

export interface UserLatestPlanDay {
  id: string
  label: string
  isRest: boolean
  orderIndex: number
  exercises: UserLatestPlanExercise[]
}

export interface UserLatestWeeklyPlan {
  id: string
  label: string
  days: UserLatestPlanDay[]
}

export interface UserLatestWeeklyEntry extends UserLatestWeeklyPlan {
  weekFrequency: number
  orderIndex: number
  planId?: string
}

export interface UserScheduleEntry {
  date: string
  dayId: string
  label: string
  isRest: boolean
  exercises: UserLatestPlanExercise[]
}

export interface UserLatestPlan {
  id: string
  planId: string
  planTitle: string
  duration: number
  durationType: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  startDate: string
  endDate: string
  status: PlanStatus
  remainingDays?: number | null
  assignedByName?: string | null
  assignedByEmail?: string | null
  weeklyPlans?: UserLatestWeeklyEntry[] | null
  flatDays?: UserLatestPlanDay[] | null
  schedule: UserScheduleEntry[]
}

export type Gender = 'male' | 'female' | 'other'

export interface User {
  id: string
  firstName: string
  lastName: string
  email: string
  avatarUrl?: string | null
  timezone?: string
  gender?: Gender | null
  phoneNumber?: string | null
  latestPlan?: UserLatestPlan | null
  removed?: boolean
}
