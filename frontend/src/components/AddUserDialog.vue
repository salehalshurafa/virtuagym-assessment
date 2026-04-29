<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, Copy, UserPlus } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import TimezoneSelect from '@/components/TimezoneSelect.vue'
import { useUsersStore } from '@/stores/users'
import { useAuthStore } from '@/stores/auth'
import type { Gender, User } from '@/types/user'

const emit = defineEmits<{
  created: [user: User]
}>()

const usersStore = useUsersStore()
const auth = useAuthStore()

const open = ref(false)

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const timezone = ref('')
const gender = ref<Gender | ''>('')
const phoneNumber = ref('')
const tempPassword = ref('')

const submitting = ref(false)
const error = ref<string | null>(null)

const phase = ref<'form' | 'success'>('form')

const generatePassword = (): string => {
  const bytes = new Uint8Array(12)
  crypto.getRandomValues(bytes)
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

const reset = () => {
  firstName.value = ''
  lastName.value = ''
  email.value = ''
  timezone.value = auth.browserTimezone() ?? 'UTC'
  gender.value = ''
  phoneNumber.value = ''
  tempPassword.value = ''
  error.value = null
  phase.value = 'form'
  submitting.value = false
}

watch(open, (isOpen) => {
  if (isOpen) reset()
})

const canSubmit = computed(
  () => firstName.value.trim() !== '' && lastName.value.trim() !== '' && email.value.trim() !== '',
)

const handleSubmit = async () => {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  error.value = null
  const generated = generatePassword()
  try {
    const res = await axios.post<User>(`${import.meta.env.VITE_API_URL}/api/users`, {
      firstName: firstName.value.trim(),
      lastName: lastName.value.trim(),
      email: email.value.trim(),
      timezone: timezone.value.trim() || 'UTC',
      gender: gender.value === '' ? null : gender.value,
      phoneNumber: phoneNumber.value.trim() === '' ? null : phoneNumber.value.trim(),
      password: generated,
    })

    usersStore.users = [...usersStore.users, res.data]
    tempPassword.value = generated
    phase.value = 'success'
    emit('created', res.data)
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      error.value = 'A user with that email already exists.'
    } else {
      error.value = "Couldn't create the user. Please try again later."
    }
  } finally {
    submitting.value = false
  }
}

const copied = ref(false)
const copyPassword = async () => {
  try {
    await navigator.clipboard.writeText(tempPassword.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {}
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <button
        type="button"
        class="flex items-center gap-2 rounded-md border-2 border-[#3a3a37] bg-[#1f1f1d] px-3 py-1.5 text-xs font-semibold text-[#d4d4cf] transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
      >
        <UserPlus class="h-3.5 w-3.5" />
        Add user
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-md p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37]"
    >
      <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-4">
        <DialogTitle class="text-2xl text-white">
          {{ phase === 'form' ? 'Add user' : 'User created' }}
        </DialogTitle>
      </DialogHeader>

      <template v-if="phase === 'form'">
        <div class="flex flex-col gap-4 px-6 py-5">
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium text-white" for="add-user-first">First name</label>
              <Input
                id="add-user-first"
                v-model="firstName"
                class="bg-[#2a2a28] border-[#3a3a37] text-white"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-sm font-medium text-white" for="add-user-last">Last name</label>
              <Input
                id="add-user-last"
                v-model="lastName"
                class="bg-[#2a2a28] border-[#3a3a37] text-white"
              />
            </div>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-medium text-white" for="add-user-email">Email</label>
            <Input
              id="add-user-email"
              v-model="email"
              type="email"
              class="bg-[#2a2a28] border-[#3a3a37] text-white"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-medium text-white" for="add-user-tz">
              Time zone
              <span class="text-xs font-normal text-[#a0a09a]">(detected — change if wrong)</span>
            </label>
            <TimezoneSelect id="add-user-tz" v-model="timezone" :disabled="submitting" />
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
            <label class="text-sm font-medium text-white" for="add-user-phone">
              Phone number
              <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
            </label>
            <Input
              id="add-user-phone"
              v-model="phoneNumber"
              type="tel"
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
        </div>

        <div
          class="flex items-center justify-end gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3"
        >
          <button
            type="button"
            class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="submitting"
            @click="open = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canSubmit || submitting"
            @click="handleSubmit"
          >
            <Check class="h-3.5 w-3.5" />
            {{ submitting ? 'Creating…' : 'Create user' }}
          </button>
        </div>
      </template>

      <template v-else>
        <div class="flex flex-col gap-4 px-6 py-5">
          <p class="text-sm text-white">
            User created. Share this temporary password with them — they can change it after signing
            in.
          </p>
          <div
            class="flex items-center justify-between gap-3 rounded-md border border-[#ff6f14]/40 bg-[#ff6f14]/5 px-3 py-2.5"
          >
            <code class="font-mono text-sm text-[#ff7e2a] break-all">{{ tempPassword }}</code>
            <button
              type="button"
              class="flex shrink-0 items-center gap-1 rounded-md border border-[#3a3a37] px-2.5 py-1 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white"
              @click="copyPassword"
            >
              <Copy class="h-3 w-3" />
              {{ copied ? 'Copied!' : 'Copy' }}
            </button>
          </div>
          <p class="text-xs text-[#a0a09a]">
            We never store this in plain text — once you close this dialog it's gone.
          </p>
        </div>
        <div
          class="flex items-center justify-end gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3"
        >
          <button
            type="button"
            class="rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a]"
            @click="open = false"
          >
            Done
          </button>
        </div>
      </template>
    </DialogContent>
  </Dialog>
</template>
