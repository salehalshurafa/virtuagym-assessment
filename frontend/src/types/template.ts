import type { DurationType, ExerciseAssignmentCreate, PlanDayCreate } from './plan'

export interface PlanTemplateWeeklyEntry {
  weeklySplitTemplateId?: string | null
  label?: string | null
  days?: PlanDayCreate[] | null
  weekFrequency: number
  orderIndex: number
}

export interface PlanTemplate {
  id: string
  title: string
  duration: number
  durationType: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  archived: boolean
  weeklyPlans?: PlanTemplateWeeklyEntry[] | null
  flatDays?: PlanDayCreate[] | null
}

export interface PlanTemplateCreate {
  title: string
  duration: number
  durationType: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  weeklyPlans?: PlanTemplateWeeklyEntry[] | null
  flatDays?: PlanDayCreate[] | null
}

export interface PlanTemplateUpdate {
  title?: string
  duration?: number
  durationType?: DurationType
  imageUrl?: string | null
  workoutDaysPerWeek?: number | null
  weeklyPlans?: PlanTemplateWeeklyEntry[] | null
  flatDays?: PlanDayCreate[] | null
}

export interface WeeklySplitTemplate {
  id: string
  label: string
  days: PlanDayCreate[]
}

export interface WeeklySplitTemplateCreate {
  label: string
  days: PlanDayCreate[]
}

export interface WeeklySplitTemplateUpdate {
  label?: string
  days?: PlanDayCreate[]
}

export type { ExerciseAssignmentCreate, PlanDayCreate }
