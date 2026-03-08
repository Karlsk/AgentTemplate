<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  NModal,
  NForm,
  NFormItem,
  NInput,
  NButton,
  NSpace,
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import workspaceService from '@/services/workspace.service'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const defaultFormValue = () => ({
  name: '',
  description: '',
})

const formValue = ref(defaultFormValue())

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      formValue.value = defaultFormValue()
    }
  },
)

const rules: FormRules = {
  name: [
    { required: true, message: 'Name is required', trigger: 'blur' },
    { min: 1, max: 100, message: 'Name must be 1-100 characters', trigger: 'blur' },
  ],
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
    await workspaceService.createWorkspace({
      name: formValue.value.name,
      description: formValue.value.description || undefined,
    })
    message.success('Workspace created successfully')
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to create workspace')
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
    title="New Workspace"
    class="!w-[500px] !max-w-[90vw]"
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
        <NInput v-model:value="formValue.name" placeholder="Workspace name" />
      </NFormItem>
      <NFormItem label="Description" path="description">
        <NInput
          v-model:value="formValue.description"
          type="textarea"
          placeholder="Optional description"
          :rows="3"
        />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Cancel</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">
          Create
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
