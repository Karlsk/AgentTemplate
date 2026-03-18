<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  NModal,
  NDataTable,
  NPagination,
  NText,
  NSpin,
  NEmpty,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import ragService from '@/services/rag.service'
import type { ChunkPreviewItem } from '@/types/rag'

const props = defineProps<{
  visible: boolean
  kbId: number
  docId: number | null
  docName: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const message = useMessage()
const loading = ref(false)
const chunks = ref<ChunkPreviewItem[]>([])
const totalChunks = ref(0)
const currentPage = ref(1)
const pageSize = 20

async function fetchChunks() {
  if (!props.docId) return
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize
    const res = await ragService.getDocumentChunks(props.kbId, props.docId, offset, pageSize)
    chunks.value = res.chunks
    totalChunks.value = res.total_chunks
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load chunks')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.docId) {
      currentPage.value = 1
      fetchChunks()
    }
  },
)

function handlePageChange(page: number) {
  currentPage.value = page
  fetchChunks()
}

function handleClose() {
  emit('update:visible', false)
}

const columns: DataTableColumns<ChunkPreviewItem> = [
  {
    title: '#',
    key: 'chunk_index',
    width: 60,
    align: 'center',
  },
  {
    title: 'Content',
    key: 'content',
    ellipsis: { tooltip: { width: 500 } },
  },
  {
    title: 'Characters',
    key: 'char_count',
    width: 100,
    align: 'center',
  },
]
</script>

<template>
  <NModal
    :show="visible"
    :mask-closable="true"
    preset="card"
    :title="`Chunk Preview - ${docName}`"
    class="!w-[800px] !max-w-[90vw]"
    :bordered="false"
    :segmented="{ content: true }"
    @update:show="handleClose"
  >
    <div v-if="loading" class="flex items-center justify-center py-8">
      <NSpin size="large" />
    </div>

    <template v-else>
      <div class="mb-3">
        <NText depth="3" class="text-sm">
          Total chunks: {{ totalChunks }}
        </NText>
      </div>

      <NEmpty v-if="chunks.length === 0" description="No chunks found" />

      <template v-else>
        <NDataTable
          :columns="columns"
          :data="chunks"
          :bordered="false"
          :single-line="false"
          striped
          size="small"
          :max-height="400"
        />

        <div v-if="totalChunks > pageSize" class="mt-4 flex justify-end">
          <NPagination
            :page="currentPage"
            :page-count="Math.ceil(totalChunks / pageSize)"
            @update:page="handlePageChange"
          />
        </div>
      </template>
    </template>
  </NModal>
</template>
