<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { PlanTemplate } from '@/types/template'
import { Input } from '@/components/ui/input/index'
import AddPlanDialog from '@/components/AddPlanDialog.vue'
import PlanDialog from '@/components/PlanDialog.vue'

const props = defineProps<{
  plans: PlanTemplate[]
}>()

const searchQuery = ref('')
const SUMMARY_LIMIT = 3

const visiblePlans = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    return props.plans.filter((p) => p.title.toLowerCase().includes(q))
  }
  return [...props.plans].sort((a, b) => a.title.localeCompare(b.title)).slice(0, SUMMARY_LIMIT)
})
</script>

<template>
  <section class="flex flex-col gap-4 border border-[#3a3a37] rounded-md p-4">
    <header class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-white">Plan Templates</h2>
      <div class="flex items-center gap-1">
        <AddPlanDialog />
      </div>
    </header>

    <div class="relative">
      <Input
        v-model="searchQuery"
        class="bg-[#2a2a28] border-[#3a3a37] border rounded-md px-4 py-2 pr-10 text-white text-sm focus:outline-none focus:border-[#6a6a63]"
        placeholder="Search plans..."
        aria-label="Search plans"
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

    <ul
      v-if="visiblePlans.length"
      class="flex flex-col gap-2 max-h-[11rem] overflow-y-auto pr-1 scrollbar-thin"
    >
      <li v-for="plan in visiblePlans" :key="plan.id">
        <PlanDialog :plan="plan" />
      </li>
    </ul>
    <p v-else class="text-sm text-[#a0a09a] text-center">No plans match your search</p>
  </section>
</template>
