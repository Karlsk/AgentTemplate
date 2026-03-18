<script setup lang="ts">
import { h, ref, computed, watch, onMounted } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NSelect, NButton, NSpace,
  NSteps, NStep, NDataTable, NTag, NRadioGroup, NRadio, NSpin,
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules, SelectOption, DataTableColumns, DataTableRowKey } from 'naive-ui'
import nl2sqlService from '@/services/nl2sql.service'
import aiModelService from '@/services/aiModel.service'
import type {
  NL2SQLInstanceListItem,
  NL2SQLInstanceCreatePayload,
  DbConfigListItem,
  DiscoverTableItem,
} from '@/types/nl2sql'
import { DdlModeOptions } from '@/types/nl2sql'

const props = defineProps<{
  visible: boolean
  instance: NL2SQLInstanceListItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const currentStep = ref(1)

const dbConfigs = ref<DbConfigListItem[]>([])
const embeddingModels = ref<{ id: number; name: string }[]>([])

// Step 2 state
const discoveringTables = ref(false)
const discoveredTables = ref<DiscoverTableItem[]>([])
const checkedTableKeys = ref<DataTableRowKey[]>([])
const tableSearchQuery = ref('')

const isEdit = computed(() => !!props.instance)
const title = computed(() => isEdit.value ? 'Edit NL2SQL Instance' : 'New NL2SQL Instance')

const form = ref<NL2SQLInstanceCreatePayload>({
  name: '',
  description: '',
  db_config_id: 0,
  embedding_model_id: undefined,
  ddl_mode: 'full',
})

const dbConfigOptions = computed<SelectOption[]>(() =>
  dbConfigs.value.map(c => ({ label: `${c.name} (${c.db_type})`, value: c.id }))
)

const embeddingModelOptions = computed<SelectOption[]>(() =>
  embeddingModels.value.map(m => ({ label: m.name, value: m.id }))
)

const filteredTables = computed(() => {
  if (!tableSearchQuery.value) return discoveredTables.value
  const q = tableSearchQuery.value.toLowerCase()
  return discoveredTables.value.filter(
    t => t.table_name.toLowerCase().includes(q)
      || (t.table_comment && t.table_comment.toLowerCase().includes(q))
  )
})

const selectedTableCount = computed(() => checkedTableKeys.value.length)

const discoverColumns: DataTableColumns<DiscoverTableItem> = [
  { type: 'selection' },
  { title: 'Table Name', key: 'table_name', resizable: true },
  {
    title: 'Comment',
    key: 'table_comment',
    resizable: true,
    ellipsis: { tooltip: true },
  },
]

function tableRowKey(row: DiscoverTableItem) {
  return row.table_name
}

watch(() => props.visible, (val) => {
  if (val) {
    currentStep.value = 1
    discoveredTables.value = []
    checkedTableKeys.value = []
    tableSearchQuery.value = ''

    if (props.instance) {
      form.value = {
        name: props.instance.name,
        description: props.instance.description,
        db_config_id: props.instance.db_config_id,
        embedding_model_id: undefined,
        ddl_mode: props.instance.ddl_mode || 'full',
      }
    } else {
      form.value = {
        name: '',
        description: '',
        db_config_id: 0,
        embedding_model_id: undefined,
        ddl_mode: 'full',
      }
    }
    fetchDbConfigs()
    fetchEmbeddingModels()
  }
})

async function fetchDbConfigs() {
  try {
    dbConfigs.value = await nl2sqlService.listDbConfigs()
    if (!isEdit.value && dbConfigs.value.length > 0 && !form.value.db_config_id) {
      form.value.db_config_id = dbConfigs.value[0].id
    }
  } catch {
    message.error('Failed to load DB configs')
  }
}

async function fetchEmbeddingModels() {
  try {
    const models = await aiModelService.listModels()
    embeddingModels.value = models
      .filter((m: { llm_type: string }) => m.llm_type === 'embedding')
      .map((m: { id: number; base_model: string }) => ({ id: m.id, name: m.base_model }))
  } catch {
    // Ignore - optional
  }
}

const rules: FormRules = {
  name: { required: true, message: 'Name is required' },
  db_config_id: { required: true, type: 'number', min: 1, message: 'DB config is required' },
}

async function handleNext() {
  if (currentStep.value === 1) {
    try {
      await formRef.value?.validate()
    } catch {
      return
    }

    if (isEdit.value) {
      // Edit mode: submit directly from step 1
      await handleSubmit()
      return
    }

    // Create mode: go to step 2 and discover tables
    currentStep.value = 2
    await discoverTables()
  }
}

async function discoverTables() {
  if (!form.value.db_config_id) return
  discoveringTables.value = true
  try {
    const items = await nl2sqlService.discoverTablesByConfig(form.value.db_config_id)
    discoveredTables.value = items
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to discover tables')
  } finally {
    discoveringTables.value = false
  }
}

function selectAllTables() {
  checkedTableKeys.value = filteredTables.value.map(t => t.table_name)
}

function deselectAllTables() {
  checkedTableKeys.value = []
}

async function handleSubmit() {
  submitting.value = true
  try {
    if (isEdit.value && props.instance) {
      await nl2sqlService.updateInstance({
        id: props.instance.id,
        name: form.value.name,
        description: form.value.description,
        embedding_model_id: form.value.embedding_model_id,
        ddl_mode: form.value.ddl_mode,
      })
      message.success('Instance updated')
    } else {
      const payload: NL2SQLInstanceCreatePayload = { ...form.value }
      if (checkedTableKeys.value.length > 0) {
        payload.table_names = checkedTableKeys.value as string[]
      }
      await nl2sqlService.createInstance(payload)
      message.success('Instance created')
    }
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Operation failed')
  } finally {
    submitting.value = false
  }
}

function handleBack() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

function handleClose() {
  emit('update:visible', false)
}

onMounted(() => {
  if (props.visible) {
    fetchDbConfigs()
    fetchEmbeddingModels()
  }
})
</script>

<template>
  <NModal
    :show="visible"
    preset="card"
    :title="title"
    style="width: 680px"
    :mask-closable="false"
    @update:show="handleClose"
  >
    <!-- Steps indicator (create mode only) -->
    <NSteps v-if="!isEdit" :current="currentStep" size="small" class="mb-6">
      <NStep title="Basic Info" />
      <NStep title="Select Tables" />
    </NSteps>

    <!-- Step 1: Basic Info -->
    <div v-show="currentStep === 1">
      <NForm ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="140">
        <NFormItem label="Name" path="name">
          <NInput v-model:value="form.name" placeholder="My NL2SQL Instance" />
        </NFormItem>

        <NFormItem label="Description">
          <NInput v-model:value="form.description" type="textarea" placeholder="Optional description" :rows="2" />
        </NFormItem>

        <NFormItem label="Database Config" path="db_config_id">
          <NSelect
            v-model:value="form.db_config_id"
            :options="dbConfigOptions"
            placeholder="Select a database"
            :disabled="isEdit"
          />
        </NFormItem>

        <NFormItem label="Embedding Model">
          <NSelect
            v-model:value="form.embedding_model_id"
            :options="embeddingModelOptions"
            placeholder="Default embedding model"
            clearable
          />
        </NFormItem>

        <NFormItem label="DDL Mode">
          <NRadioGroup v-model:value="form.ddl_mode">
            <NRadio v-for="opt in DdlModeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </NRadio>
          </NRadioGroup>
        </NFormItem>
      </NForm>
    </div>

    <!-- Step 2: Table Discovery (create mode only) -->
    <div v-show="currentStep === 2 && !isEdit">
      <NSpin :show="discoveringTables">
        <div class="mb-3 flex items-center gap-2">
          <NInput
            v-model:value="tableSearchQuery"
            placeholder="Search tables..."
            clearable
            style="flex: 1"
          />
          <NButton size="small" secondary @click="selectAllTables">Select All</NButton>
          <NButton size="small" secondary @click="deselectAllTables">Deselect All</NButton>
        </div>
        <NDataTable
          v-model:checked-row-keys="checkedTableKeys"
          :columns="discoverColumns"
          :data="filteredTables"
          :row-key="tableRowKey"
          size="small"
          :max-height="350"
          virtual-scroll
        />
        <div class="mt-2 text-sm" style="color: var(--n-text-color-3, #999)">
          {{ discoveredTables.length }} tables discovered, {{ selectedTableCount }} selected
        </div>
      </NSpin>
    </div>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Cancel</NButton>
        <NButton v-if="currentStep > 1 && !isEdit" @click="handleBack">Back</NButton>

        <!-- Step 1: Next button for create, Submit for edit -->
        <NButton
          v-if="currentStep === 1"
          type="primary"
          :loading="submitting"
          @click="handleNext"
        >
          {{ isEdit ? 'Update' : 'Next' }}
        </NButton>

        <!-- Step 2: Create button -->
        <NButton
          v-if="currentStep === 2 && !isEdit"
          type="primary"
          :loading="submitting"
          :disabled="discoveringTables"
          @click="handleSubmit"
        >
          Create ({{ selectedTableCount }} tables)
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
