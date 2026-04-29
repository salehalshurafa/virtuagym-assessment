<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Trash2 } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import AvatarUploader from '@/components/AvatarUploader.vue'
import TimezoneSelect from '@/components/TimezoneSelect.vue'
import { useUsersStore } from '@/stores/users'
import { useAuthStore } from '@/stores/auth'
import type { Gender, User } from '@/types/user'
import axios from 'axios'

const props = defineProps<{
  user: User
}>()

const open = defineModel<boolean>('open', { required: true })

const usersStore = useUsersStore()
const auth = useAuthStore()
const router = useRouter()

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const timezone = ref('')
const gender = ref<Gender | ''>('')
const phoneNumber = ref('')
const avatarUrl = ref<string | null>(null)
const confirmingDelete = ref(false)

const API_URL = import.meta.env.VITE_API_URL

const loadUser = () => {
  firstName.value = props.user.firstName
  lastName.value = props.user.lastName
  email.value = props.user.email
  timezone.value =
    (props.user as User & { timezone?: string }).timezone ?? auth.browserTimezone() ?? 'UTC'
  gender.value = (props.user.gender ?? '') as Gender | ''
  phoneNumber.value = props.user.phoneNumber ?? ''
  avatarUrl.value = props.user.avatarUrl ?? null
}

const fullName = computed(() => `${firstName.value} ${lastName.value}`.trim() || 'User')

const isValid = computed(
  () =>
    firstName.value.trim() !== '' &&
    lastName.value.trim() !== '' &&
    email.value.trim() !== '' &&
    timezone.value.trim() !== '',
)

const changesMade = computed(() => {
  const u = props.user as User & { timezone?: string }
  const currentGender = (props.user.gender ?? '') as Gender | ''
  const currentPhone = (props.user.phoneNumber ?? '') as string
  const currentAvatar = (props.user.avatarUrl ?? null) as string | null
  return (
    firstName.value.trim() !== props.user.firstName ||
    lastName.value.trim() !== props.user.lastName ||
    email.value.trim() !== props.user.email ||
    timezone.value.trim() !== (u.timezone ?? 'UTC') ||
    gender.value !== currentGender ||
    phoneNumber.value.trim() !== currentPhone ||
    avatarUrl.value !== currentAvatar
  )
})

const canSave = computed(() => isValid.value && changesMade.value)

