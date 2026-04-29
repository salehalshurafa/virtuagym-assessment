<script setup lang="ts">
import StepOneBasics from '@/components/plan-form/StepOneBasics.vue'
import PlanWorkoutsEditor from '@/components/plan-form/PlanWorkoutsEditor.vue'
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="flex flex-col gap-3">
      <h3 class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]">
        Basics
      </h3>
      <StepOneBasics />
    </section>

    <section class="flex flex-col gap-3">
      <h3 class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]">
        Workouts
      </h3>
      <PlanWorkoutsEditor />
    </section>
  </div>
</template>
