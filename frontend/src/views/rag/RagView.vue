<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NDataTable, NPopconfirm, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import RagInstanceModal from './RagInstanceModal.vue'
import { ragService } from '@/services/rag.service'
import type { RagInstance } from '@/types/rag'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const instances = ref<RagInstance[]>([])
const searchKeyword = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout>>()

const modalVisible = ref(false)
const editingInstance = ref<RagInstance | null>(null)

async function fetchInstances() {
  loading.value = true
  try {
    instances.value = await ragService.listInstances()
  } catch (err) {
    message.error('Failed to load RAG instances')
  } finally {
    loading.value = false
  }
}

function handleSearch(value: string) {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    searchKeyword.value = value
    // Local search filter or refetch
    fetchInstances()
  }, 300)
}

function openCreateModal() {
  editingInstance.value = null
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchInstances()
}

function goToDetail(instance: RagInstance) {
  router.push(`/rag/instance/${instance.id}`)
}

function confirmDelete(instance: RagInstance) {
  dialog.warning({
    title: 'Delete Knowledge Base',
    content: `Are you sure you want to delete "${instance.name}"? This will also remove the vector collection.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await ragService.deleteInstance(instance.id)
        message.success('Knowledge base deleted')
        fetchInstances()
      } catch (err) {
        message.error('Failed to delete knowledge base')
      }
    },
  })
}

const columns: DataTableColumns<RagInstance> = [
  {
    title: 'Name',
    key: 'name',
    render(row) {
      return h('div', { class: 'font-medium' }, row.name)
    },
  },
  {
    title: 'Collection',
    key: 'collection_name',
    render(row) {
      return h('code', { class: 'bg-gray-100 px-2 py-1 rounded text-sm' }, row.collection_name)
    },
  },
  {
    title: 'Created At',
    key: 'created_at',
    render(row) {
      return row.created_at ? new Date(row.created_at).toLocaleString() : '-'
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 200,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => goToDetail(row) }, { default: () => 'Manage' }),
          h(NPopconfirm, { onPositiveClick: () => confirmDelete(row) }, {
            trigger: () => h(NButton, { size: 'small', secondary: true, type: 'error' }, { default: () => 'Delete' }),
            default: () => `Delete "${row.name}"?`,
          }),
        ],
      })
    },
  },
]

onMounted(fetchInstances)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div>
    <PageHeader title="Knowledge Base" subtitle="Manage your RAG instances and vector collections">
      <template #actions>
        <NButton type="primary" @click="openCreateModal">
          + New Knowledge Base
        </NButton>
      </template>
    </PageHeader>

    <BentoCard class="mb-4">
      <NInput
        placeholder="Search knowledge bases..."
        clearable
        @update:value="handleSearch"
      >
        <template #prefix>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </template>
      </NInput>
    </BentoCard>

    <TableSkeleton v-if="loading" :rows="5" :cols="4" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="instances"
        :bordered="false"
        striped
      />
    </BentoCard>

    <RagInstanceModal
      v-model:visible="modalVisible"
      :instance="editingInstance"
      @success="handleModalSuccess"
    />
  </div>
</template>
