<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NDataTable, NButton, NSpace,
  NCheckbox, NSpin, useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import nl2sqlService from '@/services/nl2sql.service'
import type { SchemaTableInfo, SchemaColumnInfo, UpdateSchemaColumnItem } from '@/types/nl2sql'

interface EditableColumn extends SchemaColumnInfo {
  selected: boolean
}

const props = defineProps<{
  visible: boolean
  instanceId: number
  tableInfo: SchemaTableInfo | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const saving = ref(false)
const tableComment = ref('')
const editableColumns = ref<EditableColumn[]>([])

watch(() => props.visible, (val) => {
  if (val && props.tableInfo) {
    tableComment.value = props.tableInfo.table_comment || ''
    editableColumns.value = props.tableInfo.columns.map(c => ({
      ...c,
      selected: true,
    }))
  }
})

const title = computed(() =>
  props.tableInfo ? `Edit Table: ${props.tableInfo.table_name}` : 'Edit Table'
)

const selectedCount = computed(() =>
  editableColumns.value.filter(c => c.selected).length
)

function toggleAll(checked: boolean) {
  editableColumns.value.forEach(c => { c.selected = checked })
}

const allSelected = computed(() =>
  editableColumns.value.length > 0 && editableColumns.value.every(c => c.selected)
)

const columns: DataTableColumns<EditableColumn> = [
  {
    title: '',
    key: 'selected',
    width: 50,
    render(row) {
      return h(NCheckbox, {
        checked: row.selected,
        'onUpdate:checked': (val: boolean) => { row.selected = val },
      })
    },
    renderHeader() {
      return h(NCheckbox, {
        checked: allSelected.value,
        'onUpdate:checked': (val: boolean) => toggleAll(val),
      })
    },
  },
  {
    title: 'Column',
    key: 'column_name',
    width: 160,
    render(row) {
      return h('span', { class: 'font-mono' }, row.column_name)
    },
  },
  {
    title: 'Type',
    key: 'column_type',
    width: 120,
    render(row) {
      return h('span', { class: 'font-mono text-xs' }, row.column_type || '-')
    },
  },
  {
    title: 'Comment',
    key: 'column_comment',
    render(row) {
      return h(NInput, {
        value: row.column_comment || '',
        size: 'small',
        placeholder: 'Column description',
        disabled: !row.selected,
        'onUpdate:value': (val: string) => { row.column_comment = val || null },
      })
    },
  },
]

async function handleSave() {
  if (!props.tableInfo) return
  if (selectedCount.value === 0) {
    message.warning('Please keep at least one column')
    return
  }

  saving.value = true
  try {
    const selectedCols: UpdateSchemaColumnItem[] = editableColumns.value
      .filter(c => c.selected)
      .map(c => ({
        column_name: c.column_name,
        column_comment: c.column_comment,
      }))

    await nl2sqlService.updateSchemaTable(
      props.instanceId,
      props.tableInfo.table_name,
      {
        table_comment: tableComment.value || null,
        columns: selectedCols,
      }
    )
    message.success('Table schema updated and DDL regenerated')
    emit('success')
    handleClose()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to update table schema')
  } finally {
    saving.value = false
  }
}

function handleClose() {
  emit('update:visible', false)
}
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <NModal
    :show="visible"
    preset="card"
    :title="title"
    style="width: 720px; max-height: 85vh"
    :mask-closable="false"
    @update:show="handleClose"
  >
    <NForm label-placement="left" label-width="120">
      <NFormItem label="Table Comment">
        <NInput
          v-model:value="tableComment"
          type="textarea"
          placeholder="Table description"
          :rows="2"
        />
      </NFormItem>
    </NForm>

    <div class="mb-2 text-sm font-medium">
      Columns ({{ selectedCount }} / {{ editableColumns.length }} selected)
    </div>

    <NDataTable
      :columns="columns"
      :data="editableColumns"
      :row-key="(row: EditableColumn) => row.column_name"
      size="small"
      :max-height="360"
      :bordered="true"
      :single-line="false"
    />

    <div class="mt-2 text-xs" style="color: var(--n-text-color-3, #999)">
      Unchecked columns will be removed from schema. Save will automatically regenerate DDL.
    </div>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Cancel</NButton>
        <NButton
          type="primary"
          :loading="saving"
          :disabled="selectedCount === 0"
          @click="handleSave"
        >
          Save & Regenerate DDL
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
