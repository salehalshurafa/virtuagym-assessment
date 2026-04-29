<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import vgLogoDarkmode from '@/assets/vg-logo.png'
import HomeViewSkeleton from '@/components/skeletons/HomeViewSkeleton.vue'
import UserProfileSkeleton from '@/components/skeletons/UserProfileSkeleton.vue'
import UserProfile from '@/components/UserProfile.vue'
import axios from 'axios'
import type { User } from './types/user'
import type { Exercise } from './types/exercise'
import type { PlanTemplate, WeeklySplitTemplate } from './types/template'
import { useUsersStore } from './stores/users'
import { usePlanTemplatesStore } from './stores/planTemplates'
import { useExercisesStore } from './stores/exercises'
import { useWeeklySplitTemplatesStore } from './stores/weeklySplitTemplates'
import { useActivePlansStore, type ActivePlanRow } from './stores/activePlans'
import { useAuthStore } from './stores/auth'

const userStore = useUsersStore()
const planTemplatesStore = usePlanTemplatesStore()
const exerciseStore = useExercisesStore()
const weeklySplitTemplatesStore = useWeeklySplitTemplatesStore()
const activePlansStore = useActivePlansStore()
const authStore = useAuthStore()
const route = useRoute()
const isBootstrapping = ref(false)
const API_URL = import.meta.env.VITE_API_URL

// Public routes (login/signup) skip the dashboard chrome entirely — they
// have their own full-page layouts.
const isPublicRoute = computed(() => route.meta.public === true)

const loadDashboardData = async () => {
  if (!authStore.isAuthenticated) return
  isBootstrapping.value = true
  try {
    const [usersResult, planResult, exerciseResult, weeklyPlanResult, activePlansResult] =
      await Promise.allSettled([
        axios.get<User[]>(`${API_URL}/api/users`),
        axios.get<PlanTemplate[]>(`${API_URL}/api/plan-templates`),
        axios.get<Exercise[]>(`${API_URL}/api/exercises`),
        axios.get<WeeklySplitTemplate[]>(`${API_URL}/api/weekly-split-templates`),
        axios.get<ActivePlanRow[]>(`${API_URL}/api/plans/active`),
      ])

    if (authStore.me) userStore.initMe(authStore.me)

    if (usersResult.status === 'fulfilled' && usersResult.value.data) {
      userStore.initUsers(usersResult.value.data)
    } else if (usersResult.status === 'rejected') {
      console.error('Failed to load users:', usersResult.reason)
    }

    if (planResult.status === 'fulfilled' && planResult.value.data) {
      planTemplatesStore.initTemplates(planResult.value.data)
    } else if (planResult.status === 'rejected') {
      console.error('Failed to load plan templates:', planResult.reason)
    }

    if (exerciseResult.status === 'fulfilled' && exerciseResult.value.data) {
      exerciseStore.initExercises(exerciseResult.value.data)
    }

    if (weeklyPlanResult.status === 'fulfilled' && weeklyPlanResult.value.data) {
      weeklySplitTemplatesStore.initTemplates(weeklyPlanResult.value.data)
    } else if (weeklyPlanResult.status === 'rejected') {
      console.error('Failed to load weekly split templates:', weeklyPlanResult.reason)
    }

    if (activePlansResult.status === 'fulfilled' && activePlansResult.value.data) {
      activePlansStore.initActivePlans(activePlansResult.value.data)
    } else if (activePlansResult.status === 'rejected') {
      console.error('Failed to load active plans:', activePlansResult.reason)
    }
  } finally {
    isBootstrapping.value = false
  }
}

onMounted(async () => {
  // The router guard already runs auth.bootstrap() before any navigation
  // resolves, so by the time the App component mounts we know whether
  // authStore.me is set. Just hydrate the dashboard if we are.
  await loadDashboardData()
})

// Re-load when the user logs in mid-session (e.g. signup flow).
watch(
  () => authStore.isAuthenticated,
  async (isAuthed, wasAuthed) => {
    if (isAuthed && !wasAuthed) {
      await loadDashboardData()
    }
  },
)
</script>

<template>
  <!-- Login + signup take over the viewport entirely. -->
  <RouterView v-if="isPublicRoute" />

  <div v-else class="flex flex-col min-h-screen">
    <nav
      class="sticky top-0 z-50 bg-[#181818] px-3 py-3 sm:px-5 sm:py-5 flex items-center justify-between gap-3"
    >
      <div class="flex gap-2 items-center min-w-0">
        <img :src="vgLogoDarkmode" alt="Virtuagym" class="w-8 h-8 sm:w-10 sm:h-10 shrink-0" />
        <span class="text-white font-extrabold text-lg sm:text-2xl truncate">virtuagym</span>
      </div>
      <UserProfile v-if="!isBootstrapping" class="ml-auto shrink-0" />
      <UserProfileSkeleton v-else class="ml-auto shrink-0" />
    </nav>
    <main class="px-3 py-3 sm:px-6 lg:px-10">
      <HomeViewSkeleton v-if="isBootstrapping" />
      <RouterView v-else />
    </main>
  </div>
</template>
