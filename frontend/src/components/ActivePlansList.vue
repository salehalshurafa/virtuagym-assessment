<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Search, Send, X } from 'lucide-vue-next'
import { Input } from '@/components/ui/input/index'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select/index'
import { useUsersStore } from '@/stores/users'
import { useActivePlansStore, type ActivePlanRow } from '@/stores/activePlans'
import ActivePlanDialog from '@/components/ActivePlanDialog.vue'
import AssignPlansDialog from '@/components/AssignPlansDialog.vue'
import ModifyUserPlanDialog from '@/components/ModifyUserPlanDialog.vue'
import type { DurationType } from '@/types/plan'

const activePlansStore = useActivePlansStore()
const { items, loading, loadError, initialised } = storeToRefs(activePlansStore)

const searchQuery = ref('')
const durationFilter = ref<DurationType | 'any'>('any')
const statusFilter = ref<'any' | 'in-progress' | 'paused' | 'mixed'>('any')

const assignDialogOpen = ref(false)

const usersStore = useUsersStore()
const { users } = storeToRefs(usersStore)

const openAssignDialog = () => {
  assignDialogOpen.value = true
}

const showSkeleton = computed(() => loading.value && !initialised.value)

onMounted(() => {
  if (!initialised.value && !loading.value) {
    activePlansStore.refresh()
  }
})

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return items.value.filter((row) => {
    if (q && !row.title.toLowerCase().includes(q)) return false
    if (durationFilter.value !== 'any' && row.durationType !== durationFilter.value) return false
    if (statusFilter.value !== 'any' && row.statusSummary !== statusFilter.value) return false
    return true
  })
})

const filtersActive = computed(
  () => !!searchQuery.value || durationFilter.value !== 'any' || statusFilter.value !== 'any',
)

const clearFilters = () => {
  searchQuery.value = ''
  durationFilter.value = 'any'
  statusFilter.value = 'any'
}

const previewAssignees = (row: ActivePlanRow): string => {
  const names = row.assignees.map((a) => `${a.firstName} ${a.lastName}`)
  if (names.length <= 2) return names.join(', ') || '—'
  return `${names[0]}, ${names[1]} +${names.length - 2}`
}

const openRow = ref<ActivePlanRow | null>(null)
const openPlan = (row: ActivePlanRow) => {
  openRow.value = row
}
const closeDialog = () => {
  openRow.value = null
  activePlansStore.refresh()
}

const onAssignDialogChange = (open: boolean) => {
  assignDialogOpen.value = open
  if (!open) activePlansStore.refresh()
}

const modifyDialogOpen = ref(false)
const modifyTargetUserId = ref<string | null>(null)
const onRequestModify = (userId: string) => {
  modifyTargetUserId.value = userId
  modifyDialogOpen.value = true
}
const onModifyDialogChange = (open: boolean) => {
  modifyDialogOpen.value = open
  if (!open) activePlansStore.refresh()
}

const _userIdsForDebug = computed(() => users.value.map((u) => u.id))
void _userIdsForDebug
</script>

