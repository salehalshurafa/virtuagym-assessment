<script setup lang="ts">
import SkeletonBlock from './SkeletonBlock.vue'
</script>

<template>
  <section class="flex flex-col gap-4 rounded-md border border-[#3a3a37] p-4">
    <div class="flex items-center justify-between gap-3">
      <div class="flex flex-col gap-2">
        <SkeletonBlock class="h-7 w-32" />
        <SkeletonBlock class="h-3 w-56" />
      </div>
      <SkeletonBlock class="h-9 w-32 rounded-md" />
    </div>

    <div class="flex flex-wrap items-end gap-3">
      <SkeletonBlock class="h-10 min-w-[14rem] flex-1" />
      <SkeletonBlock class="h-10 w-28" />
      <SkeletonBlock class="h-10 w-28" />
    </div>

    <ul class="flex flex-col gap-2">
      <li
        v-for="i in 4"
        :key="`sk-active-${i}`"
        class="flex items-center gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3"
      >
        <div class="flex flex-1 flex-col gap-2 min-w-0">
          <SkeletonBlock class="h-4 w-40" />
          <SkeletonBlock class="h-3 w-28" />
        </div>
        <SkeletonBlock class="hidden h-3 w-32 md:block" />
        <SkeletonBlock class="h-5 w-20 rounded-full" />
      </li>
    </ul>
  </section>
</template>
