<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { LogIn } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import vgLogoDarkmode from '@/assets/vg-logo.png'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

const onSubmit = async () => {
  if (submitting.value) return
  if (!email.value.trim() || !password.value) {
    error.value = 'Email and password are required.'
    return
  }
  submitting.value = true
  error.value = null
  try {
    await auth.login({ email: email.value.trim(), password: password.value })

    const redirect = (router.currentRoute.value.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      error.value = 'Invalid email or password.'
    } else {
      error.value = "Couldn't sign you in. Please try again."
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div
    class="dark min-h-screen w-full flex items-center justify-center bg-[#181818] px-6 py-10 text-white"
  >
    <div
      class="flex w-full max-w-md flex-col gap-6 rounded-lg border border-[#3a3a37] bg-[#1f1f1d] p-8 shadow-xl"
    >
      <div class="flex flex-col items-center gap-2">
        <img :src="vgLogoDarkmode" alt="Virtuagym" class="w-12 h-12" />
        <h1 class="text-2xl font-bold">Sign in to Virtuagym</h1>
        <p class="text-xs text-[#a0a09a]">Workout Plan Manager</p>
      </div>

      <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
        <div class="flex flex-col gap-1.5">
          <label for="email" class="text-sm font-medium text-white">Email</label>
          <Input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>
        <div class="flex flex-col gap-1.5">
          <label for="password" class="text-sm font-medium text-white">Password</label>
          <Input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <p
          v-if="error"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          {{ error }}
        </p>

        <button
          type="submit"
          class="flex items-center justify-center gap-1.5 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="submitting"
        >
          <LogIn class="h-4 w-4" />
          {{ submitting ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <p class="text-center text-xs text-[#a0a09a]">
        Don't have an account?
        <RouterLink to="/signup" class="font-medium text-[#ff6f14] hover:underline"
          >Create one</RouterLink
        >
      </p>
    </div>
  </div>
</template>
