<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
  NButton,
  NSpace,
  NDynamicInput,
  NRadioGroup,
  NRadio,
  NText,
  NSpin,
  NAlert,
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import aiModelService from '@/services/aiModel.service'
import type { AiModel, AiModelConfigItem } from '@/types/aiModel'
import { Supplier, Protocol, SupplierLabels, ProtocolLabels } from '@/types/aiModel'

const props = defineProps<{
  visible: boolean
  model: AiModel | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const testing = ref(false)
const testResult = ref('')
const testError = ref('')
const testSuccess = ref(false)

const isEdit = computed(() => !!props.model)
const modalTitle = computed(() => (isEdit.value ? 'Edit Model' : 'New Model'))

const defaultFormValue = () => ({
  name: '',
  base_model: '',
  supplier: Supplier.OpenAI as number,
  protocol: Protocol.OpenAISdk as number,
  api_domain: '',
  api_key: '',
  default_model: false,
  backup_model: false,
  llm_type: 'chat',
  config_list: [] as AiModelConfigItem[],
})

const formValue = ref(defaultFormValue())

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.model) {
      loadModelForEdit(props.model)
    } else if (visible) {
      formValue.value = defaultFormValue()
    }
    // Reset test state when modal opens
    testResult.value = ''
    testError.value = ''
    testSuccess.value = false
  },
)

async function loadModelForEdit(model: AiModel) {
  try {
    const detail = await aiModelService.getModelById(model.id)
    // Decode base64 encoded api_key from backend
    let decodedApiKey = detail.api_key
    if (detail.api_key) {
      try {
        decodedApiKey = atob(detail.api_key)
      } catch {
        // If decoding fails, use original value
        decodedApiKey = detail.api_key
      }
    }
    formValue.value = {
      name: detail.name,
      base_model: detail.base_model,
      supplier: detail.supplier,
      protocol: detail.protocol,
      api_domain: detail.api_domain,
      api_key: decodedApiKey,
      default_model: detail.default_model,
      backup_model: detail.backup_model,
      llm_type: detail.llm_type,
      config_list: detail.config_list ?? [],
    }
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load model details')
  }
}

const rules: FormRules = {
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  base_model: [{ required: true, message: 'Base model is required', trigger: 'blur' }],
  api_domain: [{ required: true, message: 'API domain is required', trigger: 'blur' }],
  api_key: [{ required: true, message: 'API key is required', trigger: 'blur' }],
}

const supplierOptions = Object.entries(SupplierLabels).map(([value, label]) => ({
  label,
  value: Number(value),
}))

const protocolOptions = Object.entries(ProtocolLabels).map(([value, label]) => ({
  label,
  value: Number(value),
}))

function handleClose() {
  emit('update:visible', false)
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    if (isEdit.value && props.model) {
      await aiModelService.updateModel({
        id: props.model.id,
        ...formValue.value,
      })
      message.success('Model updated')
    } else {
      await aiModelService.createModel(formValue.value)
      message.success('Model created')
    }
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Operation failed')
  } finally {
    loading.value = false
  }
}

function createConfigItem(): AiModelConfigItem {
  return { key: '', val: '', name: '' }
}

async function handleTest() {
  // Validate required fields for test
  if (!formValue.value.base_model || !formValue.value.api_domain || !formValue.value.api_key) {
    message.warning('Please fill in Base Model, API Domain and API Key first')
    return
  }

  testing.value = true
  testResult.value = ''
  testError.value = ''
  testSuccess.value = false

  try {
    await aiModelService.testLlmStatus(formValue.value, (result) => {
      if (result.error) {
        testError.value = result.error
      } else if (result.content) {
        testResult.value += result.content
      }
    })
    // If no error occurred, mark as success
    if (!testError.value) {
      testSuccess.value = true
      message.success('Connection test successful')
    }
  } catch (err) {
    testError.value = err instanceof Error ? err.message : 'Test failed'
    message.error(testError.value)
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <NModal
    :show="visible"
    :mask-closable="false"
    preset="card"
    :title="modalTitle"
    class="!w-[600px] !max-w-[90vw]"
    :bordered="false"
    :segmented="{ content: true }"
    @update:show="handleClose"
  >
    <NForm
      ref="formRef"
      :model="formValue"
      :rules="rules"
      label-placement="left"
      label-width="120"
      require-mark-placement="right-hanging"
    >
      <NFormItem label="Name" path="name">
        <NInput v-model:value="formValue.name" placeholder="Model name" />
      </NFormItem>
      <NFormItem label="Base Model" path="base_model">
        <NInput v-model:value="formValue.base_model" placeholder="e.g. gpt-4o" />
      </NFormItem>
      <NFormItem label="Supplier" path="supplier">
        <NSelect v-model:value="formValue.supplier" :options="supplierOptions" />
      </NFormItem>
      <NFormItem label="Protocol" path="protocol">
        <NSelect v-model:value="formValue.protocol" :options="protocolOptions" />
      </NFormItem>
      <NFormItem label="API Domain" path="api_domain">
        <NInput v-model:value="formValue.api_domain" placeholder="https://api.openai.com" />
      </NFormItem>
      <NFormItem label="API Key" path="api_key">
        <NInput
          v-model:value="formValue.api_key"
          type="password"
          show-password-on="click"
          placeholder="sk-..."
        />
      </NFormItem>
      <NFormItem label="LLM Type" path="llm_type">
        <NRadioGroup v-model:value="formValue.llm_type">
          <NRadio value="chat">Chat</NRadio>
          <NRadio value="embedding">Embedding</NRadio>
        </NRadioGroup>
      </NFormItem>
      <NFormItem label="Default Model">
        <NSwitch v-model:value="formValue.default_model" />
      </NFormItem>
      <NFormItem label="Backup Model">
        <NSwitch v-model:value="formValue.backup_model" />
      </NFormItem>
      <NFormItem label="Config">
        <NDynamicInput
          v-model:value="formValue.config_list"
          :on-create="createConfigItem"
        >
          <template #default="{ value: item }">
            <div class="flex w-full gap-2">
              <NInput v-model:value="(item as AiModelConfigItem).key" placeholder="Key" class="w-1/3" />
              <NInput v-model:value="(item as AiModelConfigItem).name" placeholder="Display Name" class="w-1/3" />
              <NInput v-model:value="(item as AiModelConfigItem).val as string" placeholder="Value" class="w-1/3" />
            </div>
          </template>
        </NDynamicInput>
      </NFormItem>

      <!-- Test Connection -->
      <NFormItem label="Test">
        <div class="w-full">
          <NButton :loading="testing" @click="handleTest">
            Test Connection
          </NButton>

          <!-- Testing spinner -->
          <div v-if="testing" class="mt-3 flex items-center gap-2">
            <NSpin size="small" />
            <NText depth="3">Testing connection, please wait...</NText>
            <NText v-if="testResult" type="info" class="ml-2">{{ testResult }}</NText>
          </div>

          <!-- Success result -->
          <NAlert v-else-if="testSuccess" type="success" class="mt-3" title="Connection Successful">
            <template v-if="testResult">LLM Response: {{ testResult }}</template>
            <template v-else>API connection verified successfully.</template>
          </NAlert>

          <!-- Error result -->
          <NAlert v-else-if="testError" type="error" class="mt-3" title="Connection Failed">
            {{ testError }}
          </NAlert>
        </div>
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Cancel</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">
          {{ isEdit ? 'Update' : 'Create' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
