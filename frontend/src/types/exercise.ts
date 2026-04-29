export type BodyCategory = 'chest' | 'back' | 'legs' | 'core' | 'arms' | 'shoulders' | 'cardio'

export type Equipment = 'bar' | 'dumbbell' | 'machine' | 'cable' | 'free-weight'

export interface Exercise {
  id: string
  name: string
  bodyCategory: BodyCategory
  equipment: Equipment
  imageUrl?: string | null
  videoUrl?: string | null
  instructions?: string | null
  usageCount: number
}

export const BODY_CATEGORY_LABELS: Record<BodyCategory, string> = {
  chest: 'Chest',
  back: 'Back',
  legs: 'Legs',
  core: 'Core',
  arms: 'Arms',
  shoulders: 'Shoulders',
  cardio: 'Cardio',
}

export const EQUIPMENT_LABELS: Record<Equipment, string> = {
  bar: 'Bar',
  dumbbell: 'Dumbbell',
  machine: 'Machine',
  cable: 'Cable',
  'free-weight': 'Free Weight',
}
