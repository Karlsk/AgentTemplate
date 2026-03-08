<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NButton, NSpace, useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import userService from '@/services/user.service'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const formModel = ref({
  password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  password: [
    { required: true, message: 'Please enter current password', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: 'Please enter new password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: 'Please confirm new password', trigger: 'blur' },
    {
      validator: (_rule, value: string) => {
        if (value !== formModel.value.new_password) {
          return new Error('Passwords do not match')
        }
        return true
      },
      trigger: 'blur',
    },
  ],
}

watch(() => props.visible, (val) => {
  if (val) {
    formModel.value = { password: '', new_password: '', confirm_password: '' }
  }
})

function close() {
  emit('update:visible', false)
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    await userService.changePassword({
      password: formModel.value.password,
      new_password: formModel.value.new_password,
    })
    message.success('Password changed successfully')
    emit('success')
    close()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to change password')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <NModal
    :show="visible"
    preset="card"
    title="Change Password"
    style="width: 400px"
    :mask-closable="false"
    @update:show="emit('update:visible', $event)"
  >
    <NForm
      ref="formRef"
      :model="formModel"
      :rules="rules"
      label-placement="top"
    >
      <NFormItem label="Current Password" path="password">
        <NInput
          v-model:value="formModel.password"
          type="password"
          show-password-on="click"
          placeholder="Enter current password"
        />
      </NFormItem>
      <NFormItem label="New Password" path="new_password">
        <NInput
          v-model:value="formModel.new_password"
          type="password"
          show-password-on="click"
          placeholder="Enter new password"
        />
      </NFormItem>
      <NFormItem label="Confirm New Password" path="confirm_password">
        <NInput
          v-model:value="formModel.confirm_password"
          type="password"
          show-password-on="click"
          placeholder="Confirm new password"
        />
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="close">Cancel</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          Change Password
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
