<script setup lang="ts">
import { storeToRefs } from 'pinia'
import PlansList from '@/components/PlansList.vue'
import WeeksList from '@/components/WeeksList.vue'
import ExercisesList from '@/components/ExercisesList.vue'
import UsersList from '@/components/UsersList.vue'
import ActivePlansList from '@/components/ActivePlansList.vue'
import { useUsersStore } from '@/stores/users'
import { usePlanTemplatesStore } from '@/stores/planTemplates'
import { useExercisesStore } from '@/stores/exercises'
import { useWeeklySplitTemplatesStore } from '@/stores/weeklySplitTemplates'

const { manageableUsers, me } = storeToRefs(useUsersStore())
const { templates: planTemplates } = storeToRefs(usePlanTemplatesStore())
const { exercises } = storeToRefs(useExercisesStore())
const { templates: weeklySplitTemplates } = storeToRefs(useWeeklySplitTemplatesStore())
</script>

<template>
  <div class="flex flex-col gap-6 sm:gap-10">
    <header>
      <h1 class="text-2xl sm:text-3xl font-bold text-white">Workout Plan Manager</h1>
      <h4 v-if="me" class="text-sm sm:text-base">Welcome back, {{ me.firstName }}</h4>
    </header>
    <main class="flex flex-col gap-6 sm:gap-10">
      <div class="flex flex-col gap-5 lg:flex-row lg:items-stretch">
        <PlansList :plans="planTemplates" class="flex-1 min-w-0" />
        <WeeksList :weekly-plans="weeklySplitTemplates" class="flex-1 min-w-0" />
        <ExercisesList :exercises="exercises" class="flex-1 min-w-0" />
      </div>
      <div class="flex flex-col gap-5 lg:flex-row lg:items-stretch">
        <UsersList :users="manageableUsers" class="flex-1 min-w-0" />
        <ActivePlansList class="flex-1 min-w-0" />
      </div>
    </main>
  </div>
</template>
