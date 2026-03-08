<script setup lang="ts">
import { NSkeleton } from 'naive-ui'

withDefaults(
  defineProps<{
    rows?: number
    cols?: number
  }>(),
  { rows: 5, cols: 4 },
)
</script>

<template>
  <div class="bento-card">
    <!-- Header row -->
    <div class="mb-4 flex gap-4 border-b border-(--color-border) pb-3 dark:border-(--color-border-dark)">
      <NSkeleton v-for="c in cols" :key="'h' + c" text :style="{ width: c === 1 ? '25%' : '15%', height: '16px' }" />
    </div>
    <!-- Data rows -->
    <div v-for="r in rows" :key="'r' + r" class="flex gap-4 py-3">
      <NSkeleton v-for="c in cols" :key="'d' + r + '-' + c" text :style="{ width: c === 1 ? '25%' : '15%', height: '14px' }" />
    </div>
  </div>
</template>
