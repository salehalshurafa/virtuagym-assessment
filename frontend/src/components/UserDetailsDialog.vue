<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, History, Loader2, Mail, Pencil, Plus, RotateCcw, Trash2, X } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import AvatarUploader from '@/components/AvatarUploader.vue'
import TimezoneSelect from '@/components/TimezoneSelect.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { useActivePlansStore } from '@/stores/activePlans'
import { useUsersStore } from '@/stores/users'
import type { Gender, PlanStatus, User } from '@/types/user'
import type { DurationType } from '@/types/plan'

interface HistoryRow {
  id: string
  userId: string
  planId: string
  planTitle: string
  startDate: string
  endDate: string
  status: PlanStatus
  remainingDays?: number | null
  assignedAt: string
  assignedByName?: string | null
  assignedByEmail?: string | null
}

const props = defineProps<{ userId: string }>()
const emit = defineEmits<{
  close: []
  requestAssign: [userId: string]
}>()

const requestAssign = () => {
  emit('requestAssign', props.userId)
}

const usersStore = useUsersStore()
const activePlansStore = useActivePlansStore()
const user = computed(() => usersStore.getById(props.userId))

const open = ref(true)
watch(open, (v) => {
  if (!v) emit('close')
})

const API_URL = import.meta.env.VITE_API_URL

const history = ref<HistoryRow[]>([])
const historyLoading = ref(false)
const historyError = ref<string | null>(null)

const fetchHistory = async (uid: string) => {
  historyLoading.value = true
  historyError.value = null
  try {
    const res = await axios.get<HistoryRow[]>(`${API_URL}/api/users/${uid}/assignments`)
    history.value = [...res.data].sort((a, b) =>
      a.assignedAt < b.assignedAt ? 1 : a.assignedAt > b.assignedAt ? -1 : 0,
    )
  } catch (err) {
    console.error('failed to load user history', err)
    historyError.value = "We couldn't load this user's plan history."
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

watch(
  () => props.userId,
  (uid) => {
    if (uid) fetchHistory(uid)
  },
  { immediate: true },
)

const toDate = (value: string | Date) => (value instanceof Date ? value : new Date(value))

const formatLong = (value: string | Date) =>
  toDate(value).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

const formatDateTime = (value: string | Date) =>
  toDate(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })

const durationLabels: Record<DurationType, string> = {
  days: 'day',
  weeks: 'week',
  months: 'month',
  years: 'year',
}

const formatDuration = (n: number, t: DurationType) =>
  `${n} ${durationLabels[t]}${n === 1 ? '' : 's'}`

type DisplayEntry = { label: string; classes: string }

const isEditing = ref(false)
const savingEdit = ref(false)
const editError = ref<string | null>(null)

const editFirstName = ref('')
const editLastName = ref('')
const editEmail = ref('')
const editTimezone = ref('')
const editGender = ref<Gender | ''>('')
const editPhoneNumber = ref('')
const editAvatarUrl = ref<string | null>(null)

const loadEditFields = (u: User) => {
  editFirstName.value = u.firstName
  editLastName.value = u.lastName
  editEmail.value = u.email
  editTimezone.value = u.timezone ?? 'UTC'
  editGender.value = (u.gender ?? '') as Gender | ''
  editPhoneNumber.value = u.phoneNumber ?? ''
  editAvatarUrl.value = u.avatarUrl ?? null
  editError.value = null
}

const beginEdit = () => {
  if (!user.value) return
  loadEditFields(user.value)
  isEditing.value = true
}

const cancelEdit = () => {
  if (savingEdit.value) return
  isEditing.value = false
  editError.value = null
}

const editFullName = computed(() => `${editFirstName.value} ${editLastName.value}`.trim() || 'User')

const editValid = computed(
  () =>
    editFirstName.value.trim() !== '' &&
    editLastName.value.trim() !== '' &&
    editEmail.value.trim() !== '' &&
    editTimezone.value.trim() !== '',
)

const editChanged = computed(() => {
  const u = user.value
  if (!u) return false
  const currentGender = (u.gender ?? '') as Gender | ''
  const currentPhone = (u.phoneNumber ?? '') as string
  const currentAvatar = (u.avatarUrl ?? null) as string | null
  return (
    editFirstName.value.trim() !== u.firstName ||
    editLastName.value.trim() !== u.lastName ||
    editEmail.value.trim() !== u.email ||
    editTimezone.value.trim() !== (u.timezone ?? 'UTC') ||
    editGender.value !== currentGender ||
    editPhoneNumber.value.trim() !== currentPhone ||
    editAvatarUrl.value !== currentAvatar
  )
})

const canSaveEdit = computed(() => editValid.value && editChanged.value)

const saveEdit = async () => {
  const u = user.value
  if (!u || !canSaveEdit.value || savingEdit.value) return

  const payload: Partial<{
    firstName: string
    lastName: string
    email: string
    timezone: string
    gender: Gender | null
    phoneNumber: string | null
    avatarUrl: string | null
  }> = {}

  const fn = editFirstName.value.trim()
  const ln = editLastName.value.trim()
  const em = editEmail.value.trim()
  const tz = editTimezone.value.trim()
  const ph = editPhoneNumber.value.trim()
  const currentGender = (u.gender ?? '') as Gender | ''
  const currentPhone = (u.phoneNumber ?? '') as string
  const currentAvatar = (u.avatarUrl ?? null) as string | null

  if (fn !== u.firstName) payload.firstName = fn
  if (ln !== u.lastName) payload.lastName = ln
  if (em !== u.email) payload.email = em
  if (tz !== (u.timezone ?? 'UTC')) payload.timezone = tz
  if (editGender.value !== currentGender) {
    payload.gender = editGender.value === '' ? null : editGender.value
  }
  if (ph !== currentPhone) payload.phoneNumber = ph === '' ? null : ph
  if (editAvatarUrl.value !== currentAvatar) payload.avatarUrl = editAvatarUrl.value

  if (Object.keys(payload).length === 0) {
    isEditing.value = false
    return
  }

  savingEdit.value = true
  editError.value = null
  let res: { data: User } | null = null
  try {
    res = await axios.patch<User>(`${API_URL}/api/users/${u.id}`, payload)
  } catch (err) {
    console.error('Failed to update user:', err)
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      editError.value = 'That email is already in use by another account.'
    } else {
      editError.value = "We couldn't save the changes. Please try again later."
    }
    savingEdit.value = false
    return
  }

  try {
    if (res?.data) {
      usersStore.updateUser(u.id, {
        firstName: res.data.firstName,
        lastName: res.data.lastName,
        email: res.data.email,
        gender: res.data.gender ?? null,
        phoneNumber: res.data.phoneNumber ?? null,
        avatarUrl: res.data.avatarUrl ?? null,
        timezone: res.data.timezone ?? 'UTC',
      })

      activePlansStore.updateAssignee(u.id, {
        firstName: res.data.firstName,
        lastName: res.data.lastName,
      })
    }
  } catch (localErr) {
    console.error('Local store update failed after successful save:', localErr)
  }

  isEditing.value = false
  savingEdit.value = false
}

