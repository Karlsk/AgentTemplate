<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NDataTable,
  NTag,
  NSpace,
  NUpload,
  NAlert,
  NSelect,
  NInputNumber,
  NInput,
  NCollapse,
  NCollapseItem,
  NProgress,
  useMessage,
  useDialog,
} from 'naive-ui'
import type { DataTableColumns, UploadFileInfo } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import ChunkPreviewModal from './ChunkPreviewModal.vue'
import ragService from '@/services/rag.service'
import type { KnowledgeBase, RagDocumentListItem, DocumentUploadOptions } from '@/types/rag'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const kbId = computed(() => Number(route.params.kbId))
const kb = ref<KnowledgeBase | null>(null)
const documents = ref<RagDocumentListItem[]>([])
const loading = ref(true)
const uploading = ref(false)

// Upload advanced settings
const uploadOptions = ref<DocumentUploadOptions>({})

// Chunk preview
const previewDocId = ref<number | null>(null)
const previewDocName = ref('')
const showPreview = ref(false)

// Progress polling
const pollingTimers = ref<Map<number, ReturnType<typeof setInterval>>>(new Map())

const chunkMethodOptions = [
  { label: 'Use KB Default', value: '' },
  { label: 'Naive', value: 'naive' },
  { label: 'Sentence', value: 'sentence' },
  { label: 'Token', value: 'token' },
  { label: 'Delimiter', value: 'delimiter' },
]

const isDelimiterMethod = computed(() => uploadOptions.value.chunk_method === 'delimiter')

async function fetchKb() {
  try {
    kb.value = await ragService.getKnowledgeBase(kbId.value)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load knowledge base')
  }
}

async function fetchDocuments() {
  loading.value = true
  try {
    documents.value = await ragService.listDocuments(kbId.value)
    startPollingForProcessing()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load documents')
  } finally {
    loading.value = false
  }
}

function startPollingForProcessing() {
  // Stop existing timers
  stopAllPolling()

  // Start polling for documents that are still processing
  for (const doc of documents.value) {
    if (doc.status === 1) {
      const timer = setInterval(async () => {
        try {
          const progress = await ragService.getDocumentProgress(kbId.value, doc.id)
          const idx = documents.value.findIndex((d) => d.id === doc.id)
          if (idx !== -1) {
            documents.value[idx].status = progress.status
            documents.value[idx].processing_step = progress.processing_step
            documents.value[idx].parse_progress = progress.parse_progress
            documents.value[idx].chunk_progress = progress.chunk_progress
            documents.value[idx].embed_progress = progress.embed_progress
          }
          if (progress.status !== 1) {
            clearInterval(timer)
            pollingTimers.value.delete(doc.id)
            fetchKb()
            fetchDocuments()
          }
        } catch {
          clearInterval(timer)
          pollingTimers.value.delete(doc.id)
        }
      }, 3000)
      pollingTimers.value.set(doc.id, timer)
    }
  }
}

function stopAllPolling() {
  for (const timer of pollingTimers.value.values()) {
    clearInterval(timer)
  }
  pollingTimers.value.clear()
}

async function handleUpload({ file }: { file: UploadFileInfo }) {
  if (!file.file) return
  uploading.value = true
  try {
    const opts: DocumentUploadOptions = {}
    if (uploadOptions.value.chunk_method) {
      opts.chunk_method = uploadOptions.value.chunk_method
    }
    if (uploadOptions.value.chunk_size != null) {
      opts.chunk_size = uploadOptions.value.chunk_size
    }
    if (uploadOptions.value.chunk_overlap != null) {
      opts.chunk_overlap = uploadOptions.value.chunk_overlap
    }
    if (uploadOptions.value.chunk_separator) {
      opts.chunk_separator = uploadOptions.value.chunk_separator
    }
    await ragService.uploadDocument(kbId.value, file.file, opts)
    message.success(`"${file.name}" uploaded and processing`)
    fetchDocuments()
    fetchKb()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Upload failed')
  } finally {
    uploading.value = false
  }
}

