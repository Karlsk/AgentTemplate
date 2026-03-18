<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NInputNumber,
  NButton,
  NSpace,
  NSwitch,
  NSlider,
  NDivider,
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import ragService from '@/services/rag.service'
import aiModelService from '@/services/aiModel.service'
import type { KnowledgeBaseListItem } from '@/types/rag'
import type { AiModel } from '@/types/aiModel'

const props = defineProps<{
  visible: boolean
  kb: KnowledgeBaseListItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const isEdit = computed(() => !!props.kb)
const modalTitle = computed(() => (isEdit.value ? 'Edit Knowledge Base' : 'New Knowledge Base'))

const embeddingModels = ref<AiModel[]>([])

const defaultFormValue = () => ({
  name: '',
  description: '',
  embedding_model_id: null as number | null,
  chunk_method: 'naive',
  chunk_size: 512,
  chunk_overlap: 64,
  retrieval_mode: 'hybrid',
  semantic_weight: 0.7,
  keyword_weight: 0.3,
  default_top_k: 5,
  enable_score_threshold: false,
  default_score_threshold: 0.0,
})

const formValue = ref(defaultFormValue())

async function loadEmbeddingModels() {
  try {
    const models = await aiModelService.listModels()
    embeddingModels.value = models.filter((m) => m.llm_type === 'embedding')
  } catch {
    // Silently fail - embedding model selection is optional
  }
}

watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      await loadEmbeddingModels()
      if (props.kb) {
        loadKbForEdit(props.kb)
      } else {
        formValue.value = defaultFormValue()
      }
    }
  },
)

async function loadKbForEdit(kb: KnowledgeBaseListItem) {
  try {
    const detail = await ragService.getKnowledgeBase(kb.id)
    formValue.value = {
      name: detail.name,
      description: detail.description,
      embedding_model_id: detail.embedding_model_id,
      chunk_method: detail.chunk_method,
      chunk_size: detail.chunk_size,
      chunk_overlap: detail.chunk_overlap,
      retrieval_mode: detail.retrieval_mode,
      semantic_weight: detail.semantic_weight,
      keyword_weight: detail.keyword_weight,
      default_top_k: detail.default_top_k,
      enable_score_threshold: detail.enable_score_threshold,
      default_score_threshold: detail.default_score_threshold,
    }
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load knowledge base details')
  }
}

const rules: FormRules = {
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
}

const chunkMethodOptions = [
  { label: 'Naive', value: 'naive' },
  { label: 'Sentence', value: 'sentence' },
  { label: 'Token', value: 'token' },
  { label: 'Delimiter', value: 'delimiter' },
]

const retrievalModeOptions = [
  { label: 'Hybrid (Vector + Keyword)', value: 'hybrid' },
  { label: 'Vector (Pure Semantic)', value: 'vector' },
]

const embeddingModelOptions = computed(() =>
  embeddingModels.value.map((m) => ({
    label: `${m.name} (${m.base_model})`,
    value: m.id,
  })),
)

const isHybridMode = computed(() => formValue.value.retrieval_mode === 'hybrid')

function handleSemanticWeightChange(val: number) {
  formValue.value.semantic_weight = val
  formValue.value.keyword_weight = Math.round((1 - val) * 100) / 100
}

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
    if (isEdit.value && props.kb) {
      await ragService.updateKnowledgeBase({
        id: props.kb.id,
        ...formValue.value,
      })
      message.success('Knowledge base updated')
    } else {
      await ragService.createKnowledgeBase(formValue.value)
      message.success('Knowledge base created')
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
    class="!w-[620px] !max-w-[90vw]"
    :bordered="false"
    :segmented="{ content: true }"
    @update:show="handleClose"
  >
    <NForm
      ref="formRef"
      :model="formValue"
      :rules="rules"
      label-placement="left"
      label-width="160"
      require-mark-placement="right-hanging"
    >
      <NFormItem label="Name" path="name">
        <NInput v-model:value="formValue.name" placeholder="Knowledge base name" />
      </NFormItem>
      <NFormItem label="Description" path="description">
        <NInput
          v-model:value="formValue.description"
          type="textarea"
          placeholder="Optional description"
          :autosize="{ minRows: 2, maxRows: 4 }"
        />
      </NFormItem>
      <NFormItem label="Embedding Model" path="embedding_model_id">
        <NSelect
          v-model:value="formValue.embedding_model_id"
          :options="embeddingModelOptions"
          placeholder="Use system default"
          clearable
        />
      </NFormItem>

      <NDivider title-placement="left">
        Chunking Configuration
      </NDivider>

      <NFormItem label="Chunk Method" path="chunk_method">
        <NSelect v-model:value="formValue.chunk_method" :options="chunkMethodOptions" />
      </NFormItem>
      <NFormItem label="Chunk Size" path="chunk_size">
        <NInputNumber
          v-model:value="formValue.chunk_size"
          :min="64"
          :max="4096"
          :step="64"
          class="w-full"
        />
      </NFormItem>
      <NFormItem label="Chunk Overlap" path="chunk_overlap">
        <NInputNumber
          v-model:value="formValue.chunk_overlap"
          :min="0"
          :max="512"
          :step="16"
          class="w-full"
        />
      </NFormItem>

      <NDivider title-placement="left">
        Retrieval Configuration
      </NDivider>

      <NFormItem label="Retrieval Mode" path="retrieval_mode">
        <NSelect v-model:value="formValue.retrieval_mode" :options="retrievalModeOptions" />
      </NFormItem>
      <NFormItem v-if="isHybridMode" label="Semantic Weight" path="semantic_weight">
        <div class="w-full">
          <NSlider
            :value="formValue.semantic_weight"
            :min="0"
            :max="1"
            :step="0.05"
            :tooltip="true"
            @update:value="handleSemanticWeightChange"
          />
          <div class="mt-1 flex justify-between text-xs text-(--color-text-secondary)">
            <span>Keyword: {{ formValue.keyword_weight }}</span>
            <span>Semantic: {{ formValue.semantic_weight }}</span>
          </div>
        </div>
      </NFormItem>
      <NFormItem label="Default Top K" path="default_top_k">
        <NInputNumber
          v-model:value="formValue.default_top_k"
          :min="1"
          :max="50"
          class="w-full"
        />
      </NFormItem>
      <NFormItem label="Score Threshold" path="enable_score_threshold">
        <NSpace align="center" :size="12">
          <NSwitch v-model:value="formValue.enable_score_threshold" />
          <NInputNumber
            v-if="formValue.enable_score_threshold"
            v-model:value="formValue.default_score_threshold"
            :min="0"
            :max="1"
            :step="0.05"
            size="small"
            style="width: 120px"
          />
        </NSpace>
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
