<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NDataTable, NTag, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import KnowledgeBaseModal from './KnowledgeBaseModal.vue'
import ragService from '@/services/rag.service'
import type { KnowledgeBaseListItem } from '@/types/rag'
import { ChunkMethodLabels, RetrievalModeLabels } from '@/types/rag'

const message = useMessage()
const dialog = useDialog()
const router = useRouter()

const loading = ref(true)
const knowledgeBases = ref<KnowledgeBaseListItem[]>([])
const searchKeyword = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout>>()

const modalVisible = ref(false)
const editingKb = ref<KnowledgeBaseListItem | null>(null)

async function fetchKnowledgeBases() {
  loading.value = true
  try {
    knowledgeBases.value = await ragService.listKnowledgeBases(searchKeyword.value || undefined)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load knowledge bases')
  } finally {
    loading.value = false
  }
}

function handleSearch(value: string) {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    searchKeyword.value = value
    fetchKnowledgeBases()
  }, 300)
}

function openCreateModal() {
  editingKb.value = null
  modalVisible.value = true
}

function openEditModal(kb: KnowledgeBaseListItem) {
  editingKb.value = kb
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchKnowledgeBases()
}

function confirmDelete(kb: KnowledgeBaseListItem) {
  dialog.warning({
    title: 'Delete Knowledge Base',
    content: `Are you sure you want to delete "${kb.name}"? All documents and chunks will be permanently removed.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await ragService.deleteKnowledgeBase(kb.id)
        message.success('Knowledge base deleted')
        fetchKnowledgeBases()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete knowledge base')
      }
    },
  })
}

function viewDocuments(kb: KnowledgeBaseListItem) {
  router.push({ name: 'rag-documents', params: { kbId: kb.id } })
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

const columns: DataTableColumns<KnowledgeBaseListItem> = [
  {
    title: 'Name',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', { class: 'font-medium' }, row.name)
    },
  },
  {
    title: 'Description',
    key: 'description',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Chunk Method',
    key: 'chunk_method',
    width: 130,
    render(row) {
      return ChunkMethodLabels[row.chunk_method] ?? row.chunk_method
    },
  },
  {
    title: 'Retrieval',
    key: 'retrieval_mode',
    width: 100,
    render(row) {
      return RetrievalModeLabels[row.retrieval_mode] ?? row.retrieval_mode
    },
  },
  {
    title: 'Documents',
    key: 'doc_count',
    width: 100,
    align: 'center',
  },
  {
    title: 'Chunks',
    key: 'chunk_count',
    width: 100,
    align: 'center',
  },
  {
    title: 'Status',
    key: 'status',
    width: 100,
    render(row) {
      const active = row.status === 1
      return h(NTag, { type: active ? 'success' : 'default', size: 'small', round: true }, { default: () => active ? 'Active' : 'Disabled' })
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
    width: 280,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => viewDocuments(row) }, { default: () => 'Documents' }),
          h(NButton, { size: 'small', secondary: true, onClick: () => openEditModal(row) }, { default: () => 'Edit' }),
          h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => 'Delete' }),
        ],
      })
    },
  },
]

onMounted(fetchKnowledgeBases)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div>
    <PageHeader title="Knowledge Bases" subtitle="Manage RAG knowledge bases and document collections">
      <template #actions>
        <NButton secondary @click="router.push({ name: 'rag-search' })">
          Search
        </NButton>
        <NButton type="primary" @click="openCreateModal">
          + New Knowledge Base
        </NButton>
      </template>
    </PageHeader>

    <!-- Search -->
    <BentoCard class="mb-4">
      <NInput
        placeholder="Search knowledge bases..."
        clearable
        @update:value="handleSearch"
      >
        <template #prefix>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-(--color-text-secondary)">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </template>
      </NInput>
    </BentoCard>

    <!-- Table -->
    <TableSkeleton v-if="loading" :rows="5" :cols="7" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="knowledgeBases"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <!-- Modal -->
    <KnowledgeBaseModal
      v-model:visible="modalVisible"
      :kb="editingKb"
      @success="handleModalSuccess"
    />
  </div>
</template>