function confirmDelete(doc: RagDocumentListItem) {
  dialog.warning({
    title: 'Delete Document',
    content: `Are you sure you want to delete "${doc.name}"? All associated chunks will be removed.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await ragService.deleteDocument(kbId.value, doc.id)
        message.success('Document deleted')
        fetchDocuments()
        fetchKb()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete document')
      }
    },
  })
}

function openChunkPreview(doc: RagDocumentListItem) {
  previewDocId.value = doc.id
  previewDocName.value = doc.name
  showPreview.value = true
}

type TagType = 'default' | 'info' | 'success' | 'error' | 'warning' | 'primary'

function statusTag(status: number): { type: TagType; label: string } {
  const map: Record<number, { type: TagType; label: string }> = {
    0: { type: 'default', label: 'Pending' },
    1: { type: 'info', label: 'Processing' },
    2: { type: 'success', label: 'Completed' },
    3: { type: 'error', label: 'Failed' },
  }
  return map[status] ?? { type: 'default', label: 'Unknown' }
}

function overallProgress(doc: RagDocumentListItem): number {
  return Math.round((doc.parse_progress + doc.chunk_progress + doc.embed_progress) / 3)
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

const columns: DataTableColumns<RagDocumentListItem> = [
  {
    title: 'Name',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', { class: 'font-medium' }, row.name)
    },
  },
  {
    title: 'Type',
    key: 'file_type',
    width: 80,
    render(row) {
      return h(NTag, { size: 'tiny', round: true }, { default: () => row.file_type.toUpperCase() })
    },
  },
  {
    title: 'Size',
    key: 'file_size',
    width: 100,
    render(row) {
      return formatFileSize(row.file_size)
    },
  },
  {
    title: 'Chunks',
    key: 'chunk_count',
    width: 80,
    align: 'center',
  },
  {
    title: 'Status',
    key: 'status',
    width: 200,
    render(row) {
      if (row.status === 1) {
        const step = row.processing_step || 'processing'
        const pct = overallProgress(row)
        return h('div', { class: 'space-y-1' }, [
          h('div', { class: 'text-xs text-gray-500' }, `${step} (${pct}%)`),
          h(NProgress, { percentage: pct, height: 6, showIndicator: false, status: 'info' }),
        ])
      }
      const s = statusTag(row.status)
      return h(NTag, { type: s.type, size: 'small', round: true }, { default: () => s.label })
    },
  },
  {
    title: 'Created',
    key: 'created_at',
    width: 170,
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 160,
    render(row) {
      const buttons = []
      if (row.status === 2) {
        buttons.push(
          h(NButton, { size: 'small', secondary: true, onClick: () => openChunkPreview(row) }, { default: () => 'Preview' }),
        )
      }
      buttons.push(
        h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => 'Delete' }),
      )
      return h(NSpace, { size: 'small' }, { default: () => buttons })
    },
  },
]

onMounted(() => {
  fetchKb()
  fetchDocuments()
})
</script>

<script lang="ts">
import { h, onUnmounted } from 'vue'
export default {
  unmounted() {
    // Cleanup handled in setup
  },
}
</script>

<template>
  <div>
    <PageHeader
      :title="kb ? `Documents - ${kb.name}` : 'Documents'"
      :subtitle="kb ? `${kb.doc_count} documents, ${kb.chunk_count} chunks` : ''"
    >
      <template #actions>
        <NButton secondary @click="router.push({ name: 'rag-kb' })">
          Back to KBs
        </NButton>
      </template>
    </PageHeader>

    <!-- Upload Area -->
    <BentoCard class="mb-4">
      <NUpload
        :custom-request="() => {}"
        :show-file-list="false"
        accept=".txt,.pdf,.docx,.md,.html,.csv"
        :disabled="uploading"
        @change="handleUpload"
      >
        <NButton type="primary" :loading="uploading">
          Upload Document
        </NButton>
      </NUpload>

      <NCollapse class="mt-3">
        <NCollapseItem title="Advanced Chunking Settings" name="advanced">
          <div class="space-y-3">
            <NAlert type="info" :bordered="false" class="mb-3">
              Leave empty to use knowledge base defaults.
            </NAlert>
            <div class="flex flex-wrap gap-4">
              <div class="w-40">
                <label class="mb-1 block text-xs text-(--color-text-secondary)">Chunk Method</label>
                <NSelect
                  v-model:value="uploadOptions.chunk_method"
                  :options="chunkMethodOptions"
                  size="small"
                  clearable
                  placeholder="KB Default"
                />
              </div>
              <div class="w-32">
                <label class="mb-1 block text-xs text-(--color-text-secondary)">Chunk Size</label>
                <NInputNumber
                  v-model:value="uploadOptions.chunk_size"
                  :min="64"
                  :max="4096"
                  :step="64"
                  size="small"
                  placeholder="Default"
                  clearable
                />
              </div>
              <div class="w-32">
                <label class="mb-1 block text-xs text-(--color-text-secondary)">Overlap</label>
                <NInputNumber
                  v-model:value="uploadOptions.chunk_overlap"
                  :min="0"
                  :max="512"
                  :step="16"
                  size="small"
                  placeholder="Default"
                  clearable
                />
              </div>
              <div v-if="isDelimiterMethod" class="w-48">
                <label class="mb-1 block text-xs text-(--color-text-secondary)">Separator</label>
                <NInput
                  v-model:value="uploadOptions.chunk_separator"
                  size="small"
                  placeholder="e.g. \\n\\n or ---"
                />
              </div>
            </div>
          </div>
        </NCollapseItem>
      </NCollapse>

      <NAlert type="info" class="mt-3" :bordered="false">
        Supported formats: TXT, PDF, DOCX, Markdown, HTML, CSV
      </NAlert>
    </BentoCard>

    <!-- Table -->
    <TableSkeleton v-if="loading" :rows="5" :cols="6" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="documents"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <!-- Chunk Preview Modal -->
    <ChunkPreviewModal
      v-model:visible="showPreview"
      :kb-id="kbId"
      :doc-id="previewDocId"
      :doc-name="previewDocName"
    />
  </div>
</template>
