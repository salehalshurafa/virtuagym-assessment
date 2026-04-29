<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { LogOut, User } from 'lucide-vue-next'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useUsersStore } from '@/stores/users'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/UserAvatar.vue'
import UserProfileDialog from '@/components/UserProfileDialog.vue'

const { me } = storeToRefs(useUsersStore())
const auth = useAuthStore()
const router = useRouter()

const profileDialogOpen = ref(false)

const fullName = computed(() => (me.value ? `${me.value.firstName} ${me.value.lastName}` : ''))

const handleLogOut = async () => {
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div>
    <template v-if="me">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <button
            type="button"
            class="flex items-center gap-3 rounded-full px-2 py-1.5 pr-4 text-left transition-colors hover:cursor-pointer hover:bg-[#2a2a28] focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
            :aria-label="`Open profile menu for ${fullName}`"
          >
            <UserAvatar :name="fullName" :avatar-url="me.avatarUrl" />
            <span class="flex flex-col leading-tight">
              <span class="text-sm font-medium text-white">{{ fullName }}</span>
              <span class="text-xs text-[#a0a09a]">{{ me.email }}</span>
            </span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          class="dark w-44 bg-[#181818] text-white border-[#3a3a37]"
          align="end"
        >
          <DropdownMenuItem
            class="focus:bg-[#2a2a28] focus:text-white hover:cursor-pointer"
            @select="profileDialogOpen = true"
          >
            <User class="h-4 w-4" />
            Profile
          </DropdownMenuItem>
          <DropdownMenuSeparator class="bg-[#3a3a37]" />
          <DropdownMenuItem
            class="focus:bg-[#2a2a28] focus:text-white hover:cursor-pointer"
            @select="handleLogOut"
          >
            <LogOut class="h-4 w-4" />
            Log Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <UserProfileDialog v-model:open="profileDialogOpen" :user="me" />
    </template>

    <div v-else class="flex items-center gap-3 rounded-full px-2 py-1.5 pr-4">
      <div class="h-10 w-10 animate-pulse rounded-full bg-[#2a2a28]" />
      <div class="flex flex-col gap-1.5">
        <div class="h-3 w-28 animate-pulse rounded bg-[#2a2a28]" />
        <div class="h-2.5 w-36 animate-pulse rounded bg-[#2a2a28]" />
      </div>
    </div>
  </div>
</template>
