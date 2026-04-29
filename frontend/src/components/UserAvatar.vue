<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  name: string
  avatarUrl?: string | null
}>()

const initials = computed(() => {
  const parts = props.name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return ''
  const first = parts[0]!.charAt(0)
  const last = parts.length > 1 ? (parts[parts.length - 1]!.charAt(0) ?? '') : ''
  return (first + last).toUpperCase()
})
</script>

<template>
  <img
    v-if="avatarUrl"
    :src="avatarUrl"
    :alt="name"
    class="h-9 w-9 shrink-0 rounded-full object-cover"
  />
  <span
    v-else
    class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#3a3a37] text-xs font-semibold text-white"
    :aria-label="name"
  >
    {{ initials }}
  </span>
</template>
