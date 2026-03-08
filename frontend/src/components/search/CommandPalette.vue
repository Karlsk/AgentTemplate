<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NModal, NInput } from 'naive-ui'
import { useCommandPalette } from '@/composables/useCommandPalette'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const { isOpen, close } = useCommandPalette()

const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref<InstanceType<typeof NInput> | null>(null)

interface Command {
  id: string
  label: string
  description: string
  icon: string
  keywords: string[]
  action: () => void
}

const commands: Command[] = [
  {
    id: 'nav-aimodel',
    label: 'AI Models',
    description: 'Manage AI model configurations',
    icon: '🤖',
    keywords: ['ai', 'model', 'llm', 'openai'],
    action: () => router.push('/system/aimodel'),
  },
  {
    id: 'nav-users',
    label: 'Users',
    description: 'User management',
    icon: '👥',
    keywords: ['user', 'people', 'account'],
    action: () => router.push('/system/users'),
  },
  {
    id: 'nav-workspace',
    label: 'Workspace',
    description: 'Workspace management',
    icon: '📁',
    keywords: ['workspace', 'org', 'team'],
    action: () => router.push('/system/workspace'),
  },
  {
    id: 'toggle-theme',
    label: 'Toggle Theme',
    description: `Current: ${themeStore.mode}`,
    icon: '🎨',
    keywords: ['theme', 'dark', 'light', 'mode'],
    action: () => themeStore.toggleMode(),
  },
  {
    id: 'logout',
    label: 'Logout',
    description: 'Sign out of your account',
    icon: '🚪',
    keywords: ['logout', 'signout', 'exit'],
    action: () => {
      authStore.logout()
      router.push('/login')
    },
  },
]

const filteredCommands = computed(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return commands
  return commands.filter((cmd) => {
    return (
      cmd.label.toLowerCase().includes(q) ||
      cmd.description.toLowerCase().includes(q) ||
      cmd.keywords.some((kw) => kw.includes(q))
    )
  })
})

function executeCommand(cmd: Command) {
  close()
  query.value = ''
  selectedIndex.value = 0
  cmd.action()
}

function handleKeydown(e: KeyboardEvent) {
  const cmds = filteredCommands.value
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % cmds.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value - 1 + cmds.length) % cmds.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const cmd = cmds[selectedIndex.value]
    if (cmd) executeCommand(cmd)
  }
}

watch(isOpen, (open) => {
  if (open) {
    query.value = ''
    selectedIndex.value = 0
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

watch(query, () => {
  selectedIndex.value = 0
})
</script>

<template>
  <NModal
    v-model:show="isOpen"
    :mask-closable="true"
    :auto-focus="false"
    transform-origin="center"
    class="!w-[560px] !max-w-[90vw]"
  >
    <div
      class="overflow-hidden rounded-2xl border border-(--color-border) bg-(--color-card-bg) shadow-xl dark:border-(--color-border-dark) dark:bg-(--color-card-bg-dark)"
      @keydown="handleKeydown"
    >
      <!-- Search Input -->
      <div class="border-b border-(--color-border) p-4 dark:border-(--color-border-dark)">
        <NInput
          ref="inputRef"
          v-model:value="query"
          placeholder="Search pages, actions..."
          size="large"
          clearable
        >
          <template #prefix>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-(--color-text-secondary)">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </template>
        </NInput>
      </div>

      <!-- Results -->
      <div class="max-h-[320px] overflow-y-auto p-2">
        <div v-if="filteredCommands.length === 0" class="px-4 py-8 text-center text-sm text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
          No results found
        </div>
        <button
          v-for="(cmd, index) in filteredCommands"
          :key="cmd.id"
          class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors duration-100"
          :class="[
            index === selectedIndex
              ? 'bg-(--color-primary-light) dark:bg-white/10'
              : 'hover:bg-gray-50 dark:hover:bg-white/5',
          ]"
          @click="executeCommand(cmd)"
          @mouseenter="selectedIndex = index"
        >
          <span class="shrink-0 text-lg">{{ cmd.icon }}</span>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-medium text-(--color-text-primary) dark:text-(--color-text-primary-dark)">
              {{ cmd.label }}
            </div>
            <div class="truncate text-xs text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
              {{ cmd.description }}
            </div>
          </div>
          <kbd
            v-if="index === selectedIndex"
            class="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-white/10 dark:text-gray-400"
          >
            ↵
          </kbd>
        </button>
      </div>

      <!-- Footer -->
      <div class="flex items-center gap-4 border-t border-(--color-border) px-4 py-2 text-[11px] text-(--color-text-secondary) dark:border-(--color-border-dark) dark:text-(--color-text-secondary-dark)">
        <span><kbd class="rounded bg-gray-100 px-1 py-0.5 dark:bg-white/10">↑↓</kbd> Navigate</span>
        <span><kbd class="rounded bg-gray-100 px-1 py-0.5 dark:bg-white/10">↵</kbd> Select</span>
        <span><kbd class="rounded bg-gray-100 px-1 py-0.5 dark:bg-white/10">Esc</kbd> Close</span>
      </div>
    </div>
  </NModal>
</template>
