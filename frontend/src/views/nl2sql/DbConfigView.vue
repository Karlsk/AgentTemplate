<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NDataTable, NTag, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import DbConfigModal from './DbConfigModal.vue'
import nl2sqlService from '@/services/nl2sql.service'
import type { DbConfigListItem } from '@/types/nl2sql'
import { DbTypeLabels, DbConfigStatusLabels } from '@/types/nl2sql'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const dbConfigs = ref<DbConfigListItem[]>([])
const searchKeyword = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout>>()

const modalVisible = ref(false)
const editingConfig = ref<DbConfigListItem | null>(null)
const testingId = ref<number | null>(null)

async function fetchDbConfigs() {
  loading.value = true
  try {
    dbConfigs.value = await nl2sqlService.listDbConfigs(searchKeyword.value || undefined)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load DB configs')
  } finally {
    loading.value = false
  }
}

function handleSearch(value: string) {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    searchKeyword.value = value
    fetchDbConfigs()
  }, 300)
}

function openCreateModal() {
  editingConfig.value = null
  modalVisible.value = true
}

function openEditModal(config: DbConfigListItem) {
  editingConfig.value = config
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchDbConfigs()
}

async function testConnection(config: DbConfigListItem) {
  testingId.value = config.id
  try {
    const result = await nl2sqlService.testDbConfigById(config.id)
    if (result.success) {
      message.success(`Connection successful (${result.latency_ms}ms)`)
    } else {
      message.error(`Connection failed: ${result.message}`)
    }
    fetchDbConfigs()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Test failed')
  } finally {
    testingId.value = null
  }
}

function confirmDelete(config: DbConfigListItem) {
  dialog.warning({
    title: 'Delete DB Config',
    content: `Are you sure you want to delete "${config.name}"?`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await nl2sqlService.deleteDbConfig(config.id)
        message.success('DB config deleted')
        fetchDbConfigs()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete')
      }
    },
  })
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function getStatusType(status: number): 'default' | 'success' | 'error' {
  if (status === 1) return 'success'
  if (status === 2) return 'error'
  return 'default'
}

const columns: DataTableColumns<DbConfigListItem> = [
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
    key: 'db_type',
    width: 120,
    render(row) {
      return DbTypeLabels[row.db_type] ?? row.db_type
    },
  },
  {
    title: 'Host',
    key: 'host',
    ellipsis: { tooltip: true },
    render(row) {
      return `${row.host}:${row.port}`
    },
  },
  {
    title: 'Database',
    key: 'database_name',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Status',
    key: 'status',
    width: 110,
    render(row) {
      return h(NTag, { type: getStatusType(row.status), size: 'small', round: true }, { default: () => DbConfigStatusLabels[row.status] })
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
    width: 260,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, {
            size: 'small',
            secondary: true,
            loading: testingId.value === row.id,
            onClick: () => testConnection(row),
          }, { default: () => 'Test' }),
          h(NButton, { size: 'small', secondary: true, onClick: () => openEditModal(row) }, { default: () => 'Edit' }),
          h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => 'Delete' }),
        ],
      })
    },
  },
]

onMounted(fetchDbConfigs)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div>
    <PageHeader title="Database Configurations" subtitle="Manage database connections for NL2SQL">
      <template #actions>
        <NButton type="primary" @click="openCreateModal">
          + New DB Config
        </NButton>
      </template>
    </PageHeader>

    <!-- Search -->
    <BentoCard class="mb-4">
      <NInput
        placeholder="Search DB configs..."
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
    <TableSkeleton v-if="loading" :rows="5" :cols="6" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="dbConfigs"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <!-- Modal -->
    <DbConfigModal
      v-model:visible="modalVisible"
      :config="editingConfig"
      @success="handleModalSuccess"
    />
  </div>
</template>
