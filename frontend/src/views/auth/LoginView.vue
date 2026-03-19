<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import authService from '@/services/auth.service'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const formValue = ref({
  email: '',
  password: '',
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    const res = await authService.login(formValue.value.email, formValue.value.password)
    authStore.setAuth(res)
    message.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Login failed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen">
    <!-- Left Brand Panel -->
    <div class="hidden w-1/2 items-center justify-center bg-gradient-to-br from-blue-500 to-blue-700 lg:flex">
      <div class="max-w-md px-8 text-center text-white">
        <div class="mb-6 flex justify-center">
          <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 text-3xl font-bold backdrop-blur-sm">
            A
          </div>
        </div>
        <h1 class="mb-4 text-4xl font-bold">Agent编排系统</h1>
        <p class="text-lg leading-relaxed text-blue-100">
          智能AI Agent平台，提供强大的工作流编排与实时分析能力。
        </p>
      </div>
    </div>

    <!-- Right Login Form -->
    <div class="flex w-full items-center justify-center bg-(--color-page-bg) p-8 dark:bg-(--color-page-bg-dark) lg:w-1/2">
      <div class="w-full max-w-md">
        <!-- Mobile Logo -->
        <div class="mb-8 text-center lg:hidden">
          <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-primary) text-xl font-bold text-white">
            A
          </div>
          <h1 class="text-2xl font-bold text-(--color-text-primary) dark:text-(--color-text-primary-dark)">Agent编排系统</h1>
        </div>

        <div class="bento-card">
          <h2 class="mb-2 text-xl font-semibold text-(--color-text-primary) dark:text-(--color-text-primary-dark)">
            Welcome back
          </h2>
          <p class="mb-6 text-sm text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
            Sign in to your account
          </p>

          <NForm ref="formRef" :model="formValue" :rules="rules" label-placement="top" size="large">
            <NFormItem label="Email" path="email">
              <NInput
                v-model:value="formValue.email"
                placeholder="Enter your email"
                @keydown.enter="handleSubmit"
              />
            </NFormItem>
            <NFormItem label="Password" path="password">
              <NInput
                v-model:value="formValue.password"
                type="password"
                show-password-on="click"
                placeholder="Enter your password"
                @keydown.enter="handleSubmit"
              />
            </NFormItem>
            <NButton
              type="primary"
              block
              strong
              :loading="loading"
              class="!mt-2"
              @click="handleSubmit"
            >
              登录
            </NButton>
          </NForm>
        </div>
      </div>
    </div>
  </div>
</template>
