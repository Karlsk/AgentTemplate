<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NDataTable, NTag, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import NL2SQLInstanceModal from './NL2SQLInstanceModal.vue'
import nl2sqlService from '@/services/nl2sql.service'
import type { NL2SQLInstanceListItem } from '@/types/nl2sql'
import { InstanceStatusLabels } from '@/types/nl2sql'

const message = useMessage()
const dialog = useDialog()
const router = useRouter()

const loading = ref(true)
const instances = ref<NL2SQLInstanceListItem[]>([])
const searchKeyword = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout>>()

const modalVisible = ref(false)
const editingInstance = ref<NL2SQLInstanceListItem | null>(null)

async function fetchInstances() {
  loading.value = true
  try {
    instances.value = await nl2sqlService.listInstances(searchKeyword.value || undefined)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load instances')
  } finally {
    loading.value = false
  }
}

function handleSearch(value: string) {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    searchKeyword.value = value
    fetchInstances()
  }, 300)
}

function openCreateModal() {
  editingInstance.value = null
  modalVisible.value = true
}

function openEditModal(instance: NL2SQLInstanceListItem) {
  editingInstance.value = instance
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchInstances()
}

function viewDetail(instance: NL2SQLInstanceListItem) {
  router.push({ name: 'nl2sql-instance-detail', params: { instanceId: instance.id } })
}

function confirmDelete(instance: NL2SQLInstanceListItem) {
  dialog.warning({
    title: 'Delete NL2SQL Instance',
    content: `Are you sure you want to delete "${instance.name}"? All training data will be permanently removed.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await nl2sqlService.deleteInstance(instance.id)
        message.success('Instance deleted')
        fetchInstances()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete')
      }
    },
  })
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function getStatusType(status: number): 'default' | 'success' | 'warning' {
  if (status === 1) return 'success'
  if (status === 2) return 'warning'
  return 'default'
}

const columns: DataTableColumns<NL2SQLInstanceListItem> = [
  {
    title: 'Name',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', { class: 'font-medium cursor-pointer text-(--color-primary)', onClick: () => viewDetail(row) }, row.name)
    },
  },
  {
    title: 'Description',
    key: 'description',
    ellipsis: { tooltip: true },
  },
  {
    title: 'DDL',
    key: 'ddl_count',
    width: 80,
    align: 'center',
  },
  {
    title: 'SQL',
    key: 'sql_count',
    width: 80,
    align: 'center',
  },
  {
    title: 'Docs',
    key: 'doc_count',
    width: 80,
    align: 'center',
  },
  {
    title: 'Status',
    key: 'status',
    width: 110,
    render(row) {
      return h(NTag, { type: getStatusType(row.status), size: 'small', round: true }, { default: () => InstanceStatusLabels[row.status] })
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
    width: 240,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => viewDetail(row) }, { default: () => 'Manage' }),
          h(NButton, { size: 'small', secondary: true, onClick: () => openEditModal(row) }, { default: () => 'Edit' }),
          h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => 'Delete' }),
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
    <PageHeader title="NL2SQL Instances" subtitle="Manage NL2SQL training instances">
      <template #actions>
        <NButton secondary @click="router.push({ name: 'nl2sql-db-config' })">
          DB Configs
        </NButton>
        <NButton type="primary" @click="openCreateModal">
          + New Instance
        </NButton>
      </template>
    </PageHeader>

    <!-- Search -->
    <BentoCard class="mb-4">
      <NInput
        placeholder="Search instances..."
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
        :data="instances"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <!-- Modal -->
    <NL2SQLInstanceModal
      v-model:visible="modalVisible"
      :instance="editingInstance"
      @success="handleModalSuccess"
    />
  </div>
</template>
