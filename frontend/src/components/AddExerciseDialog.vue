<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { Check, Plus, Upload, X } from 'lucide-vue-next'
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
import type { BodyCategory, Equipment, Exercise } from '@/types/exercise'

const exercisesStore = useExercisesStore()

const open = ref(false)

const name = ref('')
const videoUrl = ref('')
const instructions = ref('')
const bodyCategory = ref<BodyCategory | null>(null)
const equipment = ref<Equipment | null>(null)
const imageFile = ref<File | null>(null)
const imagePreviewUrl = ref('')
const imageError = ref<string | null>(null)
const isDragging = ref(false)
const submitting = ref(false)
const saveError = ref<string | null>(null)

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

const canSave = computed(
  () => name.value.trim() !== '' && bodyCategory.value !== null && equipment.value !== null,
)

const resetForm = () => {
  void setImage(null)
  name.value = ''
  videoUrl.value = ''
  instructions.value = ''
  bodyCategory.value = null
  equipment.value = null
  isDragging.value = false
  imageError.value = null
  saveError.value = null
  submitting.value = false
}

const handleSave = async () => {
  if (!canSave.value || submitting.value) return
  submitting.value = true
  saveError.value = null
  try {
    const res = await axios.post<Exercise>(`${import.meta.env.VITE_API_URL}/api/exercises`, {
      name: name.value.trim(),
      bodyCategory: bodyCategory.value!,
      equipment: equipment.value!,
      imageUrl: imagePreviewUrl.value || null,
      videoUrl: videoUrl.value.trim() || null,
      instructions: instructions.value.trim() || null,
    })

    exercisesStore.ingestExercise(res.data)
    open.value = false
  } catch (err) {
    console.error('failed to create exercise', err)
    saveError.value = "We couldn't save the exercise. Please try again later."
  } finally {
    submitting.value = false
  }
}

watch(open, (isOpen) => {
  if (!isOpen) resetForm()
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <button
        type="button"
        class="flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-[#ff6f14] transition-colors hover:cursor-pointer hover:bg-[#2a2a28] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#6a6a63]"
        aria-label="Add exercise"
      >
        <Plus class="h-3.5 w-3.5" />
        Add
      </button>
    </DialogTrigger>
    <DialogContent
      class="dark sm:max-w-xl max-h-[90vh] p-0 gap-0 flex flex-col bg-[#181818] text-white border-[#3a3a37] scrollbar-thin"
    >
      <DialogHeader class="border-b border-[#3a3a37] px-6 pt-6 pb-4">
        <DialogTitle class="text-2xl text-white">New exercise</DialogTitle>
      </DialogHeader>

      <div class="flex flex-1 flex-col gap-5 overflow-y-auto px-6 py-5 scrollbar-thin">
        <div class="flex flex-col gap-2">
          <label for="exercise-name" class="text-sm font-medium text-white">Name</label>
          <Input
            id="exercise-name"
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
          <label for="exercise-video" class="text-sm font-medium text-white">
            Video link
            <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
          </label>
          <Input
            id="exercise-video"
            v-model="videoUrl"
            type="url"
            placeholder="https://youtube.com/..."
            class="bg-[#2a2a28] border-[#3a3a37] text-white"
          />
        </div>

        <div class="flex flex-col gap-2">
          <label for="exercise-instructions" class="text-sm font-medium text-white">
            Instructions
            <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
          </label>
          <textarea
            id="exercise-instructions"
            v-model="instructions"
            rows="3"
            placeholder="A short brief on how to perform the exercise..."
            class="rounded-md border border-[#3a3a37] bg-[#2a2a28] px-3 py-2 text-sm text-white placeholder:text-[#a0a09a] outline-none transition-colors focus:border-[#6a6a63]"
          ></textarea>
        </div>

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
      </div>

      <div class="flex flex-col gap-2 border-t border-[#3a3a37] bg-[#181818] px-6 py-3">
        <p
          v-if="saveError"
          class="rounded-md border border-rose-500/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-300"
        >
          {{ saveError }}
        </p>
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
            {{ submitting ? 'Saving…' : 'Save exercise' }}
          </button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
