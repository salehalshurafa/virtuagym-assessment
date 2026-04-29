<script setup lang="ts">
withDefaults(
  defineProps<{
    class?: string
  }>(),
  {
    class: '',
  },
)
</script>

<template>
  <div
    :class="[
      'animate-pulse rounded-md bg-[#2a2a28] shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]',
      $props.class,
    ]"
  />
</template>
