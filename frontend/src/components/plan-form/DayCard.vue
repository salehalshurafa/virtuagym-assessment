<!-- eslint-disable vue/no-mutating-props -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Check, Pencil, Plus, Sparkles, Trash2 } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { useExercisesStore } from '@/stores/exercises'
import type { ExerciseAssignment, PlanDay } from '@/types/plan'
import { createId } from './ids'

const props = defineProps<{
  day: PlanDay
  otherDays: PlanDay[]
  weeklyPlanId?: string
}>()

const exercisesStore = useExercisesStore()
const { exercises: libraryExercises } = storeToRefs(exercisesStore)

const datalistId = `exercise-library-${Math.random().toString(36).slice(2, 10)}`

const sortedLibrary = computed(() =>
  [...libraryExercises.value].sort((a, b) => a.name.localeCompare(b.name)),
)

const libraryByLowerName = computed(() => {
  const map = new Map<string, (typeof libraryExercises.value)[number]>()
  for (const ex of libraryExercises.value) {
    map.set(ex.name.toLowerCase(), ex)
  }
  return map
})

const onExerciseNameChange = (exercise: ExerciseAssignment, value: string) => {
  exercise.exerciseName = value
  const match = libraryByLowerName.value.get(value.trim().toLowerCase())
  exercise.exerciseId = match ? match.id : undefined
}

const isFromLibrary = (exercise: ExerciseAssignment) => exercise.exerciseId !== null

const copySource = ref('')
const editingExerciseId = ref<string | null>(null)

const isEditing = (id: string) => editingExerciseId.value === id

const startEditing = (id: string) => {
  editingExerciseId.value = id
}

const stopEditing = () => {
  editingExerciseId.value = null
}

const toggleRest = () => {
  props.day.isRest = !props.day.isRest
  if (props.day.isRest) props.day.exercises = []
}

const addExercise = () => {
  const next: ExerciseAssignment = {
    id: createId(),
    exerciseId: undefined,
    exerciseName: '',
    sets: 3,
    reps: 10,
    weight: undefined,
    weightUnit: 'kg',
    restSeconds: 60,
    orderIndex: props.day.exercises.length,
  }
  props.day.exercises.push(next)
  editingExerciseId.value = next.id
}

const removeExercise = (id: string) => {
  props.day.exercises = props.day.exercises.filter((e) => e.id !== id)
  if (editingExerciseId.value === id) editingExerciseId.value = null
}

const onCopyDay = () => {
  if (!copySource.value) return
  const source = props.otherDays.find((d) => d.id === copySource.value)
  if (!source) {
    copySource.value = ''
    return
  }
  props.day.isRest = source.isRest
  props.day.exercises = source.exercises.map((e) => ({ ...e, id: createId() }))
  copySource.value = ''
}

onMounted(() => {
  const unfinished = props.day.exercises.find((ex) => !ex.exerciseName.trim())
  if (unfinished) editingExerciseId.value = unfinished.id
})
</script>

