<script setup lang="ts">
import ActivePlansListSkeleton from './ActivePlansListSkeleton.vue'
import ExercisesListSkeleton from './ExercisesListSkeleton.vue'
import PlansListSkeleton from './PlansListSkeleton.vue'
import SkeletonBlock from './SkeletonBlock.vue'
import UsersListSkeleton from './UsersListSkeleton.vue'
</script>

<template>
  <div class="flex flex-col gap-10">
    <header class="flex flex-col gap-3">
      <SkeletonBlock class="h-9 w-80" />
      <SkeletonBlock class="h-5 w-40" />
    </header>

    <main class="flex flex-col gap-10">
      <div class="flex gap-5">
        <PlansListSkeleton />
        <PlansListSkeleton />
        <ExercisesListSkeleton />
      </div>

      <div class="flex flex-col gap-5 lg:flex-row lg:items-stretch">
        <UsersListSkeleton class="flex-1 min-w-0" />
        <ActivePlansListSkeleton class="flex-1 min-w-0" />
      </div>
    </main>
  </div>
</template>
