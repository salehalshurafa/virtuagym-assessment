<script setup lang="ts">
import SkeletonBlock from './SkeletonBlock.vue'
</script>

<template>
  <div class="flex items-center gap-3 rounded-full px-2 py-1.5 pr-4">
    <SkeletonBlock class="h-10 w-10 rounded-full" />
    <div class="flex flex-col gap-1.5">
      <SkeletonBlock class="h-3 w-28" />
      <SkeletonBlock class="h-2.5 w-36" />
    </div>
  </div>
</template>
