<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { NButton } from 'naive-ui'
import { useCommandPalette } from '@/composables/useCommandPalette'

defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  toggleSidebar: []
}>()

const route = useRoute()
const { open: openSearch } = useCommandPalette()

const pageTitle = computed(() => (route.meta.title as string) ?? '')

const isMac = navigator.platform.toUpperCase().includes('MAC')
const shortcutHint = isMac ? '⌘K' : 'Ctrl+K'
</script>

<template>
  <header
    class="flex h-14 shrink-0 items-center justify-between border-b px-4"
    :class="[
      'bg-(--color-card-bg)/80 dark:bg-(--color-card-bg-dark)/80',
      'border-(--color-border) dark:border-(--color-border-dark)',
      'backdrop-blur-sm',
    ]"
  >
    <!-- Left -->
    <div class="flex items-center gap-3">
      <button
        class="flex h-8 w-8 items-center justify-center rounded-lg text-(--color-text-secondary) transition-colors hover:bg-gray-100 dark:text-(--color-text-secondary-dark) dark:hover:bg-white/5"
        @click="emit('toggleSidebar')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <h1 class="text-base font-semibold text-(--color-text-primary) dark:text-(--color-text-primary-dark)">
        {{ pageTitle }}
      </h1>
    </div>

    <!-- Right -->
    <div class="flex items-center gap-2">
      <NButton
        secondary
        size="small"
        class="!rounded-lg"
        @click="openSearch"
      >
        <template #icon>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </template>
        <span class="mr-2 hidden text-xs sm:inline">Search</span>
        <kbd class="hidden rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 sm:inline dark:bg-white/10 dark:text-gray-400">
          {{ shortcutHint }}
        </kbd>
      </NButton>
    </div>
  </header>
</template>
