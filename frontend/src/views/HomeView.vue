<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NSpace, NStatistic, NGrid, NGi } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/common/PageHeader.vue'

const authStore = useAuthStore()

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good Morning'
  if (hour < 18) return 'Good Afternoon'
  return 'Good Evening'
})

const userEmail = computed(() => authStore.user?.email ?? '')
</script>

<template>
  <div class="p-6">
    <PageHeader
      :title="`${greeting}, ${userEmail}`"
      description="Welcome to TerraChatBI - Your AI-powered Business Intelligence Platform"
    />

    <NGrid :cols="3" :x-gap="16" :y-gap="16" class="mt-6">
      <NGi>
        <NCard class="bento-card h-full">
          <NSpace vertical align="center" justify="center" class="py-8">
            <div class="text-4xl mb-2">💬</div>
            <NStatistic label="Chat Sessions" value="--" />
          </NSpace>
        </NCard>
      </NGi>
      <NGi>
        <NCard class="bento-card h-full">
          <NSpace vertical align="center" justify="center" class="py-8">
            <div class="text-4xl mb-2">📊</div>
            <NStatistic label="Reports Generated" value="--" />
          </NSpace>
        </NCard>
      </NGi>
      <NGi>
        <NCard class="bento-card h-full">
          <NSpace vertical align="center" justify="center" class="py-8">
            <div class="text-4xl mb-2">🔍</div>
            <NStatistic label="Queries Processed" value="--" />
          </NSpace>
        </NCard>
      </NGi>
    </NGrid>

    <NCard class="bento-card mt-6">
      <template #header>
        <span class="font-semibold">Quick Start</span>
      </template>
      <div class="text-gray-600 dark:text-gray-400">
        <p class="mb-4">
          TerraChatBI helps you analyze and visualize your business data using natural language queries.
        </p>
        <ul class="list-disc list-inside space-y-2">
          <li>Ask questions in plain English about your data</li>
          <li>Generate charts and reports automatically</li>
          <li>Export insights to various formats</li>
        </ul>
      </div>
    </NCard>
  </div>
</template>
