<script setup lang="ts">
import { computed } from 'vue'
import {
  NativeSelect,
  NativeSelectOption,
  NativeSelectOptGroup,
} from '@/components/ui/native-select'

const value = defineModel<string>({ required: true })

defineProps<{
  id?: string
  disabled?: boolean
}>()

const detectedTz = (() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
})()

const allTimezones = computed<string[]>(() => {
  const intlAny = Intl as typeof Intl & {
    supportedValuesOf?: (key: string) => string[]
  }
  if (typeof intlAny.supportedValuesOf === 'function') {
    try {
      return intlAny.supportedValuesOf('timeZone').slice().sort()
    } catch {}
  }
  return ['UTC']
})

const customEntry = computed(() =>
  value.value && !allTimezones.value.includes(value.value) ? value.value : null,
)
</script>

<template>
  <NativeSelect
    :id="id"
    v-model="value"
    :disabled="disabled"
    class="w-full bg-[#2a2a28] border-[#3a3a37] text-white"
  >
    <NativeSelectOptGroup v-if="detectedTz" label="Detected">
      <NativeSelectOption :value="detectedTz">{{ detectedTz }}</NativeSelectOption>
    </NativeSelectOptGroup>
    <NativeSelectOptGroup v-if="customEntry" label="Current">
      <NativeSelectOption :value="customEntry">{{ customEntry }}</NativeSelectOption>
    </NativeSelectOptGroup>
    <NativeSelectOptGroup label="All timezones">
      <NativeSelectOption v-for="tz in allTimezones" :key="tz" :value="tz">
        {{ tz }}
      </NativeSelectOption>
    </NativeSelectOptGroup>
  </NativeSelect>
</template>
