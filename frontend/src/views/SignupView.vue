<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { UserPlus } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import TimezoneSelect from '@/components/TimezoneSelect.vue'
import { useAuthStore } from '@/stores/auth'
import type { Gender } from '@/types/user'
import vgLogoDarkmode from '@/assets/vg-logo.png'

const router = useRouter()
const auth = useAuthStore()

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const passwordConfirm = ref('')
const gender = ref<Gender | ''>('')
const phoneNumber = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

const detectedTimezone = ref(auth.browserTimezone() ?? 'UTC')

const passwordsMatch = computed(
  () => password.value.length > 0 && password.value === passwordConfirm.value,
)

const canSubmit = computed(
  () =>
    firstName.value.trim() !== '' &&
    lastName.value.trim() !== '' &&
    email.value.trim() !== '' &&
    password.value.length >= 8 &&
    passwordsMatch.value,
)

const onSubmit = async () => {
  if (submitting.value) return
  if (!canSubmit.value) {
    if (password.value.length < 8) {
      error.value = 'Password must be at least 8 characters.'
    } else if (!passwordsMatch.value) {
      error.value = 'Passwords do not match.'
    } else {
      error.value = 'Please fill in every field.'
    }
    return
  }

  submitting.value = true
  error.value = null
  try {
    await auth.signup({
      firstName: firstName.value.trim(),
      lastName: lastName.value.trim(),
      email: email.value.trim(),
      password: password.value,
      timezone: detectedTimezone.value,
      gender: gender.value === '' ? null : gender.value,
      phoneNumber: phoneNumber.value.trim() === '' ? null : phoneNumber.value.trim(),
    })
    router.replace('/')
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      error.value = 'An account with that email already exists.'
    } else {
      error.value = "Couldn't create your account. Please try again."
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
        <h1 class="text-2xl font-bold">Create your account</h1>
        <p class="text-xs text-[#a0a09a]">Manage workout plans, exercises and users.</p>
      </div>

      <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1.5">
            <label for="firstName" class="text-sm font-medium text-white">First name</label>
            <Input
              id="firstName"
              v-model="firstName"
              autocomplete="given-name"
              class="bg-[#2a2a28] border-[#3a3a37] text-white"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <label for="lastName" class="text-sm font-medium text-white">Last name</label>
            <Input
              id="lastName"
              v-model="lastName"
              autocomplete="family-name"
              class="bg-[#2a2a28] border-[#3a3a37] text-white"
            />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="email" class="text-sm font-medium text-white">Email</label>
          <Input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="password" class="text-sm font-medium text-white">
            Password
            <span class="text-xs font-normal text-[#a0a09a]">(min 8 characters)</span>
          </label>
          <Input
            id="password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="password-confirm" class="text-sm font-medium text-white">
            Confirm password
          </label>
          <Input
            id="password-confirm"
            v-model="passwordConfirm"
            type="password"
            autocomplete="new-password"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="timezone" class="text-sm font-medium text-white">
            Time zone
            <span class="text-xs font-normal text-[#a0a09a]">(detected — change if wrong)</span>
          </label>
          <TimezoneSelect id="timezone" v-model="detectedTimezone" :disabled="submitting" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-white">
            Gender
            <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="opt in ['male', 'female', 'other'] as const"
              :key="opt"
              type="button"
              :class="[
                'rounded-md border px-3 py-1.5 text-xs font-medium capitalize transition-colors hover:cursor-pointer focus:outline-none focus:ring-2',
                gender === opt
                  ? 'border-[#ff6f14] bg-[#ff6f14]/15 text-[#ff7e2a] focus:ring-[#ff6f14]'
                  : 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf] hover:border-[#55554f] hover:text-white focus:ring-[#6a6a63]',
              ]"
              @click="gender = gender === opt ? '' : opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="signup-phone" class="text-sm font-medium text-white">
            Phone number
            <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
          </label>
          <Input
            id="signup-phone"
            v-model="phoneNumber"
            type="tel"
            autocomplete="tel"
            placeholder="+31 6 1234 5678"
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
          <UserPlus class="h-4 w-4" />
          {{ submitting ? 'Creating account…' : 'Create account' }}
        </button>
      </form>

      <p class="text-center text-xs text-[#a0a09a]">
        Already have an account?
        <RouterLink to="/login" class="font-medium text-[#ff6f14] hover:underline"
          >Sign in</RouterLink
        >
      </p>
    </div>
  </div>
</template>
