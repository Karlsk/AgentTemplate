<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-(--color-text-primary) dark:text-(--color-text-primary-dark)">
        {{ title }}
      </h1>
      <p v-if="subtitle" class="mt-1 text-sm text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
        {{ subtitle }}
      </p>
    </div>
    <div class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
