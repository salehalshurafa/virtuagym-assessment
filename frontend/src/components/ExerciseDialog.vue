<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, ExternalLink, Pencil, Trash2, Upload, X } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useExercisesStore } from '@/stores/exercises'
import { fileToDataUrl } from '@/lib/images'
import { BODY_CATEGORY_LABELS, EQUIPMENT_LABELS } from '@/types/exercise'
import type { Exercise, BodyCategory, Equipment } from '@/types/exercise'

const props = defineProps<{ exercise: Exercise }>()

const exercisesStore = useExercisesStore()

const open = ref(false)
const mode = ref<'view' | 'edit'>('view')
const confirmingDelete = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const saveError = ref<string | null>(null)
const deleteError = ref<string | null>(null)

const name = ref('')
const videoUrl = ref('')
const instructions = ref('')
const bodyCategory = ref<BodyCategory | null>(null)
const equipment = ref<Equipment | null>(null)
const imageFile = ref<File | null>(null)
const imagePreviewUrl = ref('')
const imageError = ref<string | null>(null)
const isDragging = ref(false)

const bodyCategories: { value: BodyCategory; label: string }[] = [
  { value: 'chest', label: 'Chest' },
  { value: 'back', label: 'Back' },
  { value: 'legs', label: 'Legs' },
  { value: 'shoulders', label: 'Shoulders' },
  { value: 'arms', label: 'Arms' },
  { value: 'core', label: 'Core' },
  { value: 'cardio', label: 'Cardio' },
]

const equipmentOptions: { value: Equipment; label: string }[] = [
  { value: 'bar', label: 'Bar' },
  { value: 'dumbbell', label: 'Dumbbell' },
  { value: 'machine', label: 'Machine' },
  { value: 'cable', label: 'Cable' },
  { value: 'free-weight', label: 'Free Weight' },
]

const setImage = async (file: File | null) => {
  imageError.value = null
  if (file === null) {
    imageFile.value = null
    imagePreviewUrl.value = ''
    return
  }
  try {
    const dataUrl = await fileToDataUrl(file)
    imageFile.value = file
    imagePreviewUrl.value = dataUrl
  } catch (err) {
    imageError.value = (err as Error).message
    imageFile.value = null
    imagePreviewUrl.value = ''
  }
}

const onFileInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) setImage(file)
  target.value = ''
}

const onDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) setImage(file)
}

const onDragOver = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = true
}

const onDragLeave = () => {
  isDragging.value = false
}

const loadFromExercise = () => {
  imageFile.value = null
  imagePreviewUrl.value = props.exercise.imageUrl ?? ''
  imageError.value = null
  name.value = props.exercise.name
  videoUrl.value = props.exercise.videoUrl ?? ''
  instructions.value = props.exercise.instructions ?? ''
  bodyCategory.value = props.exercise.bodyCategory
  equipment.value = props.exercise.equipment
  isDragging.value = false
}

const resetForm = () => {
  imageFile.value = null
  imagePreviewUrl.value = ''
  imageError.value = null
  name.value = ''
  videoUrl.value = ''
  instructions.value = ''
  bodyCategory.value = null
  equipment.value = null
  isDragging.value = false
}

const isValid = computed(
  () => name.value.trim() !== '' && bodyCategory.value !== null && equipment.value !== null,
)

const changesMade = computed(() => {
  const ex = props.exercise
  if (name.value.trim() !== ex.name) return true
  if ((videoUrl.value.trim() || undefined) !== ex.videoUrl) return true
  if ((instructions.value.trim() || undefined) !== ex.instructions) return true
  if (bodyCategory.value !== ex.bodyCategory) return true
  if (equipment.value !== ex.equipment) return true
  if ((imagePreviewUrl.value || undefined) !== ex.imageUrl) return true
  return false
})

const canSave = computed(() => isValid.value && changesMade.value)

const enterEdit = () => {
  loadFromExercise()
  mode.value = 'edit'
}

const exitEdit = () => {
  mode.value = 'view'
}

const handleSave = async () => {
  if (!canSave.value || submitting.value) return
  submitting.value = true
  saveError.value = null
  try {
    const res = await axios.patch<Exercise>(
      `${import.meta.env.VITE_API_URL}/api/exercises/${props.exercise.id}`,
      {
        name: name.value.trim(),
        bodyCategory: bodyCategory.value!,
        equipment: equipment.value!,
        imageUrl: imagePreviewUrl.value || null,
        videoUrl: videoUrl.value.trim() || null,
        instructions: instructions.value.trim() || null,
      },
    )
    exercisesStore.ingestExercise(res.data)
    imageFile.value = null
    open.value = false
  } catch (err) {
    console.error('failed to update exercise', err)
    saveError.value = "We couldn't save your changes. Please try again later."
  } finally {
    submitting.value = false
  }
}

