<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertTriangle, Ban, RotateCw } from 'lucide-vue-next'

export interface ConflictInfo {
  userId: string
  userName: string
  currentPlanTitle: string
  currentPlanStatus: 'in-progress' | 'paused'
}

export type ConflictDecision = 'force' | 'skip'

const props = defineProps<{
  conflicts: ConflictInfo[]
  submitting?: boolean
}>()

const emit = defineEmits<{
  decided: [decisions: Record<string, ConflictDecision>]
  cancel: []
}>()

const decisions = ref<Record<string, ConflictDecision>>({})

watch(
  () => props.conflicts.map((c) => c.userId).join(','),
  () => {
    decisions.value = {}
  },
)

const decide = (userId: string, choice: ConflictDecision) => {
  decisions.value = { ...decisions.value, [userId]: choice }
}

const allDecided = computed(() =>
  props.conflicts.every((c) => decisions.value[c.userId] !== undefined),
)

const onContinue = () => {
  if (!allDecided.value) return
  emit('decided', { ...decisions.value })
}
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded-md border-2 border-amber-500/60 bg-amber-500/10 px-4 py-3"
  >
    <div class="flex items-start gap-2 text-amber-200">
      <AlertTriangle class="h-4 w-4 shrink-0 mt-0.5" />
      <p class="text-sm font-medium">
        {{ conflicts.length }} user{{ conflicts.length === 1 ? '' : 's' }} already
        {{ conflicts.length === 1 ? 'has' : 'have' }} an active or paused plan. Decide what to do
        for each — Replace cancels the existing assignment first, Skip leaves them as-is:
      </p>
    </div>

    <ul class="flex flex-col gap-2">
      <li
        v-for="c in conflicts"
        :key="c.userId"
        class="flex flex-wrap items-center gap-3 rounded-md border border-amber-500/30 bg-[#1f1f1d] px-3 py-2"
      >
        <div class="flex flex-1 flex-col min-w-0">
          <span class="truncate text-sm font-medium text-white">{{ c.userName }}</span>
          <span class="truncate text-xs text-[#a0a09a]">
            <template v-if="c.currentPlanStatus === 'paused'">
              Currently <strong class="text-amber-300">paused</strong> on
            </template>
            <template v-else>Currently on </template>
            <strong class="text-[#d4d4cf]">{{ c.currentPlanTitle }}</strong>
          </span>
        </div>
        <div class="flex items-center gap-1.5">
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border-2 px-2.5 py-1 text-xs font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-40"
            :class="
              decisions[c.userId] === 'force'
                ? 'border-emerald-500 bg-emerald-500 text-white'
                : 'border-emerald-500/60 bg-emerald-500/5 text-emerald-300 hover:bg-emerald-500/15 hover:text-emerald-200 focus:ring-emerald-500/50'
            "
            :disabled="submitting"
            @click="decide(c.userId, 'force')"
          >
            <RotateCw class="h-3 w-3" />
            Replace
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border-2 px-2.5 py-1 text-xs font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-40"
            :class="
              decisions[c.userId] === 'skip'
                ? 'border-rose-500 bg-rose-600 text-white'
                : 'border-rose-500/60 bg-rose-600/5 text-rose-300 hover:bg-rose-600/15 hover:text-rose-200 focus:ring-rose-500/50'
            "
            :disabled="submitting"
            @click="decide(c.userId, 'skip')"
          >
            <Ban class="h-3 w-3" />
            Skip
          </button>
        </div>
      </li>
    </ul>

    <div class="flex items-center justify-end gap-2 pt-1">
      <button
        type="button"
        class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="submitting"
        @click="emit('cancel')"
      >
        Cancel assignment
      </button>
      <button
        type="button"
        class="flex items-center gap-1 rounded-md border-2 border-amber-500 bg-amber-500 px-3 py-1.5 text-xs font-medium text-[#181818] transition-colors hover:cursor-pointer hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="!allDecided || submitting"
        @click="onContinue"
      >
        {{ submitting ? 'Assigning…' : 'Continue' }}
      </button>
    </div>
  </div>
</template>
