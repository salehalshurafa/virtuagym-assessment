<script setup lang="ts">
import { computed, ref } from 'vue'
import { Upload, X } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { usePlanForm } from './usePlanForm'

const form = usePlanForm()
const isDragging = ref(false)

const durationModel = computed<number | undefined>({
  get: () => form.duration.value ?? undefined,
  set: (v) => {
    form.duration.value = v ?? null
  },
})

const onFileInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) form.setImageFile(file)
  target.value = ''
}

const onDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) form.setImageFile(file)
}

const onDragOver = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = true
}

const onDragLeave = () => {
  isDragging.value = false
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-2">
      <label for="plan-name" class="text-sm font-medium text-white">Name</label>
      <Input
        id="plan-name"
        v-model="form.name.value"
        placeholder="e.g. Full-Body Strength Starter"
        class="bg-[#2a2a28] border-[#3a3a37] text-white"
      />
    </div>

    <div class="flex flex-col gap-2">
      <label class="text-sm font-medium text-white">
        Cover image
        <span class="text-xs font-normal text-[#a0a09a]">(optional)</span>
      </label>
      <div v-if="form.imagePreviewUrl.value" class="relative">
        <img
          :src="form.imagePreviewUrl.value"
          alt="Plan cover preview"
          class="h-40 w-full rounded-md border border-[#3a3a37] object-cover"
        />
        <button
          type="button"
          class="absolute top-2 right-2 grid h-7 w-7 place-items-center rounded-full bg-black/60 text-white transition-colors hover:cursor-pointer hover:bg-black/80"
          aria-label="Remove image"
          @click="form.setImageFile(null)"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>
      <label
        v-else
        :class="[
          'flex h-40 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed transition-colors',
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
      <p v-if="form.imageError.value" class="text-xs text-rose-300">
        {{ form.imageError.value }}
      </p>
    </div>

    <div class="flex flex-col gap-2">
      <label class="text-sm font-medium text-white">Duration</label>
      <div class="flex gap-2">
        <Input
          v-model.number="durationModel"
          type="number"
          min="1"
          placeholder="8"
          aria-label="Duration"
          class="bg-[#2a2a28] border-[#3a3a37] text-white flex-1"
        />
        <NativeSelect
          v-model="form.durationType.value"
          aria-label="Duration type"
          class="w-36 bg-[#2a2a28] border-[#3a3a37] text-white"
        >
          <NativeSelectOption value="days">Day(s)</NativeSelectOption>
          <NativeSelectOption value="weeks">Week(s)</NativeSelectOption>
          <NativeSelectOption value="months">Month(s)</NativeSelectOption>
          <NativeSelectOption value="years">Year(s)</NativeSelectOption>
        </NativeSelect>
      </div>
    </div>

    <div v-if="form.showWeeklyDaysQuestion.value" class="flex flex-col gap-2">
      <label class="text-sm font-medium text-white">Workout days per week</label>
      <div class="grid grid-cols-7 gap-1">
        <button
          v-for="n in 7"
          :key="n"
          type="button"
          :class="[
            'rounded-md border px-2 py-1.5 text-sm font-medium transition-colors hover:cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#6a6a63]',
            form.workoutDaysPerWeek.value === n
              ? 'border-[#ff6f14] bg-[#ff6f14] text-white'
              : 'border-[#3a3a37] bg-[#2a2a28] text-[#d4d4cf] hover:border-[#55554f]',
          ]"
          @click="form.workoutDaysPerWeek.value = n"
        >
          {{ n }}
        </button>
      </div>
    </div>
  </div>
</template>
