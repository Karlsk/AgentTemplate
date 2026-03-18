<script setup lang="ts">
import { h, ref, computed, watch } from 'vue'
import {
  NModal,
  NDataTable,
  NButton,
  NSpace,
  NInput,
  NTag,
  NSpin,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, DataTableRowKey } from 'naive-ui'
import nl2sqlService from '@/services/nl2sql.service'
import type { DiscoverTableItem } from '@/types/nl2sql'

const props = defineProps<{
  visible: boolean
  instanceId: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const loading = ref(false)
const syncing = ref(false)
const searchQuery = ref('')
const tables = ref<DiscoverTableItem[]>([])
const checkedKeys = ref<DataTableRowKey[]>([])
const errorMsg = ref('')

const filteredTables = computed(() => {
  if (!searchQuery.value) return tables.value
  const q = searchQuery.value.toLowerCase()
  return tables.value.filter(
    t => t.table_name.toLowerCase().includes(q)
      || (t.table_comment && t.table_comment.toLowerCase().includes(q))
  )
})

const selectedCount = computed(() => checkedKeys.value.length)

const columns: DataTableColumns<DiscoverTableItem> = [
  { type: 'selection' },
  { title: 'Table Name', key: 'table_name', resizable: true },
  { title: 'Comment', key: 'table_comment', resizable: true, ellipsis: { tooltip: true } },
  {
    title: 'Status',
    key: 'synced',
    width: 100,
    render(row) {
      return row.synced
        ? h(NTag, { type: 'success', size: 'small', round: true }, { default: () => 'Synced' })
        : h(NTag, { type: 'default', size: 'small', round: true }, { default: () => 'New' })
    },
  },
]

function rowKey(row: DiscoverTableItem) {
  return row.table_name
}

watch(() => props.visible, async (val) => {
  if (val) {
    await fetchTables()
  } else {
    tables.value = []
    checkedKeys.value = []
    searchQuery.value = ''
    errorMsg.value = ''
  }
})

async function fetchTables() {
  loading.value = true
  errorMsg.value = ''
  try {
    const resp = await nl2sqlService.discoverTables(props.instanceId)
    tables.value = resp.tables
    // Pre-select already synced tables
    checkedKeys.value = resp.tables.filter(t => t.synced).map(t => t.table_name)
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : 'Failed to discover tables'
  } finally {
    loading.value = false
  }
}

function selectAll() {
  checkedKeys.value = filteredTables.value.map(t => t.table_name)
}

function deselectAll() {
  checkedKeys.value = []
}

async function handleSync() {
  if (selectedCount.value === 0) {
    message.warning('Please select at least one table')
    return
  }
  syncing.value = true
  try {
    const result = await nl2sqlService.syncSchema(
      props.instanceId,
      checkedKeys.value as string[],
    )
    message.success(
      `Schema synced: ${result.tables_synced} tables, ${result.ddl_generated} DDL entries`,
    )
    emit('success')
    handleClose()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Schema sync failed')
  } finally {
    syncing.value = false
  }
}

function handleClose() {
  emit('update:visible', false)
}
</script>

<template>
  <NModal
    :show="visible"
    preset="card"
    title="Sync Schema - Select Tables"
    style="width: 720px; max-height: 80vh"
    :mask-closable="false"
    @update:show="handleClose"
  >
    <NSpin :show="loading">
      <div v-if="errorMsg" class="mb-3 text-red-500">
        {{ errorMsg }}
      </div>
      <template v-else>
        <div class="mb-3 flex items-center gap-2">
          <NInput
            v-model:value="searchQuery"
            placeholder="Search tables..."
            clearable
            style="flex: 1"
          />
          <NButton size="small" secondary @click="selectAll">Select All</NButton>
          <NButton size="small" secondary @click="deselectAll">Deselect All</NButton>
        </div>
        <NDataTable
          v-model:checked-row-keys="checkedKeys"
          :columns="columns"
          :data="filteredTables"
          :row-key="rowKey"
          size="small"
          :max-height="400"
          virtual-scroll
        />
        <div class="mt-2 text-sm" style="color: var(--n-text-color-3, #999)">
          {{ tables.length }} tables discovered, {{ selectedCount }} selected
        </div>
      </template>
    </NSpin>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Cancel</NButton>
        <NButton
          type="primary"
          :loading="syncing"
          :disabled="loading || selectedCount === 0"
          @click="handleSync"
        >
          Sync Selected ({{ selectedCount }})
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
