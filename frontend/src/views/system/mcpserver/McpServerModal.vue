<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NButton,
  NSpace,
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import mcpServerService from '@/services/mcpServer.service'
import type { McpServerGridItem } from '@/types/mcpServer'
import { McpTransport, McpTransportLabels } from '@/types/mcpServer'

const props = defineProps<{
  visible: boolean
  server: McpServerGridItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const isEdit = computed(() => !!props.server)
const modalTitle = computed(() => (isEdit.value ? 'Edit MCP Server' : 'New MCP Server'))

const defaultFormValue = () => ({
  name: '',
  url: '',
  transport: McpTransport.StreamableHttp as string,
  config: '' as string,
})

const formValue = ref(defaultFormValue())

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.server) {
      loadServerForEdit(props.server)
    } else if (visible) {
      formValue.value = defaultFormValue()
    }
  },
)

async function loadServerForEdit(server: McpServerGridItem) {
  try {
    const detail = await mcpServerService.getServerById(server.id)
    formValue.value = {
      name: detail.name,
      url: detail.url,
      transport: detail.transport,
      config: detail.config ? JSON.stringify(detail.config, null, 2) : '',
    }
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load server details')
  }
}

const rules: FormRules = {
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  url: [{ required: true, message: 'URL is required', trigger: 'blur' }],
  transport: [{ required: true, message: 'Transport is required', trigger: 'change' }],
}

const transportOptions = Object.entries(McpTransportLabels).map(([value, label]) => ({
  label,
  value,
}))

function handleClose() {
  emit('update:visible', false)
}

function parseConfig(configStr: string): Record<string, unknown> | null {
  if (!configStr.trim()) return null
  try {
    return JSON.parse(configStr)
  } catch {
    throw new Error('Config must be valid JSON')
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  let config: Record<string, unknown> | null = null
  try {
    config = parseConfig(formValue.value.config)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Invalid config')
    return
  }

  loading.value = true
  try {
    if (isEdit.value && props.server) {
      await mcpServerService.updateServer({
        id: props.server.id,
        name: formValue.value.name,
        url: formValue.value.url,
        transport: formValue.value.transport,
        config,
      })
      message.success('MCP server updated')
    } else {
      await mcpServerService.createServer({
        name: formValue.value.name,
        url: formValue.value.url,
        transport: formValue.value.transport,
        config,
      })
      message.success('MCP server created')
    }
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Operation failed')
  } finally {
    loading.value = false
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
      label-width="100"
      require-mark-placement="right-hanging"
    >
      <NFormItem label="Name" path="name">
        <NInput v-model:value="formValue.name" placeholder="MCP server name" />
      </NFormItem>
      <NFormItem label="URL" path="url">
        <NInput v-model:value="formValue.url" placeholder="http://localhost:8080/mcp" />
      </NFormItem>
      <NFormItem label="Transport" path="transport">
        <NSelect v-model:value="formValue.transport" :options="transportOptions" />
      </NFormItem>
      <NFormItem label="Config" path="config">
        <NInput
          v-model:value="formValue.config"
          type="textarea"
          placeholder='{"key": "value"}'
          :autosize="{ minRows: 3, maxRows: 10 }"
        />
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
