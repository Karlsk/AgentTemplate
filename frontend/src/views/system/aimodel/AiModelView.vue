<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NDataTable, NPopconfirm, NTag, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import AiModelModal from './AiModelModal.vue'
import aiModelService from '@/services/aiModel.service'
import type { AiModel } from '@/types/aiModel'
import { SupplierLabels, ProtocolLabels, type Supplier, type Protocol } from '@/types/aiModel'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const models = ref<AiModel[]>([])
const searchKeyword = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout>>()

const modalVisible = ref(false)
const editingModel = ref<AiModel | null>(null)

async function fetchModels() {
  loading.value = true
  try {
    models.value = await aiModelService.listModels(searchKeyword.value || undefined)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load models')
  } finally {
    loading.value = false
  }
}

function handleSearch(value: string) {
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    searchKeyword.value = value
    fetchModels()
  }, 300)
}

function openCreateModal() {
  editingModel.value = null
  modalVisible.value = true
}

function openEditModal(model: AiModel) {
  editingModel.value = model
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchModels()
}

function confirmDelete(model: AiModel) {
  dialog.warning({
    title: 'Delete Model',
    content: `Are you sure you want to delete "${model.name}"?`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await aiModelService.deleteModel(model.id)
        message.success('Model deleted')
        fetchModels()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete model')
      }
    },
  })
}

async function setDefault(model: AiModel) {
  try {
    await aiModelService.setDefaultModel(model.id)
    message.success(`"${model.name}" set as default`)
    fetchModels()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to set default')
  }
}

async function setBackup(model: AiModel) {
  try {
    await aiModelService.setBackupModel(model.id)
    message.success(`"${model.name}" set as backup`)
    fetchModels()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to set backup')
  }
}

const columns: DataTableColumns<AiModel> = [
  {
    title: 'Name',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row) {
      return h('div', { class: 'flex items-center gap-2' }, [
        h('span', { class: 'font-medium' }, row.name),
        row.default_model
          ? h(NTag, { size: 'tiny', type: 'info', round: true }, { default: () => 'Default' })
          : null,
        row.backup_model
          ? h(NTag, { size: 'tiny', type: 'warning', round: true }, { default: () => 'Backup' })
          : null,
      ])
    },
  },
  {
    title: 'Base Model',
    key: 'base_model',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Supplier',
    key: 'supplier',
    width: 120,
    render(row) {
      return SupplierLabels[row.supplier as Supplier] ?? String(row.supplier)
    },
  },
  {
    title: 'Protocol',
    key: 'protocol',
    width: 120,
    render(row) {
      return ProtocolLabels[row.protocol as Protocol] ?? String(row.protocol)
    },
  },
  {
    title: 'Type',
    key: 'llm_type',
    width: 100,
  },
  {
    title: 'Status',
    key: 'status',
    width: 100,
    render(row) {
      return h(StatusBadge, { active: row.status === 1 })
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 280,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => openEditModal(row) }, { default: () => 'Edit' }),
          h(NButton, { size: 'small', secondary: true, onClick: () => setDefault(row), disabled: row.default_model }, { default: () => 'Set Default' }),
          h(NButton, { size: 'small', secondary: true, onClick: () => setBackup(row), disabled: row.backup_model }, { default: () => 'Set Backup' }),
          h(NPopconfirm, { onPositiveClick: () => confirmDelete(row) }, {
            trigger: () => h(NButton, { size: 'small', secondary: true, type: 'error' }, { default: () => 'Delete' }),
            default: () => `Delete "${row.name}"?`,
          }),
        ],
      })
    },
  },
]

onMounted(fetchModels)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div>
    <PageHeader title="AI Models" subtitle="Manage your AI model configurations">
      <template #actions>
        <NButton type="primary" @click="openCreateModal">
          + New Model
        </NButton>
      </template>
    </PageHeader>

    <!-- Search -->
    <BentoCard class="mb-4">
      <NInput
        placeholder="Search models..."
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
        :data="models"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <!-- Modal -->
    <AiModelModal
      v-model:visible="modalVisible"
      :model="editingModel"
      @success="handleModalSuccess"
    />
  </div>
</template>
