<script setup lang="ts">
import { NConfigProvider, NMessageProvider, NDialogProvider, NLoadingBarProvider } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
</script>

<template>
  <NConfigProvider :theme="themeStore.naiveTheme" :theme-overrides="themeStore.themeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <NLoadingBarProvider>
          <RouterView />
        </NLoadingBarProvider>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
