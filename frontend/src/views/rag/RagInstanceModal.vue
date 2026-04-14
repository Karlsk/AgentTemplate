<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NSpace, useMessage } from 'naive-ui'
import type { FormRules } from 'naive-ui'
import type { RagInstance, RagInstanceCreatePayload } from '@/types/rag'
import { ragService } from '@/services/rag.service'
import aiModelService from '@/services/aiModel.service'
import type { AiModel } from '@/types/aiModel'

const props = defineProps<{
  visible: boolean
  instance?: RagInstance | null
}>()

const emit = defineEmits(['update:visible', 'success'])

const message = useMessage()
const loading = ref(false)
const formRef = ref<any>(null)
const embeddingModels = ref<AiModel[]>([])

const formData = ref<RagInstanceCreatePayload>({
  name: '',
  embedding_model_id: 0,
  dimension: 1536,
  config: {}
})

const rules: FormRules = {
  name: { required: true, message: 'Please enter instance name', trigger: 'blur' },
  embedding_model_id: { required: true, message: 'Please select an embedding model', trigger: 'change', type: 'number' as const },
  dimension: { required: true, message: 'Please enter dimension', trigger: 'blur', type: 'number' as const }
}

async function fetchEmbeddingModels() {
  try {
    const models = await aiModelService.listModels()
    embeddingModels.value = models.filter(m => m.llm_type === 'embedding')
  } catch (err) {
    message.error('Failed to load embedding models')
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    if (props.instance) {
      formData.value = {
        name: props.instance.name,
        embedding_model_id: props.instance.embedding_model_id,
        dimension: 1536, // Default or parse from config if stored
        config: props.instance.config ? JSON.parse(props.instance.config) : {}
      }
    } else {
      formData.value = {
        name: '',
        embedding_model_id: embeddingModels.value[0]?.id || 0,
        dimension: 1536,
        config: {}
      }
    }
  }
})

async function handleSubmit() {
  loading.value = true
  try {
    await formRef.value?.validate()
    if (props.instance) {
      // Update not implemented in this simplified modal
      message.info('Update not implemented')
    } else {
      await ragService.createInstance(formData.value)
      message.success('RAG instance created')
    }
    emit('success')
  } catch (err) {
    if (!(err as any).errors) {
      message.error(err instanceof Error ? err.message : 'Failed to save RAG instance')
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchEmbeddingModels)
</script>

<template>
  <NModal
    :show="visible"
    :title="instance ? 'Edit RAG Instance' : 'New RAG Instance'"
    preset="card"
    style="width: 500px"
    @update:show="(val) => emit('update:visible', val)"
  >
    <NForm
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-placement="top"
    >
      <NFormItem label="Name" path="name">
        <NInput v-model:value="formData.name" placeholder="Knowledge Base Name" />
      </NFormItem>
      
      <NFormItem label="Embedding Model" path="embedding_model_id">
        <NSelect
          v-model:value="formData.embedding_model_id"
          :options="embeddingModels.map(m => ({ label: m.name, value: m.id }))"
          placeholder="Select Model"
        />
      </NFormItem>

      <NFormItem label="Vector Dimension" path="dimension">
        <NInputNumber v-model:value="formData.dimension" :min="1" style="width: 100%" />
      </NFormItem>

      <NSpace justify="end">
        <NButton @click="emit('update:visible', false)">Cancel</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">Confirm</NButton>
      </NSpace>
    </NForm>
  </NModal>
</template>
