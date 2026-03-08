<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { useBreakpoints } from '@vueuse/core'
import { onKeyStroke } from '@vueuse/core'
import SidebarNav from './SidebarNav.vue'
import TopBar from './TopBar.vue'
import CommandPalette from '@/components/search/CommandPalette.vue'
import { useCommandPalette } from '@/composables/useCommandPalette'

const breakpoints = useBreakpoints({ desktop: 1280 })
const isDesktop = breakpoints.greaterOrEqual('desktop')

const collapsed = ref(
  localStorage.getItem('sidebarCollapsed') === 'true',
)

watchEffect(() => {
  if (!isDesktop.value) {
    collapsed.value = true
  }
})

function toggleSidebar() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebarCollapsed', String(collapsed.value))
}

const { toggle: toggleCommandPalette } = useCommandPalette()

onKeyStroke('k', (e) => {
  if (e.metaKey || e.ctrlKey) {
    e.preventDefault()
    toggleCommandPalette()
  }
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-(--color-page-bg) dark:bg-(--color-page-bg-dark)">
    <SidebarNav :collapsed="collapsed" @toggle="toggleSidebar" />
    <div class="flex flex-1 flex-col overflow-hidden">
      <TopBar :collapsed="collapsed" @toggle-sidebar="toggleSidebar" />
      <main class="flex-1 overflow-auto p-6">
        <RouterView />
      </main>
    </div>
    <CommandPalette />
  </div>
</template>
