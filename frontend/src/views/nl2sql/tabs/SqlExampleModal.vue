<script setup lang="ts">
import { ref } from 'vue'
import { NModal, NForm, NFormItem, NInput, NButton, NSpace, useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import nl2sqlService from '@/services/nl2sql.service'

const props = defineProps<{
  visible: boolean
  instanceId: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const form = ref({
  question: '',
  sql_text: '',
})

const rules: FormRules = {
  question: { required: true, message: 'Question is required' },
  sql_text: { required: true, message: 'SQL is required' },
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    await nl2sqlService.addQuestionSQL(props.instanceId, {
      question: form.value.question,
      sql_text: form.value.sql_text,
    })
    message.success('SQL example added')
    form.value = { question: '', sql_text: '' }
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to add')
  } finally {
    submitting.value = false
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
    title="Add SQL Example"
    style="width: 600px"
    :mask-closable="false"
    @update:show="handleClose"
  >
    <NForm ref="formRef" :model="form" :rules="rules" label-placement="top">
      <NFormItem label="Natural Language Question" path="question">
        <NInput
          v-model:value="form.question"
          type="textarea"
          placeholder="e.g., How many orders were placed last month?"
          :rows="2"
        />
      </NFormItem>

      <NFormItem label="SQL Query" path="sql_text">
        <NInput
          v-model:value="form.sql_text"
          type="textarea"
          placeholder="SELECT COUNT(*) FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
          :rows="4"
          class="font-mono"
        />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Cancel</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          Add
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