const submitting = ref(false)
const saveError = ref<string | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const handleSave = async () => {
  if (!canSave.value || submitting.value) return

  const u = props.user as User & { timezone?: string }
  const payload: Partial<{
    firstName: string
    lastName: string
    email: string
    timezone: string
    gender: Gender | null
    phoneNumber: string | null
    avatarUrl: string | null
  }> = {}

  const fn = firstName.value.trim()
  const ln = lastName.value.trim()
  const em = email.value.trim()
  const tz = timezone.value.trim()
  const ph = phoneNumber.value.trim()
  const currentGender = (props.user.gender ?? '') as Gender | ''
  const currentPhone = (props.user.phoneNumber ?? '') as string
  const currentAvatar = (props.user.avatarUrl ?? null) as string | null

  if (fn !== u.firstName) payload.firstName = fn
  if (ln !== u.lastName) payload.lastName = ln
  if (em !== u.email) payload.email = em
  if (tz !== (u.timezone ?? 'UTC')) payload.timezone = tz
  if (gender.value !== currentGender) payload.gender = gender.value === '' ? null : gender.value
  if (ph !== currentPhone) payload.phoneNumber = ph === '' ? null : ph
  if (avatarUrl.value !== currentAvatar) payload.avatarUrl = avatarUrl.value

  if (Object.keys(payload).length === 0) {
    open.value = false
    return
  }

  submitting.value = true
  saveError.value = null
  try {
    const response = await axios.patch(`${API_URL}/api/users/${props.user.id}`, payload)

    if (response.data) {
      usersStore.updateUser(props.user.id, {
        firstName: response.data.firstName,
        lastName: response.data.lastName,
        email: response.data.email,
        gender: response.data.gender ?? null,
        phoneNumber: response.data.phoneNumber ?? null,
        avatarUrl: response.data.avatarUrl ?? null,
      })

      auth.patchMe({
        firstName: response.data.firstName,
        lastName: response.data.lastName,
        email: response.data.email,
      })
      open.value = false
    }
  } catch (error) {
    console.error('Error updating user profile:', error)
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      saveError.value = 'That email is already in use by another account.'
    } else {
      saveError.value = "We couldn't save your profile. Please try again later."
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async () => {
  if (deleting.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await axios.delete(`${API_URL}/api/users/${props.user.id}`)
    const isSelf = auth.me?.id === props.user.id

    usersStore.deleteUser(props.user.id)
    open.value = false

    if (isSelf) {
      await auth.logout()
      router.replace('/login')
    }
  } catch (error) {
    console.error('Error deleting user account:', error)
    deleteError.value = "We couldn't delete your account. Please try again later."
  } finally {
    deleting.value = false
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    loadUser()
    confirmingDelete.value = false
  }
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent
      class="dark sm:max-w-md p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37]"
    >
      <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-4">
        <DialogTitle class="text-2xl text-white">Profile</DialogTitle>
      </DialogHeader>

      <div class="flex flex-col gap-5 px-6 py-5">
        <AvatarUploader v-model="avatarUrl" :name="fullName" :disabled="submitting" />

        <div class="flex flex-col gap-2">
          <label for="profile-first-name" class="text-sm font-medium text-white">
            First name
          </label>
          <Input
            id="profile-first-name"
            v-model="firstName"
            placeholder="First name"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-2">
          <label for="profile-last-name" class="text-sm font-medium text-white"> Last name </label>
          <Input
            id="profile-last-name"
            v-model="lastName"
            placeholder="Last name"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-2">
          <label for="profile-email" class="text-sm font-medium text-white">Email</label>
          <Input
            id="profile-email"
            v-model="email"
            type="email"
            placeholder="email@example.com"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-2">
          <label for="profile-timezone" class="text-sm font-medium text-white">
            Time zone
            <span class="text-xs font-normal text-[#a0a09a]"> (controls how plan dates land) </span>
          </label>
          <TimezoneSelect id="profile-timezone" v-model="timezone" :disabled="submitting" />
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-sm font-medium text-white">Gender</label>
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
            <button
              type="button"
              class="rounded-md border border-[#3a3a37] bg-transparent px-3 py-1.5 text-xs font-medium text-[#a0a09a] transition-colors hover:cursor-pointer hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
              :disabled="gender === ''"
              @click="gender = ''"
            >
              Clear
            </button>
          </div>
        </div>

        <div class="flex flex-col gap-2">
          <label for="profile-phone" class="text-sm font-medium text-white">
            Phone number
            <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
          </label>
          <Input
            id="profile-phone"
            v-model="phoneNumber"
            type="tel"
            placeholder="+31 6 1234 5678"
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <section class="flex flex-col gap-3 pt-2">
          <h3 class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]">
            Danger Zone
          </h3>

          <div v-if="!confirmingDelete" class="flex items-center justify-between gap-4">
            <p class="text-sm text-[#a0a09a]">
              Permanently delete your account. This action cannot be undone.
            </p>
            <button
              type="button"
              class="flex shrink-0 items-center gap-1 rounded-md border border-red-600/60 bg-transparent px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:cursor-pointer hover:bg-red-600/10 hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-600"
              @click="confirmingDelete = true"
            >
              <Trash2 class="h-3.5 w-3.5" />
              Delete account
            </button>
          </div>

          <div
            v-else
            class="flex flex-col gap-3 rounded-md border border-red-600/60 bg-red-600/10 p-4"
          >
            <p class="text-sm font-semibold text-red-300">
              Are you sure you want to delete your account?
            </p>
            <p class="text-xs text-red-200/80">
              This is permanent and cannot be undone. Your profile, plan history, and any
              assignments will be removed.
            </p>
            <p v-if="deleteError" class="text-xs text-rose-300">{{ deleteError }}</p>
            <div class="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63] disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="deleting"
                @click="confirmingDelete = false"
              >
                Cancel
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-red-600 bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="deleting"
                @click="handleDelete"
              >
                <Trash2 class="h-3.5 w-3.5" />
                {{ deleting ? 'Deleting…' : 'Confirm delete' }}
              </button>
            </div>
          </div>
        </section>
      </div>

      <div class="flex flex-col gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3">
        <p v-if="saveError" class="text-right text-xs text-rose-300">{{ saveError }}</p>
        <div class="flex items-center justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="submitting"
            @click="open = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canSave || submitting"
            @click="handleSave"
          >
            <Check class="h-3.5 w-3.5" />
            {{ submitting ? 'Saving…' : 'Save' }}
          </button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