const confirmingRemove = ref(false)
const removing = ref(false)
const removeError = ref<string | null>(null)

const beginRemove = () => {
  confirmingRemove.value = true
  removeError.value = null
}

const cancelRemove = () => {
  if (removing.value) return
  confirmingRemove.value = false
  removeError.value = null
}

const confirmRemove = async () => {
  const u = user.value
  if (!u || removing.value) return
  removing.value = true
  removeError.value = null
  try {
    await axios.delete(`${API_URL}/api/users/${u.id}`)

    usersStore.markRemoved(u.id)
    activePlansStore.removeAssignee(u.id)

    open.value = false
  } catch (err) {
    console.error('failed to remove user', err)
    removeError.value = "We couldn't remove this user. Please try again later."
  } finally {
    removing.value = false
  }
}

const restoring = ref(false)
const restoreError = ref<string | null>(null)

const handleRestore = async () => {
  const u = user.value
  if (!u || restoring.value) return
  restoring.value = true
  restoreError.value = null
  try {
    await usersStore.restoreUser(u.id)
    activePlansStore.refresh().catch(() => undefined)
  } catch (err) {
    console.error('failed to re-list user', err)
    restoreError.value = "We couldn't re-list this user. Please try again later."
  } finally {
    restoring.value = false
  }
}

watch(open, (isOpen) => {
  if (!isOpen) {
    isEditing.value = false
    confirmingRemove.value = false
    editError.value = null
    removeError.value = null
  }
})

