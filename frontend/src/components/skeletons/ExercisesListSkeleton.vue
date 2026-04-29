<script setup lang="ts">
import SkeletonBlock from './SkeletonBlock.vue'
</script>

<template>
  <section class="flex w-130 flex-col gap-4 rounded-md border border-[#3a3a37] p-4">
    <header class="flex items-center justify-between">
      <SkeletonBlock class="h-7 w-28" />
      <SkeletonBlock class="h-7 w-24" />
    </header>

    <div class="flex gap-3">
      <SkeletonBlock class="h-10 flex-1" />
      <SkeletonBlock class="h-10 w-40" />
      <SkeletonBlock class="h-10 w-16" />
    </div>

    <div class="flex flex-col gap-2">
      <div
        v-for="index in 3"
        :key="index"
        class="flex items-center gap-3 rounded-lg border border-[#3a3a37] bg-[#2a2a28]/60 px-4 py-3"
      >
        <SkeletonBlock class="h-4 flex-1" />
        <SkeletonBlock class="h-6 w-20 rounded-full" />
        <SkeletonBlock class="h-6 w-6 rounded-full" />
        <SkeletonBlock class="h-4 w-12" />
      </div>
    </div>
  </section>
</template>
