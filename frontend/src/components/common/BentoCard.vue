<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<template>
  <div class="bento-card">
    <h3 v-if="title" class="mb-4 text-sm font-semibold text-(--color-text-primary) dark:text-(--color-text-primary-dark)">
      {{ title }}
    </h3>
    <slot />
  </div>
</template>
