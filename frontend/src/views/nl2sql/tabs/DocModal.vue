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
  content: '',
})

const rules: FormRules = {
  content: { required: true, message: 'Content is required' },
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    await nl2sqlService.addDocumentation(props.instanceId, {
      content: form.value.content,
    })
    message.success('Documentation added')
    form.value = { content: '' }
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
    title="Add Documentation"
    style="width: 600px"
    :mask-closable="false"
    @update:show="handleClose"
  >
    <NForm ref="formRef" :model="form" :rules="rules" label-placement="top">
      <NFormItem label="Documentation Content" path="content">
        <NInput
          v-model:value="form.content"
          type="textarea"
          placeholder="Enter business glossary, terminology definitions, or domain knowledge that helps understand the database context..."
          :rows="6"
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