const handleDelete = async () => {
  if (deleting.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await axios.delete(`${import.meta.env.VITE_API_URL}/api/exercises/${props.exercise.id}`)
    exercisesStore.removeExercise(props.exercise.id)
    open.value = false
  } catch (err) {
    console.error('failed to delete exercise', err)
    deleteError.value = "We couldn't delete this exercise. Please try again later."
  } finally {
    deleting.value = false
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    mode.value = 'view'
    confirmingDelete.value = false
    saveError.value = null
    deleteError.value = null
  } else {
    resetForm()
    mode.value = 'view'
    confirmingDelete.value = false
    submitting.value = false
    deleting.value = false
    saveError.value = null
    deleteError.value = null
  }
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <button
        type="button"
        class="group flex w-full items-center gap-3 rounded-lg border border-[#3a3a37] bg-[#2a2a28]/60 px-4 py-3 text-left transition-colors hover:cursor-pointer hover:border-[#55554f] hover:bg-[#2a2a28] focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
        :aria-label="`Open ${exercise.name}`"
      >
        <span class="flex-1 truncate text-sm font-medium text-white">
          {{ exercise.name }}
        </span>
        <span
          class="shrink-0 rounded-full border border-[#ff6f14] bg-[#1f1f1d] px-2.5 py-0.5 text-xs font-medium text-[#ff6f14]"
        >
          {{ BODY_CATEGORY_LABELS[exercise.bodyCategory] }}
        </span>
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-xl max-h-[90vh] p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37] overflow-hidden"
    >
      <template v-if="mode === 'view'">
        <div class="relative h-44 w-full shrink-0 overflow-hidden">
          <img
            v-if="exercise.imageUrl"
            :src="exercise.imageUrl"
            :alt="`${exercise.name} cover`"
            class="h-full w-full object-cover"
          />
          <div
            v-else
            class="h-full w-full bg-gradient-to-br from-[#2a2a28] via-[#1f1f1d] to-[#0f0f0e]"
          />
          <div
            class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/40 to-transparent"
          />
          <div class="absolute bottom-4 left-6 right-12">
            <DialogTitle class="text-3xl font-bold text-white drop-shadow-lg">
              {{ exercise.name }}
            </DialogTitle>
            <p class="mt-1 text-xs text-white/80">
              {{ BODY_CATEGORY_LABELS[exercise.bodyCategory] }} ·
              {{ EQUIPMENT_LABELS[exercise.equipment] }}
            </p>
          </div>
        </div>

        <div class="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5 scrollbar-thin">
          <section class="flex flex-col gap-3">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Overview
            </h3>
            <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div class="flex flex-col gap-0.5">
                <dt class="text-xs text-[#a0a09a]">Body category</dt>
                <dd class="text-white">{{ BODY_CATEGORY_LABELS[exercise.bodyCategory] }}</dd>
              </div>
              <div class="flex flex-col gap-0.5">
                <dt class="text-xs text-[#a0a09a]">Equipment</dt>
                <dd class="text-white">{{ EQUIPMENT_LABELS[exercise.equipment] }}</dd>
              </div>
              <div class="flex flex-col gap-0.5">
                <dt class="text-xs text-[#a0a09a]">Used in plans</dt>
                <dd class="text-white tabular-nums">{{ exercise.usageCount.toLocaleString() }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="exercise.instructions" class="flex flex-col gap-3">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Instructions
            </h3>
            <p class="whitespace-pre-line text-sm text-[#d4d4cf]">{{ exercise.instructions }}</p>
          </section>

          <section v-if="exercise.videoUrl" class="flex flex-col gap-3">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Video
            </h3>
            <a
              :href="exercise.videoUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-[#ff6f14] hover:underline"
            >
              <ExternalLink class="h-3.5 w-3.5" />
              <span class="truncate">{{ exercise.videoUrl }}</span>
            </a>
          </section>
        </div>

        <div
          class="flex items-center justify-between gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3"
        >
          <template v-if="!confirmingDelete">
            <button
              type="button"
              class="flex items-center gap-1 rounded-md border border-red-600/60 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:cursor-pointer hover:bg-red-600/10 hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-600"
              @click="confirmingDelete = true"
            >
              <Trash2 class="h-3.5 w-3.5" />
              Delete
            </button>
            <button
              type="button"
              class="flex items-center gap-1 rounded-md border border-[#ff6f14] bg-[#ff6f14] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:cursor-pointer hover:bg-[#ff7e2a] focus:outline-none focus:ring-2 focus:ring-[#ff6f14]/50"
              @click="enterEdit"
            >
              <Pencil class="h-3.5 w-3.5" />
              Edit
            </button>
          </template>
          <template v-else>
            <span class="flex items-center gap-1.5 text-xs text-red-300">
              <Trash2 class="h-3.5 w-3.5" />
              Permanently delete this exercise?
            </span>
            <div class="flex items-center gap-2">
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
          </template>
          <p
            v-if="deleteError"
            class="basis-full rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
          >
            {{ deleteError }}
          </p>
        </div>
      </template>

      <template v-else>
        <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-4">
          <DialogTitle class="text-2xl text-white">Edit exercise</DialogTitle>
        </DialogHeader>

        <div class="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5 scrollbar-thin">
          <section class="flex flex-col gap-4">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Details
            </h3>

            <div class="flex flex-col gap-2">
              <label for="exercise-edit-name" class="text-sm font-medium text-white">Name</label>
              <Input
                id="exercise-edit-name"
                v-model="name"
                placeholder="e.g. Incline Dumbbell Press"
                class="bg-[#2a2a28] border-[#3a3a37] text-white"
              />
            </div>

            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-white">
                Cover image
                <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
              </label>
              <div v-if="imagePreviewUrl" class="relative">
                <img
                  :src="imagePreviewUrl"
                  alt="Exercise cover preview"
                  class="h-32 w-full rounded-md border border-[#3a3a37] object-cover"
                />
                <button
                  type="button"
                  class="absolute top-2 right-2 grid h-7 w-7 place-items-center rounded-full bg-black/60 text-white transition-colors hover:cursor-pointer hover:bg-black/80"
                  aria-label="Remove image"
                  @click="setImage(null)"
                >
                  <X class="h-3.5 w-3.5" />
                </button>
              </div>
              <label
                v-else
                :class="[
                  'flex h-32 cursor-pointer flex-col items-center justify-center gap-1.5 rounded-md border-2 border-dashed transition-colors',
                  isDragging
                    ? 'border-[#ff6f14] bg-[#ff6f14]/5'
                    : 'border-[#3a3a37] bg-[#2a2a28]/40 hover:border-[#55554f] hover:bg-[#2a2a28]',
                ]"
                @dragover="onDragOver"
                @dragleave="onDragLeave"
                @drop="onDrop"
              >
                <Upload class="h-5 w-5 text-[#a0a09a]" />
                <span class="text-sm text-[#d4d4cf]">
                  <span class="font-medium text-white">Click to upload</span>
                  or drag and drop
                </span>
                <span class="text-xs text-[#a0a09a]">PNG, JPG, or WebP · max 2 MB</span>
                <input type="file" accept="image/*" class="hidden" @change="onFileInput" />
              </label>
              <p v-if="imageError" class="text-xs text-rose-300">{{ imageError }}</p>
            </div>

            <div class="flex flex-col gap-2">
              <label for="exercise-edit-video" class="text-sm font-medium text-white">
                Video link
                <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
              </label>
              <Input
                id="exercise-edit-video"
                v-model="videoUrl"
                type="url"
                placeholder="https://youtube.com/..."
                class="bg-[#2a2a28] border-[#3a3a37] text-white"
              />
            </div>

            <div class="flex flex-col gap-2">
              <label for="exercise-edit-instructions" class="text-sm font-medium text-white">
                Instructions
                <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
              </label>
              <textarea
                id="exercise-edit-instructions"
                v-model="instructions"
                rows="3"
                placeholder="A short brief on how to perform the exercise..."
                class="rounded-md border border-[#3a3a37] bg-[#2a2a28] px-3 py-2 text-sm text-white placeholder:text-[#a0a09a] outline-none transition-colors focus:border-[#6a6a63]"
              ></textarea>
            </div>
          </section>

          <section class="flex flex-col gap-4">
            <h3
              class="border-b border-[#3a3a37] pb-2 text-xs font-semibold uppercase text-[#a0a09a]"
            >
              Classification
            </h3>

            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-white">Body category</label>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="cat in bodyCategories"
                  :key="cat.value"
                  type="button"
                  :class="[
                    'rounded-md border px-3 py-1.5 text-sm font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#6a6a63]',
                    bodyCategory === cat.value
                      ? 'border-[#ff6f14] bg-[#ff6f14] text-white'
                      : 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf] hover:border-[#55554f]',
                  ]"
                  @click="bodyCategory = cat.value"
                >
                  {{ cat.label }}
                </button>
              </div>
            </div>

            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-white">Equipment</label>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="eq in equipmentOptions"
                  :key="eq.value"
                  type="button"
                  :class="[
                    'rounded-md border px-3 py-1.5 text-sm font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#6a6a63]',
                    equipment === eq.value
                      ? 'border-[#ff6f14] bg-[#ff6f14] text-white'
                      : 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf] hover:border-[#55554f]',
                  ]"
                  @click="equipment = eq.value"
                >
                  {{ eq.label }}
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
              @click="exitEdit"
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
              {{ submitting ? 'Saving…' : 'Save changes' }}
            </button>
          </div>
        </div>
      </template>
    </DialogContent>
  </Dialog>
</template>
