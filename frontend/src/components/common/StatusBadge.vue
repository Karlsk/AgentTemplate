<script setup lang="ts">
import { NTag } from 'naive-ui'

defineProps<{
  active: boolean
  activeText?: string
  inactiveText?: string
}>()
</script>

<template>
  <NTag
    :type="active ? 'success' : 'default'"
    size="small"
    round
  >
    {{ active ? (activeText ?? 'Active') : (inactiveText ?? 'Disabled') }}
  </NTag>
</template>
