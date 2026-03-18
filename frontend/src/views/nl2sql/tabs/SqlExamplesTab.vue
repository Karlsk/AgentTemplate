<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NDataTable, NEmpty, NSpin, NPagination, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import SqlExampleModal from './SqlExampleModal.vue'
import nl2sqlService from '@/services/nl2sql.service'
import type { TrainingDataListItem } from '@/types/nl2sql'

const props = defineProps<{
  instanceId: number
}>()

const emit = defineEmits<{
  refresh: []
}>()

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const items = ref<TrainingDataListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const modalVisible = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const offset = (page.value - 1) * pageSize.value
    const result = await nl2sqlService.listTrainingData(props.instanceId, 'sql', offset, pageSize.value)
    items.value = result.items
    total.value = result.total
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load data')
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchData()
  emit('refresh')
}

function confirmDelete(item: TrainingDataListItem) {
  dialog.warning({
    title: 'Delete SQL Example',
    content: 'Are you sure you want to delete this SQL example?',
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await nl2sqlService.deleteTrainingData(props.instanceId, item.id)
        message.success('Deleted')
        fetchData()
        emit('refresh')
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete')
      }
    },
  })
}

function handlePageChange(newPage: number) {
  page.value = newPage
  fetchData()
}

const columns: DataTableColumns<TrainingDataListItem> = [
  {
    title: 'Question',
    key: 'question',
    ellipsis: { tooltip: true },
    render(row) {
      return row.question || row.content
    },
  },
  {
    title: 'SQL',
    key: 'sql_text',
    ellipsis: { tooltip: true },
    render(row) {
      return h('code', { class: 'text-xs' }, row.sql_text || '-')
    },
  },
  {
    title: 'Source',
    key: 'source',
    width: 100,
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 100,
    render(row) {
      return h(NButton, {
        size: 'small',
        secondary: true,
        type: 'error',
        onClick: () => confirmDelete(row),
      }, { default: () => 'Delete' })
    },
  },
]

onMounted(fetchData)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div class="py-4">
    <div class="mb-4 flex justify-end">
      <NButton type="primary" @click="openAddModal">
        + Add SQL Example
      </NButton>
    </div>

    <NSpin :show="loading">
      <NEmpty v-if="!loading && items.length === 0" description="No SQL examples yet. Add question-SQL pairs to improve NL2SQL accuracy." />
      <template v-else>
        <NDataTable
          :columns="columns"
          :data="items"
          :bordered="false"
          :single-line="false"
          striped
        />
        <div class="mt-4 flex justify-end">
          <NPagination
            v-model:page="page"
            :page-size="pageSize"
            :item-count="total"
            @update:page="handlePageChange"
          />
        </div>
      </template>
    </NSpin>

    <SqlExampleModal
      v-model:visible="modalVisible"
      :instance-id="instanceId"
      @success="handleModalSuccess"
    />
  </div>
</template>
