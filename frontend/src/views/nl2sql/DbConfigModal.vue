<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NSpace, useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import nl2sqlService from '@/services/nl2sql.service'
import type { DbConfigListItem, DbConfigCreatePayload } from '@/types/nl2sql'
import { DbTypeOptions } from '@/types/nl2sql'

const props = defineProps<{
  visible: boolean
  config: DbConfigListItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const testing = ref(false)

const isEdit = computed(() => !!props.config)
const title = computed(() => isEdit.value ? 'Edit DB Config' : 'New DB Config')

const form = ref<DbConfigCreatePayload>({
  name: '',
  db_type: 'mysql',
  host: '',
  port: 3306,
  database_name: '',
  schema_name: '',
  username: '',
  password: '',
  extra_params: '',
})

watch(() => props.visible, (val) => {
  if (val) {
    if (props.config) {
      form.value = {
        name: props.config.name,
        db_type: props.config.db_type,
        host: props.config.host,
        port: props.config.port,
        database_name: props.config.database_name,
        schema_name: '',
        username: '',
        password: '',
        extra_params: '',
      }
    } else {
      form.value = {
        name: '',
        db_type: 'mysql',
        host: '',
        port: 3306,
        database_name: '',
        schema_name: '',
        username: '',
        password: '',
        extra_params: '',
      }
    }
  }
})

watch(() => form.value.db_type, (val) => {
  const portMap: Record<string, number> = {
    mysql: 3306,
    postgresql: 5432,
    oracle: 1521,
    sqlserver: 1433,
    clickhouse: 8123,
    dameng: 5236,
    doris: 9030,
    starrocks: 9030,
    kingbase: 54321,
    redshift: 5439,
    elasticsearch: 9200,
  }
  if (portMap[val] && !isEdit.value) {
    form.value.port = portMap[val]
  }
})

const rules: FormRules = {
  name: { required: true, message: 'Name is required' },
  db_type: { required: true, message: 'Database type is required' },
  host: { required: true, message: 'Host is required' },
  port: { required: true, type: 'number', message: 'Port is required' },
  database_name: { required: true, message: 'Database name is required' },
  username: { required: true, message: 'Username is required' },
  password: { required: !isEdit.value, message: 'Password is required' },
}

async function testConnection() {
  testing.value = true
  try {
    const result = await nl2sqlService.testDbConnection({
      db_type: form.value.db_type,
      host: form.value.host,
      port: form.value.port,
      database_name: form.value.database_name,
      schema_name: form.value.schema_name || undefined,
      username: form.value.username,
      password: form.value.password,
      extra_params: form.value.extra_params || undefined,
    })
    if (result.success) {
      message.success(`Connection successful (${result.latency_ms}ms)`)
    } else {
      message.error(`Connection failed: ${result.message}`)
    }
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Test failed')
  } finally {
    testing.value = false
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (isEdit.value && props.config) {
      await nl2sqlService.updateDbConfig({
        id: props.config.id,
        ...form.value,
        password: form.value.password || undefined,
      })
      message.success('DB config updated')
    } else {
      await nl2sqlService.createDbConfig(form.value)
      message.success('DB config created')
    }
    emit('success')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Operation failed')
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
    :title="title"
    style="width: 560px"
    :mask-closable="false"
    @update:show="handleClose"
  >
    <NForm ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="120">
      <NFormItem label="Name" path="name">
        <NInput v-model:value="form.name" placeholder="My Database" />
      </NFormItem>

      <NFormItem label="Database Type" path="db_type">
        <NSelect v-model:value="form.db_type" :options="DbTypeOptions" />
      </NFormItem>

      <NFormItem label="Host" path="host">
        <NInput v-model:value="form.host" placeholder="localhost" />
      </NFormItem>

      <NFormItem label="Port" path="port">
        <NInputNumber v-model:value="form.port" :min="1" :max="65535" style="width: 100%" />
      </NFormItem>

      <NFormItem label="Database" path="database_name">
        <NInput v-model:value="form.database_name" placeholder="mydb" />
      </NFormItem>

      <NFormItem label="Schema">
        <NInput v-model:value="form.schema_name" placeholder="public (optional)" />
      </NFormItem>

      <NFormItem label="Username" path="username">
        <NInput v-model:value="form.username" placeholder="root" />
      </NFormItem>

      <NFormItem label="Password" path="password">
        <NInput v-model:value="form.password" type="password" show-password-on="click" :placeholder="isEdit ? '(unchanged)' : 'Enter password'" />
      </NFormItem>

      <NFormItem label="Extra Params">
        <NInput v-model:value="form.extra_params" placeholder="charset=utf8mb4 (optional)" />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="space-between">
        <NButton secondary :loading="testing" @click="testConnection">
          Test Connection
        </NButton>
        <NSpace>
          <NButton @click="handleClose">Cancel</NButton>
          <NButton type="primary" :loading="submitting" @click="handleSubmit">
            {{ isEdit ? 'Update' : 'Create' }}
          </NButton>
        </NSpace>
      </NSpace>
    </template>
  </NModal>
</template>
