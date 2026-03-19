<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NSpace, NStatistic, NGrid, NGi } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/common/PageHeader.vue'

const authStore = useAuthStore()

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const userEmail = computed(() => authStore.user?.email ?? '')
</script>

<template>
  <div class="p-6">
    <PageHeader
      :title="`${greeting}, ${userEmail}`"
      description="欢迎使用Agent编排系统 - 智能AI Agent编排平台"
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
            <NStatistic label="处理查询" value="--" />
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
          Agent编排系统帮助您通过智能Agent工作流编排，实现业务数据的分析与可视化。
        </p>
        <ul class="list-disc list-inside space-y-2">
          <li>使用自然语言查询您的业务数据</li>
          <li>自动生成图表和报告</li>
          <li>将洞察导出为多种格式</li>
        </ul>
      </div>
    </NCard>
  </div>
</template>
