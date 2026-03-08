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
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import userService from '@/services/user.service'
import type { Workspace } from '@/types/workspace'

const props = defineProps<{
  visible: boolean
  workspaces: Workspace[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const defaultFormValue = () => ({
  email: '',
  oid: 1,
  status: 1,
  oid_list: [] as number[],
})

const formValue = ref(defaultFormValue())

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      formValue.value = defaultFormValue()
      if (props.workspaces.length > 0) {
        formValue.value.oid = props.workspaces[0]!.id
      }
    }
  },
)

const rules: FormRules = {
  email: [
    { required: true, message: 'Email is required', trigger: 'blur' },
    { type: 'email', message: 'Invalid email format', trigger: 'blur' },
  ],
  oid: [{ required: true, type: 'number', message: 'Workspace is required', trigger: 'change' }],
}

const workspaceOptions = computed(() =>
  props.workspaces.map((ws) => ({
    label: ws.name,
    value: ws.id,
  })),
)

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
    await userService.createUser({
      email: formValue.value.email,
      oid: formValue.value.oid,
      status: formValue.value.status,
      oid_list: formValue.value.oid_list.length > 0 ? formValue.value.oid_list : undefined,
    })
    message.success('User created successfully')
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to create user')
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
    title="New User"
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
      <NFormItem label="Email" path="email">
        <NInput v-model:value="formValue.email" placeholder="user@example.com" />
      </NFormItem>
      <NFormItem label="Workspace" path="oid">
        <NSelect
          v-model:value="formValue.oid"
          :options="workspaceOptions"
          placeholder="Select workspace"
        />
      </NFormItem>
      <NFormItem label="Status" path="status">
        <NSwitch
          :value="formValue.status === 1"
          @update:value="(v: boolean) => (formValue.status = v ? 1 : 0)"
        >
          <template #checked>Active</template>
          <template #unchecked>Inactive</template>
        </NSwitch>
      </NFormItem>
      <NFormItem label="Multi-Workspace">
        <NSelect
          v-model:value="formValue.oid_list"
          :options="workspaceOptions"
          placeholder="Optional: assign to multiple workspaces"
          multiple
          clearable
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
