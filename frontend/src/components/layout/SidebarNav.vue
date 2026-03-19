<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NTooltip, NAvatar, NDropdown } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import ChangePasswordModal from '@/components/common/ChangePasswordModal.vue'

defineProps<{
  collapsed: boolean
}>()

defineEmits<{
  toggle: []
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const passwordModalVisible = ref(false)

interface NavItem {
  key: string
  label: string
  icon: string
  to: string
  adminOnly?: boolean
}

const allNavItems: NavItem[] = [
  { key: 'aimodel', label: 'AI Models', icon: '🤖', to: '/system/aimodel', adminOnly: true },
  { key: 'users', label: 'Users', icon: '👥', to: '/system/users', adminOnly: true },
  { key: 'workspace', label: 'Workspace', icon: '📁', to: '/system/workspace', adminOnly: true },
  { key: 'mcpserver', label: 'MCP Servers', icon: '🔌', to: '/system/mcpserver', adminOnly: true },
]

const navItems = computed(() => {
  return allNavItems.filter((item) => !item.adminOnly || authStore.isAdmin)
})

const showSystemSection = computed(() => {
  return navItems.value.length > 0
})

const activePath = computed(() => route.path)

function isActive(path: string): boolean {
  return activePath.value.startsWith(path)
}

function navigate(path: string) {
  router.push(path)
}

const themeIcon = computed(() => {
  if (themeStore.mode === 'light') return '☀️'
  if (themeStore.mode === 'dark') return '🌙'
  return '💻'
})

const themeLabel = computed(() => {
  if (themeStore.mode === 'light') return 'Light'
  if (themeStore.mode === 'dark') return 'Dark'
  return 'System'
})

const userDropdownOptions = [
  { label: 'Change Password', key: 'change-password' },
  { label: 'Logout', key: 'logout' },
]

function handleUserAction(key: string) {
  if (key === 'change-password') {
    passwordModalVisible.value = true
  } else if (key === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<template>
  <aside
    class="flex h-screen flex-col border-r transition-all duration-300"
    :class="[
      collapsed ? 'w-16' : 'w-60',
      'bg-(--color-sidebar-bg) dark:bg-(--color-sidebar-bg-dark)',
      'border-(--color-border) dark:border-(--color-border-dark)',
    ]"
  >
    <!-- Logo -->
    <div class="flex h-14 items-center gap-3 border-b border-(--color-border) px-4 dark:border-(--color-border-dark)">
      <div
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-(--color-primary) text-sm font-bold text-white"
      >
        A
      </div>
      <Transition name="fade">
        <span v-if="!collapsed" class="truncate text-sm font-semibold text-(--color-text-primary) dark:text-(--color-text-primary-dark)">
          Agent编排系统
        </span>
      </Transition>
    </div>

    <!-- Section Label -->
    <div v-if="!collapsed && showSystemSection" class="px-4 pt-4 pb-2">
      <span class="text-xs font-medium tracking-wider uppercase text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
        System
      </span>
    </div>

    <!-- Navigation Items -->
    <nav class="flex-1 space-y-1 px-2 py-2">
      <NTooltip
        v-for="item in navItems"
        :key="item.key"
        placement="right"
        :disabled="!collapsed"
      >
        <template #trigger>
          <button
            class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-200"
            :class="[
              isActive(item.to)
                ? 'bg-(--color-primary-light) text-(--color-primary) dark:bg-white/10 dark:text-(--color-primary)'
                : 'text-(--color-text-secondary) hover:bg-gray-100 dark:text-(--color-text-secondary-dark) dark:hover:bg-white/5',
            ]"
            @click="navigate(item.to)"
          >
            <span class="shrink-0 text-base">{{ item.icon }}</span>
            <Transition name="fade">
              <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
            </Transition>
          </button>
        </template>
        {{ item.label }}
      </NTooltip>
    </nav>

    <!-- Bottom Section -->
    <div class="space-y-1 border-t border-(--color-border) p-2 dark:border-(--color-border-dark)">
      <!-- Theme Toggle -->
      <NTooltip placement="right" :disabled="!collapsed">
        <template #trigger>
          <button
            class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-(--color-text-secondary) transition-all duration-200 hover:bg-gray-100 dark:text-(--color-text-secondary-dark) dark:hover:bg-white/5"
            @click="themeStore.toggleMode()"
          >
            <span class="shrink-0 text-base">{{ themeIcon }}</span>
            <Transition name="fade">
              <span v-if="!collapsed" class="truncate">{{ themeLabel }}</span>
            </Transition>
          </button>
        </template>
        Theme: {{ themeLabel }}
      </NTooltip>

      <!-- User -->
      <NDropdown
        :options="userDropdownOptions"
        placement="right-start"
        @select="handleUserAction"
      >
        <button
          class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-(--color-text-secondary) transition-all duration-200 hover:bg-gray-100 dark:text-(--color-text-secondary-dark) dark:hover:bg-white/5"
        >
          <NAvatar :size="24" round class="shrink-0">
            {{ authStore.user?.email?.charAt(0)?.toUpperCase() ?? 'U' }}
          </NAvatar>
          <Transition name="fade">
            <span v-if="!collapsed" class="truncate">
              {{ authStore.user?.email ?? 'User' }}
            </span>
          </Transition>
        </button>
      </NDropdown>
    </div>

    <!-- Change Password Modal -->
    <ChangePasswordModal v-model:visible="passwordModalVisible" />
  </aside>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