const planStatusDisplay: Record<PlanStatus, DisplayEntry> = {
  'in-progress': {
    label: 'In progress',
    classes: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  },
  completed: {
    label: 'Completed',
    classes: 'border-green-500/30 bg-green-500/10 text-green-300',
  },
  cancelled: {
    label: 'Cancelled',
    classes: 'border-red-500/30 bg-red-500/10 text-red-300',
  },
  paused: {
    label: 'Paused',
    classes: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300',
  },
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent
      v-if="user"
      class="dark sm:max-w-2xl max-h-[90vh] p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37] overflow-hidden"
    >
      <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-5">
        <div class="flex items-center gap-4">
          <UserAvatar
            :name="`${user.firstName} ${user.lastName}`"
            :avatar-url="user.avatarUrl"
            class="h-14 w-14 text-base"
          />
          <div class="flex flex-col gap-0.5 min-w-0">
            <DialogTitle class="text-2xl font-bold text-white truncate">
              {{ user.firstName }} {{ user.lastName }}
            </DialogTitle>
            <a
              :href="`mailto:${user.email}`"
              class="flex items-center gap-1.5 text-sm text-[#a0a09a] hover:text-white truncate"
            >
              <Mail class="h-3.5 w-3.5 shrink-0" />
              <span class="truncate">{{ user.email }}</span>
            </a>
          </div>
        </div>
      </DialogHeader>

      <div class="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5 scrollbar-thin">
        <section class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h3 class="text-xs font-semibold uppercase text-[#a0a09a]">Profile</h3>
            <div v-if="!isEditing" class="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-2.5 py-1 text-[11px] font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
                @click="beginEdit"
              >
                <Pencil class="h-3 w-3" />
                Edit
              </button>
              <button
                v-if="!user.removed"
                type="button"
                class="flex items-center gap-1 rounded-md border border-rose-600/60 bg-transparent px-2.5 py-1 text-[11px] font-medium text-rose-300 transition-colors hover:cursor-pointer hover:bg-rose-600/10 hover:text-rose-200 focus:outline-none focus:ring-2 focus:ring-rose-500/50"
                @click="beginRemove"
              >
                <Trash2 class="h-3 w-3" />
                Remove
              </button>
              <button
                v-else
                type="button"
                class="flex items-center gap-1 rounded-md border border-emerald-500/60 bg-emerald-500/5 px-2.5 py-1 text-[11px] font-medium text-emerald-300 transition-colors hover:cursor-pointer hover:bg-emerald-500/15 hover:text-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="restoring"
                @click="handleRestore"
              >
                <RotateCcw class="h-3 w-3" />
                {{ restoring ? 'Re-listing…' : 'Re-list' }}
              </button>
            </div>
          </div>

          <div
            v-if="user.removed && !confirmingRemove"
            class="flex flex-col gap-1 rounded-md border border-rose-500/40 bg-rose-600/10 px-4 py-2.5 text-xs text-rose-200"
          >
            <p>
              This user is removed and hidden from assignment pickers. Click
              <strong>Re-list</strong> to bring them back.
            </p>
            <p v-if="restoreError" class="text-rose-300">{{ restoreError }}</p>
          </div>

          <div
            v-if="confirmingRemove"
            class="flex flex-col gap-2 rounded-md border border-rose-600/60 bg-rose-600/10 px-4 py-3"
          >
            <p class="text-sm font-semibold text-rose-200">
              Remove {{ user.firstName }} {{ user.lastName }}?
            </p>
            <p class="text-xs text-rose-200/80">
              They will be hidden from the users list and the assignment pickers. Their plan history
              is preserved on the server.
            </p>
            <p v-if="removeError" class="text-xs text-rose-300">{{ removeError }}</p>
            <div class="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                class="rounded-md border border-[#3a3a37] px-3 py-1 text-[11px] font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="removing"
                @click="cancelRemove"
              >
                Cancel
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-rose-600 bg-rose-600 px-3 py-1 text-[11px] font-medium text-white transition-colors hover:cursor-pointer hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="removing"
                @click="confirmRemove"
              >
                <Trash2 class="h-3 w-3" />
                {{ removing ? 'Removing…' : 'Remove user' }}
              </button>
            </div>
          </div>

          <dl
            v-if="!isEditing"
            class="grid grid-cols-2 gap-x-6 gap-y-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3 text-sm sm:grid-cols-3"
          >
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">Gender</dt>
              <dd class="text-white capitalize">{{ user.gender ?? '—' }}</dd>
            </div>
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">Phone</dt>
              <dd class="text-white tabular-nums">{{ user.phoneNumber ?? '—' }}</dd>
            </div>
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">Time zone</dt>
              <dd class="text-white">{{ user.timezone ?? 'UTC' }}</dd>
            </div>
          </dl>

          <div
            v-else
            class="flex flex-col gap-4 rounded-md border border-[#ff6f14]/40 bg-[#1f1f1d] px-4 py-4"
          >
            <AvatarUploader v-model="editAvatarUrl" :name="editFullName" :disabled="savingEdit" />

            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-medium text-white" for="edit-user-first">
                  First name
                </label>
                <Input
                  id="edit-user-first"
                  v-model="editFirstName"
                  class="bg-[#2a2a28] border-[#3a3a37] text-white"
                />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-medium text-white" for="edit-user-last">
                  Last name
                </label>
                <Input
                  id="edit-user-last"
                  v-model="editLastName"
                  class="bg-[#2a2a28] border-[#3a3a37] text-white"
                />
              </div>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-medium text-white" for="edit-user-email"> Email </label>
              <Input
                id="edit-user-email"
                v-model="editEmail"
                type="email"
                class="bg-[#2a2a28] border-[#3a3a37] text-white"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-medium text-white" for="edit-user-tz"> Time zone </label>
              <TimezoneSelect id="edit-user-tz" v-model="editTimezone" :disabled="savingEdit" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-medium text-white">Gender</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="opt in ['male', 'female', 'other'] as const"
                  :key="opt"
                  type="button"
                  :class="[
                    'rounded-md border px-3 py-1.5 text-xs font-medium capitalize transition-colors hover:cursor-pointer focus:outline-none focus:ring-2',
                    editGender === opt
                      ? 'border-[#ff6f14] bg-[#ff6f14]/15 text-[#ff7e2a] focus:ring-[#ff6f14]'
                      : 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf] hover:border-[#55554f] hover:text-white focus:ring-[#6a6a63]',
                  ]"
                  @click="editGender = editGender === opt ? '' : opt"
                >
                  {{ opt }}
                </button>
                <button
                  type="button"
                  class="rounded-md border border-[#3a3a37] bg-transparent px-3 py-1.5 text-xs font-medium text-[#a0a09a] transition-colors hover:cursor-pointer hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63] disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="editGender === ''"
                  @click="editGender = ''"
                >
                  Clear
                </button>
              </div>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-medium text-white" for="edit-user-phone">
                Phone number
                <span class="text-[10px] font-normal text-[#a0a09a]">(optional)</span>
              </label>
              <Input
                id="edit-user-phone"
                v-model="editPhoneNumber"
                type="tel"
                placeholder="+31 6 1234 5678"
                class="bg-[#2a2a28] border-[#3a3a37] text-white"
              />
            </div>

            <p v-if="editError" class="text-xs text-rose-300">{{ editError }}</p>

            <div class="flex items-center justify-end gap-2">
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-[#3a3a37] px-3 py-1.5 text-xs font-medium text-[#d4d4cf] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="savingEdit"
                @click="cancelEdit"
              >
                <X class="h-3 w-3" />
                Cancel
              </button>
              <button
                type="button"
                class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="!canSaveEdit || savingEdit"
                @click="saveEdit"
              >
                <Check class="h-3 w-3" />
                {{ savingEdit ? 'Saving…' : 'Save' }}
              </button>
            </div>
          </div>
        </section>

        <section v-if="user.latestPlan" class="flex flex-col gap-4">
          <div class="flex items-start justify-between gap-3">
            <div class="flex flex-col gap-1 min-w-0">
              <h3 class="text-xs font-semibold uppercase text-[#a0a09a]">Latest plan</h3>
              <p class="text-xl font-bold text-white truncate">
                {{ user.latestPlan.planTitle }}
              </p>
            </div>
            <span
              class="shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium"
              :class="planStatusDisplay[user.latestPlan.status].classes"
            >
              {{ planStatusDisplay[user.latestPlan.status].label }}
            </span>
          </div>

          <dl
            class="grid grid-cols-2 gap-x-6 gap-y-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-3 text-sm sm:grid-cols-3"
          >
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">Duration</dt>
              <dd class="text-white">
                {{ formatDuration(user.latestPlan.duration, user.latestPlan.durationType) }}
              </dd>
            </div>
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">Start</dt>
              <dd class="text-white tabular-nums">{{ formatLong(user.latestPlan.startDate) }}</dd>
            </div>
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">End</dt>
              <dd class="text-white tabular-nums">{{ formatLong(user.latestPlan.endDate) }}</dd>
            </div>
            <div class="flex flex-col gap-0.5">
              <dt class="text-xs text-[#a0a09a]">Remaining days</dt>
              <dd class="text-white tabular-nums">
                {{ user.latestPlan.remainingDays ?? '—' }}
              </dd>
            </div>
            <div
              v-if="user.latestPlan.assignedByName || user.latestPlan.assignedByEmail"
              class="flex flex-col gap-0.5 sm:col-span-2"
            >
              <dt class="text-xs text-[#a0a09a]">Assigned by</dt>
              <dd class="text-white">
                {{ user.latestPlan.assignedByName ?? user.latestPlan.assignedByEmail }}
                <a
                  v-if="user.latestPlan.assignedByEmail && user.latestPlan.assignedByName"
                  :href="`mailto:${user.latestPlan.assignedByEmail}`"
                  class="text-[#a0a09a] hover:text-white"
                >
                  ({{ user.latestPlan.assignedByEmail }})
                </a>
              </dd>
            </div>
          </dl>

          <p class="text-xs text-[#a0a09a]">
            Modify, pause, resume, cancel, or restart this plan from the
            <strong class="text-[#d4d4cf]">Active plans</strong> dashboard.
          </p>

          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="flex items-center gap-2 rounded-md border-2 border-[#ff6f14]/60 bg-[#ff6f14]/5 px-3.5 py-2 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:border-[#ff6f14] hover:bg-[#ff6f14]/15 hover:text-[#ff7e2a] focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
              @click="requestAssign"
            >
              <Plus class="h-3.5 w-3.5" />
              Assign new plan
            </button>
          </div>
        </section>

        <section
          v-else
          class="flex flex-col items-center gap-3 rounded-md border border-dashed border-[#3a3a37] px-4 py-6 text-center"
        >
          <p class="text-sm text-[#a0a09a]">This user is not on a plan yet.</p>
          <button
            type="button"
            class="flex items-center gap-2 rounded-md border-2 border-[#ff6f14] bg-[#ff6f14] px-4 py-2 text-sm font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
            @click="requestAssign"
          >
            <Plus class="h-4 w-4" />
            Assign a plan
          </button>
        </section>

        <section class="flex flex-col gap-2">
          <div class="flex items-center gap-2">
            <History class="h-4 w-4 text-[#a0a09a]" />
            <h3 class="text-xs font-semibold uppercase text-[#a0a09a]">History</h3>
            <span v-if="!historyLoading && !historyError" class="text-[10px] text-[#a0a09a]">
              ({{ history.length }})
            </span>
          </div>

          <div
            v-if="historyLoading"
            class="flex items-center justify-center gap-2 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-4 py-4 text-xs text-[#a0a09a]"
          >
            <Loader2 class="h-3.5 w-3.5 animate-spin" />
            Loading history…
          </div>

          <p
            v-else-if="historyError"
            class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
          >
            {{ historyError }}
          </p>

          <p
            v-else-if="history.length === 0"
            class="rounded-md border border-dashed border-[#3a3a37] bg-[#1f1f1d] px-4 py-4 text-center text-xs text-[#a0a09a]"
          >
            No plan history yet.
          </p>

          <ul v-else class="flex flex-col gap-1.5">
            <li
              v-for="row in history"
              :key="row.id"
              class="flex flex-wrap items-center gap-3 rounded-md border border-[#3a3a37] bg-[#1f1f1d] px-3 py-2"
            >
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-white">
                  {{ row.planTitle }}
                </p>
                <p class="text-[11px] text-[#a0a09a] tabular-nums">
                  {{ formatLong(row.startDate) }} – {{ formatLong(row.endDate) }}
                </p>
                <p class="text-[10px] text-[#a0a09a]/80">
                  Assigned {{ formatDateTime(row.assignedAt) }}
                  <template v-if="row.assignedByName || row.assignedByEmail">
                    by {{ row.assignedByName ?? row.assignedByEmail }}
                  </template>
                </p>
              </div>
              <span
                v-if="row.status === 'paused' && row.remainingDays != null"
                class="shrink-0 text-[11px] text-[#a0a09a] tabular-nums"
              >
                {{ row.remainingDays }} day{{ row.remainingDays === 1 ? '' : 's' }} left
              </span>
              <span
                class="shrink-0 rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider"
                :class="planStatusDisplay[row.status].classes"
              >
                {{ planStatusDisplay[row.status].label }}
              </span>
            </li>
          </ul>
        </section>
      </div>
    </DialogContent>
  </Dialog>
</template>
