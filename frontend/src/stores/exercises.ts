import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Exercise } from '@/types/exercise'

export const useExercisesStore = defineStore('exercises', () => {
  const exercises = ref<Exercise[]>([])

  const getById = (id: string) => exercises.value.find((e) => e.id === id)

  const initExercises = (input: Exercise[]) => {
    exercises.value = input
  }

  const ingestExercise = (exercise: Exercise) => {
    const idx = exercises.value.findIndex((e) => e.id === exercise.id)
    if (idx >= 0) {
      const next = [...exercises.value]
      next[idx] = exercise
      exercises.value = next
    } else {
      exercises.value = [...exercises.value, exercise]
    }
  }

  const removeExercise = (id: string) => {
    exercises.value = exercises.value.filter((e) => e.id !== id)
  }

  return {
    exercises,
    initExercises,
    getById,
    ingestExercise,
    removeExercise,
  }
})
