<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { Exercise, BodyCategory } from '@/types/exercise'
import { BODY_CATEGORY_LABELS } from '@/types/exercise'
import { Input } from '@/components/ui/input/index'
import AddExerciseDialog from '@/components/AddExerciseDialog.vue'
import ExerciseDialog from '@/components/ExerciseDialog.vue'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'

const props = defineProps<{
  exercises: Exercise[]
}>()

const searchQuery = ref('')
const SUMMARY_LIMIT = 3

const categoryFilter = ref<BodyCategory | ''>('')

const visibleExercises = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (q || categoryFilter.value) {
    return props.exercises.filter(
      (ex) =>
        (ex.name.toLowerCase().includes(q) && categoryFilter.value === '') ||
        (ex.bodyCategory === categoryFilter.value && q === '') ||
        (ex.name.toLowerCase().includes(q) && ex.bodyCategory === categoryFilter.value),
    )
  }
  return [...props.exercises].sort((a, b) => b.usageCount - a.usageCount).slice(0, SUMMARY_LIMIT)
})
const clearFilter = () => {
  categoryFilter.value = ''
  searchQuery.value = ''
}
</script>

<template>
  <section class="flex flex-col gap-4 border border-[#3a3a37] rounded-md p-4">
    <header class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-white">Exercises</h2>
      <div class="flex items-center gap-1">
        <AddExerciseDialog />
      </div>
    </header>

    <div class="flex flex-wrap items-center gap-2 sm:gap-3">
      <div class="relative w-full sm:w-auto sm:flex-1 min-w-[10rem]">
        <Input
          v-model="searchQuery"
          class="bg-[#2a2a28] border-[#3a3a37] border rounded-md px-4 py-2 pr-10 text-white text-sm focus:outline-none focus:border-[#6a6a63]"
          placeholder="Search exercises name..."
          aria-label="Search exercises"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="absolute hover:cursor-pointer inset-y-1 right-2 grid h-6 w-6 place-items-center rounded-full text-[#a0a09a] transition-colors hover:bg-[#3a3a37] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
          aria-label="Clear search"
          @click="searchQuery = ''"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>
      <NativeSelect
        v-model="categoryFilter"
        aria-label="Filter by category"
        class="dark w-full sm:w-auto sm:min-w-40 py-2"
      >
        <NativeSelectOption value="">Any Category</NativeSelectOption>
        <NativeSelectOption
          v-for="(label, value) in BODY_CATEGORY_LABELS"
          :key="value"
          :value="value"
        >
          {{ label }}
        </NativeSelectOption>
      </NativeSelect>

      <button
        class="text-sm text-[#ff6f14] cursor-pointer hover:text-[#ffffff]"
        @click="clearFilter"
      >
        Clear
      </button>
    </div>

    <ul
      v-if="visibleExercises.length"
      class="flex flex-col gap-2 max-h-[11rem] overflow-y-auto pr-1 scrollbar-thin"
    >
      <li v-for="exercise in visibleExercises" :key="exercise.id">
        <ExerciseDialog :exercise="exercise" />
      </li>
    </ul>
    <p v-else class="text-sm text-[#a0a09a] text-center">No exercises match your search</p>
  </section>
</template>
