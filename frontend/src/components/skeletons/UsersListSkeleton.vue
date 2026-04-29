<script setup lang="ts">
import SkeletonBlock from './SkeletonBlock.vue'
</script>

<template>
  <section class="flex flex-col gap-4 rounded-md border border-[#3a3a37] p-4">
    <div class="flex items-center justify-between gap-3">
      <SkeletonBlock class="h-7 w-20" />
      <SkeletonBlock class="h-9 w-28 rounded-md" />
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <SkeletonBlock class="h-10 min-w-48 flex-1" />
    </div>

    <div class="overflow-hidden rounded-md border border-[#3a3a37]">
      <div class="grid grid-cols-[1.6fr_1fr_1.2fr_1.6fr] gap-4 border-b border-[#3a3a37] px-4 py-3">
        <SkeletonBlock class="h-3 w-16" />
        <SkeletonBlock class="h-3 w-14" />
        <SkeletonBlock class="h-3 w-20" />
        <SkeletonBlock class="h-3 w-16" />
      </div>

      <div
        v-for="index in 5"
        :key="index"
        class="grid grid-cols-[1.6fr_1fr_1.2fr_1.6fr] items-center gap-4 border-b border-[#3a3a37]/60 px-4 py-4 last:border-0"
      >
        <div class="flex items-center gap-3">
          <SkeletonBlock class="h-9 w-9 rounded-full" />
          <SkeletonBlock class="h-4 w-28" />
        </div>
        <SkeletonBlock class="h-4 w-16" />
        <SkeletonBlock class="h-4 w-32" />
        <SkeletonBlock class="h-4 w-44" />
      </div>
    </div>
  </section>
</template>
