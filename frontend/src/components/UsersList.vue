<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { User } from '@/types/user'
import { Input } from '@/components/ui/input'
import Table from './ui/table/Table.vue'
import TableHeader from './ui/table/TableHeader.vue'
import TableRow from './ui/table/TableRow.vue'
import TableHead from './ui/table/TableHead.vue'
import TableBody from './ui/table/TableBody.vue'
import TableCell from './ui/table/TableCell.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import UserDetailsDialog from '@/components/UserDetailsDialog.vue'
import AssignPlansDialog from '@/components/AssignPlansDialog.vue'
import AddUserDialog from '@/components/AddUserDialog.vue'

const props = defineProps<{
  users: User[]
}>()

const ROW_CAP = 5

const searchQuery = ref('')
const selectedUserId = ref<string | null>(null)
const assignDialogOpen = ref(false)
const assignPreselectedUserIds = ref<string[]>([])

const openAssignDialog = (userIds: string[] = []) => {
  assignPreselectedUserIds.value = userIds
  assignDialogOpen.value = true
}

const handleAssignRequest = (userId: string) => {
  selectedUserId.value = null
  openAssignDialog([userId])
}

const filteredUsers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return props.users.filter((u) => {
    if (q) {
      const fullName = `${u.firstName} ${u.lastName}`.toLowerCase()
      const email = u.email.toLowerCase()
      if (!fullName.includes(q) && !email.includes(q)) return false
    }
    return true
  })
})

const hasActiveFilters = computed(() => !!searchQuery.value)

const displayedUsers = computed(() =>
  hasActiveFilters.value ? filteredUsers.value : filteredUsers.value.slice(0, ROW_CAP),
)

const clearFilters = () => {
  searchQuery.value = ''
}
</script>

<template>
  <section class="flex flex-col gap-4 border border-[#3a3a37] rounded-md p-4">
    <div class="flex items-center justify-between gap-3">
      <h2 class="text-2xl font-bold text-white">Users</h2>
      <AddUserDialog />
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <div class="relative min-w-48 flex-1">
        <Input
          v-model="searchQuery"
          class="bg-[#2a2a28] border-[#3a3a37] border rounded-md px-4 py-2 pr-10 text-white text-sm focus:outline-none focus:border-[#6a6a63]"
          placeholder="Search by name or email..."
          aria-label="Search users by name or email"
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
      <button
        v-if="hasActiveFilters"
        type="button"
        class="flex items-center gap-1 rounded-md border border-[#ff6f14] px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#ff6f14]/10 focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
        @click="clearFilters"
      >
        <X class="h-3.5 w-3.5" />
        Clear filters
      </button>
    </div>

    <div
      class="overflow-x-auto"
      :class="hasActiveFilters ? 'max-h-[28rem] overflow-y-auto' : ''"
    >
      <Table>
        <TableHeader>
          <TableRow class="border-[#3a3a37] hover:bg-transparent">
            <TableHead class="px-3 py-2 text-xs font-medium uppercase text-[#a0a09a]">
              User
            </TableHead>
            <TableHead class="px-3 py-2 text-xs font-medium uppercase text-[#a0a09a]">
              Gender
            </TableHead>
            <TableHead class="px-3 py-2 text-xs font-medium uppercase text-[#a0a09a]">
              Time zone
            </TableHead>
            <TableHead class="px-3 py-2 text-xs font-medium uppercase text-[#a0a09a]">
              Email
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="user in displayedUsers"
            :key="user.id"
            class="border-[#3a3a37]/60 cursor-pointer hover:bg-[#2a2a28]"
            :class="user.removed ? 'opacity-60' : ''"
            @click="selectedUserId = user.id"
          >
            <TableCell class="px-3 py-3">
              <div class="flex items-center gap-3">
                <UserAvatar
                  :name="`${user.firstName} ${user.lastName}`"
                  :avatar-url="user.avatarUrl"
                />
                <span
                  class="whitespace-nowrap text-sm font-medium text-white"
                  :class="user.removed ? 'line-through decoration-[#a0a09a]/50' : ''"
                >
                  {{ user.firstName }} {{ user.lastName }}
                </span>
                <span
                  v-if="user.removed"
                  class="rounded-full border border-rose-500/40 bg-rose-600/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-rose-300"
                >
                  Removed
                </span>
              </div>
            </TableCell>
            <TableCell class="px-3 py-3 capitalize text-[#d4d4cf]">
              {{ user.gender ?? '—' }}
            </TableCell>
            <TableCell class="px-3 py-3 text-[#d4d4cf]">
              {{ user.timezone ?? 'UTC' }}
            </TableCell>
            <TableCell class="px-3 py-3 text-[#d4d4cf]">{{ user.email }}</TableCell>
          </TableRow>
          <TableRow v-if="!displayedUsers.length" class="border-0 hover:bg-transparent">
            <TableCell colspan="4" class="px-3 py-6 text-center text-sm text-[#a0a09a]">
              {{ hasActiveFilters ? 'No users match the current filters' : 'No users yet' }}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <UserDetailsDialog
      v-if="selectedUserId"
      :user-id="selectedUserId"
      @close="selectedUserId = null"
      @request-assign="handleAssignRequest"
    />

    <AssignPlansDialog
      v-model:open="assignDialogOpen"
      :preselected-user-ids="assignPreselectedUserIds"
    />
  </section>
</template>
