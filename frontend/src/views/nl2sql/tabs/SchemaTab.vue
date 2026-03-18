<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NDataTable, NTag, NEmpty, NSpin, NButton, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import nl2sqlService from '@/services/nl2sql.service'
import type { SchemaTableInfo, SchemaColumnInfo } from '@/types/nl2sql'

const props = defineProps<{
  instanceId: number
}>()

const emit = defineEmits<{
  edit: [table: SchemaTableInfo]
  refresh: []
}>()

const message = useMessage()
const dialog = useDialog()
const loading = ref(true)
const tables = ref<SchemaTableInfo[]>([])
const expandedRowKeys = ref<string[]>([])

async function fetchSchema() {
  loading.value = true
  try {
    tables.value = await nl2sqlService.getSchemaTable(props.instanceId)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load schema')
  } finally {
    loading.value = false
  }
}

function handleEdit(row: SchemaTableInfo) {
  emit('edit', row)
}

function handleDelete(row: SchemaTableInfo) {
  dialog.warning({
    title: 'Delete Table',
    content: `Are you sure you want to delete "${row.table_name}"? This will also remove its DDL training data and vector embeddings.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        const result = await nl2sqlService.deleteSchemaTable(props.instanceId, row.table_name)
        message.success(
          `Deleted "${row.table_name}": ${result.schema_rows_deleted} schema rows, ${result.training_data_deleted} DDL entries`
        )
        await fetchSchema()
        emit('refresh')
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete table')
      }
    },
  })
}

const tableColumns: DataTableColumns<SchemaTableInfo> = [
  {
    type: 'expand',
    renderExpand(row) {
      return h('div', { class: 'p-4' }, [
        h(NDataTable, {
          columns: columnColumns,
          data: row.columns,
          bordered: true,
          singleLine: false,
          size: 'small',
        }),
      ])
    },
  },
  {
    title: 'Table Name',
    key: 'table_name',
    render(row) {
      const name = row.table_schema ? `${row.table_schema}.${row.table_name}` : row.table_name
      return h('span', { class: 'font-mono font-medium' }, name)
    },
  },
  {
    title: 'Comment',
    key: 'table_comment',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Columns',
    key: 'columns',
    width: 100,
    render(row) {
      return row.columns.length
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 160,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, {
            size: 'small',
            secondary: true,
            onClick: () => handleEdit(row),
          }, { default: () => 'Edit' }),
          h(NButton, {
            size: 'small',
            secondary: true,
            type: 'error',
            onClick: () => handleDelete(row),
          }, { default: () => 'Delete' }),
        ],
      })
    },
  },
]

const columnColumns: DataTableColumns<SchemaColumnInfo> = [
  {
    title: 'Column',
    key: 'column_name',
    render(row) {
      return h('span', { class: 'font-mono' }, row.column_name)
    },
  },
  {
    title: 'Type',
    key: 'column_type',
    render(row) {
      return h('span', { class: 'font-mono text-xs' }, row.column_type || '-')
    },
  },
  {
    title: 'Comment',
    key: 'column_comment',
    ellipsis: { tooltip: true },
  },
  {
    title: 'PK',
    key: 'is_primary_key',
    width: 60,
    render(row) {
      return row.is_primary_key ? h(NTag, { type: 'warning', size: 'small' }, { default: () => 'PK' }) : '-'
    },
  },
  {
    title: 'Nullable',
    key: 'is_nullable',
    width: 80,
    render(row) {
      return row.is_nullable ? 'Yes' : 'No'
    },
  },
]

defineExpose({ fetchSchema })

onMounted(fetchSchema)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div class="py-4">
    <NSpin :show="loading">
      <NEmpty v-if="!loading && tables.length === 0" description="No schema synced. Click 'Sync Schema' to fetch table structure from the database." />
      <NDataTable
        v-else
        :columns="tableColumns"
        :data="tables"
        :row-key="(row: SchemaTableInfo) => row.table_name"
        :expanded-row-keys="expandedRowKeys"
        @update:expanded-row-keys="(keys: string[]) => expandedRowKeys = keys"
        :bordered="false"
        :single-line="false"
        striped
      />
    </NSpin>
  </div>
</template>
