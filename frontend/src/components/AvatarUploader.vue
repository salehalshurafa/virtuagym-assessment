<script setup lang="ts">
import { computed, ref } from 'vue'
import { Upload, X } from 'lucide-vue-next'
import { fileToDataUrl } from '@/lib/images'

const value = defineModel<string | null>({ required: true })

const props = withDefaults(
  defineProps<{
    name: string
    size?: number
    disabled?: boolean
  }>(),
  { size: 80, disabled: false },
)

const error = ref<string | null>(null)
const isDragging = ref(false)

const initials = computed(() => {
  const parts = props.name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  const first = parts[0]!.charAt(0)
  const last = parts.length > 1 ? parts[parts.length - 1]!.charAt(0) : ''
  return (first + last).toUpperCase()
})

const setImage = async (file: File | null) => {
  error.value = null
  if (file === null) {
    value.value = null
    return
  }
  try {
    value.value = await fileToDataUrl(file)
  } catch (err) {
    error.value = (err as Error).message
  }
}

const onFileInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) void setImage(file)
  target.value = ''
}

const onDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false
  if (props.disabled) return
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) void setImage(file)
}

const onDragOver = (e: DragEvent) => {
  e.preventDefault()
  if (!props.disabled) isDragging.value = true
}

const onDragLeave = () => {
  isDragging.value = false
}

const remove = () => {
  if (props.disabled) return
  void setImage(null)
}

const sizeStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))

const fontSize = computed(() => `${Math.round(props.size * 0.32)}px`)
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <label
      :class="[
        'group relative grid place-items-center rounded-full border-2 transition-colors',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-[#55554f]',
        isDragging
          ? 'border-[#ff6f14] bg-[#ff6f14]/10'
          : value
            ? 'border-[#3a3a37]'
            : 'border-dashed border-[#3a3a37] bg-[#2a2a28]/40',
      ]"
      :style="sizeStyle"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <img
        v-if="value"
        :src="value"
        :alt="`${name} avatar`"
        class="h-full w-full rounded-full object-cover"
      />
      <span
        v-else
        class="font-semibold text-white"
        :style="{ fontSize: fontSize }"
        aria-hidden="true"
      >
        {{ initials }}
      </span>

      <span
        v-if="!value"
        class="pointer-events-none absolute inset-0 grid place-items-center rounded-full bg-black/0 opacity-0 transition-opacity group-hover:bg-black/30 group-hover:opacity-100"
      >
        <Upload class="h-5 w-5 text-white" />
      </span>
      <span
        v-else
        class="pointer-events-none absolute inset-0 grid place-items-center rounded-full bg-black/0 opacity-0 transition-opacity group-hover:bg-black/40 group-hover:opacity-100"
      >
        <Upload class="h-4 w-4 text-white" />
      </span>

      <input
        type="file"
        accept="image/*"
        class="hidden"
        :disabled="disabled"
        @change="onFileInput"
      />
    </label>

    <div class="flex flex-col items-center gap-0.5">
      <p class="text-xs text-[#a0a09a]">
        <template v-if="value">Click or drop to replace</template>
        <template v-else>Click or drop to upload · max 2 MB</template>
      </p>
      <button
        v-if="value"
        type="button"
        class="flex items-center gap-1 text-[11px] text-[#a0a09a] transition-colors hover:cursor-pointer hover:text-rose-300 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="disabled"
        @click="remove"
      >
        <X class="h-3 w-3" />
        Remove
      </button>
    </div>
    <p v-if="error" class="text-xs text-rose-300">{{ error }}</p>
  </div>
</template>