<template>
  <section class="flex flex-col gap-4 border border-[#3a3a37] rounded-md p-4">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex flex-col min-w-0">
        <h2 class="text-2xl font-bold text-white">Active plans</h2>
        <p class="text-xs text-[#a0a09a]">Live plans assigned to one or more users.</p>
      </div>
      <button
        type="button"
        class="flex shrink-0 items-center gap-2 rounded-md border-2 border-[#ff6f14] bg-[#ff6f14] px-3 py-2 text-xs sm:text-sm font-semibold text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
        @click="openAssignDialog"
      >
        <Send class="h-4 w-4" />
        Assign plans
      </button>
    </header>

    <div class="flex flex-wrap items-end gap-3">
      <div class="relative flex-1 min-w-[14rem]">
        <Search
          class="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#a0a09a]"
        />
        <Input
          v-model="searchQuery"
          class="bg-[#2a2a28] border-[#3a3a37] border rounded-md px-4 py-2 pl-9 pr-9 text-white text-sm focus:outline-none focus:border-[#6a6a63]"
          placeholder="Search plan title…"
          aria-label="Search active plans"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="absolute inset-y-1 right-2 grid h-6 w-6 place-items-center rounded-full text-[#a0a09a] transition-colors hover:cursor-pointer hover:bg-[#3a3a37] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
          aria-label="Clear search"
          @click="searchQuery = ''"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-[#a0a09a]">Duration</label>
        <NativeSelect
          v-model="durationFilter"
          class="h-8 bg-[#2a2a28] border-[#3a3a37] text-xs text-white"
          aria-label="Filter by duration type"
        >
          <NativeSelectOption value="any">Any</NativeSelectOption>
          <NativeSelectOption value="days">Days</NativeSelectOption>
          <NativeSelectOption value="weeks">Weeks</NativeSelectOption>
          <NativeSelectOption value="months">Months</NativeSelectOption>
          <NativeSelectOption value="years">Years</NativeSelectOption>
        </NativeSelect>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs text-[#a0a09a]">Status</label>
        <NativeSelect
          v-model="statusFilter"
          class="h-8 bg-[#2a2a28] border-[#3a3a37] text-xs text-white"
          aria-label="Filter by status"
        >
          <NativeSelectOption value="any">Any</NativeSelectOption>
          <NativeSelectOption value="in-progress">In-progress</NativeSelectOption>
          <NativeSelectOption value="paused">Paused</NativeSelectOption>
          <NativeSelectOption value="mixed">Mixed</NativeSelectOption>
        </NativeSelect>
      </div>

      <button
        v-if="filtersActive"
        type="button"
        class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
        @click="clearFilters"
      >
        Clear filters
      </button>
    </div>

    <p
      v-if="loadError"
      class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
    >
      {{ loadError }}
    </p>

    <ul v-if="showSkeleton" class="flex flex-col gap-2" aria-hidden="true">
      <li
        v-for="i in 4"
        :key="`sk-${i}`"
        class="flex items-center gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3"
      >
        <div class="flex flex-1 flex-col gap-2 min-w-0">
          <div class="h-3.5 w-40 animate-pulse rounded bg-[#2a2a28]" />
          <div class="h-3 w-28 animate-pulse rounded bg-[#2a2a28]" />
        </div>
        <div class="hidden h-3 w-32 animate-pulse rounded bg-[#2a2a28] md:block" />
        <div class="h-5 w-20 animate-pulse rounded-full bg-[#2a2a28]" />
      </li>
    </ul>

    <div
      v-else-if="filtered.length === 0"
      class="rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-6 text-center text-sm text-[#a0a09a]"
    >
      <template v-if="filtersActive">No active plans match your filters.</template>
      <template v-else>No plans are currently assigned to anyone.</template>
    </div>

    <ul v-else class="flex flex-col gap-2">
      <li v-for="row in filtered" :key="row.id">
        <button
          type="button"
          class="flex w-full flex-wrap items-center gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3 text-left transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
          @click="openPlan(row)"
        >
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold text-white">{{ row.title }}</p>
            <p class="text-xs text-[#a0a09a]">
              {{ row.duration }} {{ row.durationType }} · {{ row.assignees.length }} user(s)
            </p>
          </div>
          <span class="hidden truncate text-xs text-[#d4d4cf] md:inline-block max-w-xs">
            {{ previewAssignees(row) }}
          </span>
          <span
            class="shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium"
            :class="
              row.statusSummary === 'in-progress'
                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                : row.statusSummary === 'paused'
                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                  : 'border-sky-500/40 bg-sky-500/10 text-sky-300'
            "
          >
            {{ row.statusSummary }}
          </span>
        </button>
      </li>
    </ul>

    <ActivePlanDialog
      v-if="openRow"
      :plan="openRow"
      @close="closeDialog"
      @request-modify="onRequestModify"
    />
    <AssignPlansDialog :open="assignDialogOpen" @update:open="onAssignDialogChange" />
    <ModifyUserPlanDialog
      v-if="modifyTargetUserId"
      :open="modifyDialogOpen"
      :user-id="modifyTargetUserId"
      @update:open="onModifyDialogChange"
    />
  </section>
</template>