<template>
  <div class="flex flex-col gap-3 rounded-md border border-[#3a3a37] bg-[#2a2a28]/40 p-3">
    <datalist :id="datalistId">
      <option v-for="ex in sortedLibrary" :key="ex.id" :value="ex.name" />
    </datalist>

    <div class="flex flex-wrap items-center gap-2">
      <Input
        v-model="day.label"
        :aria-label="`Label for ${day.label || 'workout day'}`"
        placeholder="Day name"
        class="h-8 min-w-44 flex-1 bg-[#1f1f1d] border-[#3a3a37] text-sm font-medium text-white"
      />
      <div class="flex items-center gap-2">
        <NativeSelect
          v-if="otherDays.length > 0"
          v-model="copySource"
          class="h-8 min-w-44 bg-[#1f1f1d] border-[#3a3a37] text-xs text-[#d4d4cf]"
          aria-label="Copy configuration from another day"
          @change="onCopyDay"
        >
          <NativeSelectOption value="">Copy from…</NativeSelectOption>
          <NativeSelectOption v-for="d in otherDays" :key="d.id" :value="d.id">
            {{ d.label || '(unnamed)' }}
          </NativeSelectOption>
        </NativeSelect>
        <label class="flex cursor-pointer items-center gap-1.5 text-xs text-[#a0a09a]">
          <input
            type="checkbox"
            :checked="day.isRest"
            class="h-3.5 w-3.5 accent-[#ff6f14]"
            @change="toggleRest"
          />
          Rest day
        </label>
      </div>
    </div>

    <div v-if="!day.isRest" class="flex flex-col gap-1.5">
      <template v-for="exercise in day.exercises" :key="exercise.id">
        <div
          v-if="isEditing(exercise.id)"
          class="flex flex-col gap-2 rounded-md border border-[#ff6f14]/40 bg-[#1f1f1d] p-3"
        >
          <div class="flex flex-col gap-1">
            <label
              class="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-[#a0a09a]"
            >
              Exercise
              <span
                v-if="isFromLibrary(exercise)"
                class="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-300"
              >
                <Sparkles class="h-2.5 w-2.5" />
                Library
              </span>
              <span
                v-else-if="exercise.exerciseName.trim()"
                class="inline-flex items-center gap-1 rounded-full border border-[#3a3a37] bg-[#2a2a28] px-1.5 py-0.5 text-[9px] font-medium text-[#a0a09a]"
              >
                Custom
              </span>
            </label>
            <Input
              :model-value="exercise.exerciseName"
              :list="datalistId"
              placeholder="Type to search the library, or write a custom name"
              aria-label="Exercise name"
              autocomplete="off"
              class="h-9 bg-[#2a2a28] border-[#3a3a37] text-sm text-white"
              @update:model-value="onExerciseNameChange(exercise, String($event))"
            />
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <div class="flex items-center gap-1">
              <Input
                v-model.number="exercise.sets"
                type="number"
                min="1"
                aria-label="Sets"
                class="h-8 w-14 bg-[#2a2a28] border-[#3a3a37] text-center text-sm text-white"
              />
              <span class="text-xs text-[#a0a09a]">sets ×</span>
              <Input
                v-model.number="exercise.reps"
                type="number"
                min="1"
                aria-label="Reps"
                class="h-8 w-14 bg-[#2a2a28] border-[#3a3a37] text-center text-sm text-white"
              />
              <span class="text-xs text-[#a0a09a]">reps</span>
            </div>
            <div class="flex items-center gap-1">
              <Input
                :model-value="exercise.weight ?? undefined"
                type="number"
                min="0"
                placeholder="wt"
                aria-label="Weight"
                class="h-8 w-16 bg-[#2a2a28] border-[#3a3a37] text-center text-sm text-white"
                @update:model-value="
                  (v) => (exercise.weight = v === '' || v == null ? null : Number(v))
                "
              />
              <NativeSelect
                v-model="exercise.weightUnit"
                aria-label="Weight unit"
                class="h-8 w-20 bg-[#2a2a28] border-[#3a3a37] px-2 text-xs text-white"
              >
                <NativeSelectOption value="kg">kg</NativeSelectOption>
                <NativeSelectOption value="lbs">lbs</NativeSelectOption>
              </NativeSelect>
            </div>
            <div class="flex items-center gap-1">
              <Input
                v-model.number="exercise.restSeconds"
                type="number"
                min="0"
                aria-label="Rest seconds"
                class="h-8 w-16 bg-[#2a2a28] border-[#3a3a37] text-center text-sm text-white"
              />
              <span class="text-xs text-[#a0a09a]">sec rest</span>
            </div>

            <div class="ml-auto flex items-center gap-2">
              <button
                type="button"
                class="grid h-7 w-7 place-items-center rounded-md text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#3a3a37] hover:text-white"
                :aria-label="`Remove ${exercise.exerciseName || 'exercise'}`"
                @click="removeExercise(exercise.id)"
              >
                <Trash2 class="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                class="flex h-7 items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-2.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
                aria-label="Done editing"
                @click="stopEditing"
              >
                <Check class="h-3.5 w-3.5" />
                Done
              </button>
            </div>
          </div>
        </div>

        <div
          v-else
          class="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md bg-[#1f1f1d] px-3 py-2 transition-colors hover:bg-[#252525]"
        >
          <span
            v-if="isFromLibrary(exercise)"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-300"
            title="From library"
          >
            <Sparkles class="h-2.5 w-2.5" />
          </span>
          <span class="flex-1 truncate text-sm font-medium text-white">
            {{ exercise.exerciseName.trim() || '(Unnamed exercise)' }}
          </span>
          <span
            class="shrink-0 rounded-full bg-[#2a2a28] px-2 py-0.5 text-xs font-medium text-[#d4d4cf] tabular-nums"
          >
            {{ exercise.sets }} × {{ exercise.reps }}
          </span>
          <span
            v-if="exercise.weight !== null && exercise.weight !== undefined && exercise.weight > 0"
            class="shrink-0 rounded-full bg-[#2a2a28] px-2 py-0.5 text-xs font-medium text-[#d4d4cf] tabular-nums"
          >
            {{ exercise.weight }} {{ exercise.weightUnit }}
          </span>
          <span class="shrink-0 text-xs text-[#a0a09a] tabular-nums">
            {{ exercise.restSeconds }}s rest
          </span>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center rounded-md text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#3a3a37] hover:text-white"
            :aria-label="`Edit ${exercise.exerciseName || 'exercise'}`"
            @click="startEditing(exercise.id)"
          >
            <Pencil class="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center rounded-md text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#3a3a37] hover:text-white"
            :aria-label="`Remove ${exercise.exerciseName || 'exercise'}`"
            @click="removeExercise(exercise.id)"
          >
            <Trash2 class="h-3.5 w-3.5" />
          </button>
        </div>
      </template>

      <button
        type="button"
        class="flex w-full items-center justify-center gap-1 rounded-md border border-dashed border-[#ff6f14] px-2.5 py-1.5 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#ff6f14]/10 focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
        @click="addExercise"
      >
        <Plus class="h-3.5 w-3.5" />
        Add exercise
      </button>
    </div>
  </div>
</template>
