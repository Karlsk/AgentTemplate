<script setup lang="ts">
import { NSkeleton } from 'naive-ui'

withDefaults(
  defineProps<{
    count?: number
  }>(),
  { count: 6 },
)
</script>

<template>
  <div class="bento-grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
    <div v-for="i in count" :key="i" class="bento-card">
      <NSkeleton text style="width: 60%; height: 18px" class="mb-3" />
      <NSkeleton text :repeat="2" style="width: 100%; height: 14px" class="mb-2" />
      <div class="mt-4 flex gap-2">
        <NSkeleton text style="width: 60px; height: 28px; border-radius: 8px" />
        <NSkeleton text style="width: 60px; height: 28px; border-radius: 8px" />
      </div>
    </div>
  </div>
</template>
