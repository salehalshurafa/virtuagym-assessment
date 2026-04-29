<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search, X } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import UserAvatar from '@/components/UserAvatar.vue'
import type { User } from '@/types/user'

const props = defineProps<{
  users: User[]
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const searchQuery = ref('')

const filteredUsers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return props.users
  return props.users.filter((u) => {
    const name = `${u.firstName} ${u.lastName}`.toLowerCase()
    return name.includes(q) || u.email.toLowerCase().includes(q)
  })
})

const isSelected = (id: string) => props.modelValue.includes(id)

const toggle = (id: string) => {
  if (isSelected(id)) {
    emit(
      'update:modelValue',
      props.modelValue.filter((uid) => uid !== id),
    )
  } else {
    emit('update:modelValue', [...props.modelValue, id])
  }
}

const selectAll = () => {
  emit('update:modelValue', filteredUsers.value.map((u) => u.id))
}

const clearAll = () => {
  emit('update:modelValue', [])
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center gap-2">
      <div class="relative flex-1">
        <Search class="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-[#a0a09a]" />
        <Input
          v-model="searchQuery"
          class="bg-[#2a2a28] border-[#3a3a37] text-sm text-white pl-8"
          placeholder="Search users..."
          aria-label="Search users"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="absolute hover:cursor-pointer top-1/2 right-2 grid h-5 w-5 -translate-y-1/2 place-items-center rounded-full text-[#a0a09a] transition-colors hover:bg-[#3a3a37] hover:text-white"
          aria-label="Clear search"
          @click="searchQuery = ''"
        >
          <X class="h-3 w-3" />
        </button>
      </div>
      <button
        type="button"
        class="rounded-md border border-[#3a3a37] px-2.5 py-1 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
        @click="selectAll"
      >
        Select all
      </button>
      <button
        v-if="modelValue.length"
        type="button"
        class="rounded-md border border-[#3a3a37] px-2.5 py-1 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
        @click="clearAll"
      >
        Clear
      </button>
    </div>

    <div
      class="flex flex-col gap-1 max-h-64 overflow-y-auto rounded-md border border-[#3a3a37] bg-[#1f1f1d] p-2 scrollbar-thin"
    >
      <p
        v-if="!filteredUsers.length"
        class="py-4 text-center text-xs text-[#a0a09a]"
      >
        No users match your search
      </p>
      <button
        v-for="user in filteredUsers"
        :key="user.id"
        type="button"
        class="flex items-center gap-3 rounded-md px-2 py-1.5 text-left transition-colors hover:cursor-pointer"
        :class="
          isSelected(user.id)
            ? 'bg-[#ff6f14]/10 hover:bg-[#ff6f14]/20'
            : 'hover:bg-[#2a2a28]'
        "
        @click="toggle(user.id)"
      >
        <input
          type="checkbox"
          :checked="isSelected(user.id)"
          class="h-3.5 w-3.5 accent-[#ff6f14]"
          @click.stop
          @change="toggle(user.id)"
        />
        <UserAvatar
          :name="`${user.firstName} ${user.lastName}`"
          :avatar-url="user.avatarUrl"
          class="h-7 w-7 text-[10px]"
        />
        <div class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-sm font-medium text-white">
            {{ user.firstName }} {{ user.lastName }}
          </span>
          <span class="truncate text-xs text-[#a0a09a]">{{ user.email }}</span>
        </div>
        <span
          v-if="user.latestPlan?.status === 'in-progress'"
          class="shrink-0 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-amber-300"
          title="Has an active plan — will be flagged as a conflict"
        >
          On plan
        </span>
        <span
          v-else-if="user.latestPlan?.status === 'paused'"
          class="shrink-0 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-amber-300"
          title="Has a paused plan — will be flagged as a conflict"
        >
          On paused plan
        </span>
      </button>
    </div>

    <p class="text-xs text-[#a0a09a]">
      {{ modelValue.length }} of {{ filteredUsers.length }} selected
    </p>
  </div>
</template>
