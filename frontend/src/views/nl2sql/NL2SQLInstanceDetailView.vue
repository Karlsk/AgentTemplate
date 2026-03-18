<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NTabs, NTabPane, NTag, NStatistic, NSpin, useMessage, useDialog } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import SchemaTab from './tabs/SchemaTab.vue'
import SqlExamplesTab from './tabs/SqlExamplesTab.vue'
import DocsTab from './tabs/DocsTab.vue'
import SchemaSyncModal from './SchemaSyncModal.vue'
import SchemaEditModal from './tabs/SchemaEditModal.vue'
import nl2sqlService from '@/services/nl2sql.service'
import type { NL2SQLInstance, SchemaTableInfo } from '@/types/nl2sql'
import { InstanceStatusLabels, DdlModeLabels } from '@/types/nl2sql'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const instanceId = computed(() => Number(route.params.instanceId))
const instance = ref<NL2SQLInstance | null>(null)
const loading = ref(true)
const showSyncModal = ref(false)
const showEditModal = ref(false)
const editingTable = ref<SchemaTableInfo | null>(null)
const activeTab = ref('schema')
const schemaTabRef = ref<InstanceType<typeof SchemaTab> | null>(null)

async function fetchInstance() {
  loading.value = true
  try {
    instance.value = await nl2sqlService.getInstance(instanceId.value)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load instance')
    router.push({ name: 'nl2sql-instance' })
  } finally {
    loading.value = false
  }
}

function confirmDelete() {
  if (!instance.value) return
  dialog.warning({
    title: 'Delete Instance',
    content: `Are you sure you want to delete "${instance.value.name}"? All training data will be permanently removed.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await nl2sqlService.deleteInstance(instanceId.value)
        message.success('Instance deleted')
        router.push({ name: 'nl2sql-instance' })
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete')
      }
    },
  })
}

function getStatusType(status: number): 'default' | 'success' | 'warning' {
  if (status === 1) return 'success'
  if (status === 2) return 'warning'
  return 'default'
}

function handleEditTable(table: SchemaTableInfo) {
  editingTable.value = table
  showEditModal.value = true
}

function handleSchemaChanged() {
  fetchInstance()
  schemaTabRef.value?.fetchSchema()
}

watch(instanceId, () => {
  if (instanceId.value) {
    fetchInstance()
  }
})

onMounted(fetchInstance)
</script>

<template>
  <div>
    <NSpin :show="loading">
      <template v-if="instance">
        <PageHeader :title="instance.name" :subtitle="instance.description || 'NL2SQL Instance'">
          <template #actions>
            <NButton secondary @click="router.push({ name: 'nl2sql-instance' })">
              Back to List
            </NButton>
            <NButton secondary @click="showSyncModal = true">
              Sync Schema
            </NButton>
            <NButton secondary type="error" @click="confirmDelete">
              Delete
            </NButton>
          </template>
        </PageHeader>

        <!-- Stats -->
        <div class="mb-4 grid grid-cols-5 gap-4">
          <BentoCard>
            <NStatistic label="Status">
              <NTag :type="getStatusType(instance.status)" round>
                {{ InstanceStatusLabels[instance.status] }}
              </NTag>
            </NStatistic>
          </BentoCard>
          <BentoCard>
            <NStatistic label="DDL Mode">
              <NTag round>{{ DdlModeLabels[instance.ddl_mode] || instance.ddl_mode }}</NTag>
            </NStatistic>
          </BentoCard>
          <BentoCard>
            <NStatistic label="DDL Entries" :value="instance.ddl_count" />
          </BentoCard>
          <BentoCard>
            <NStatistic label="SQL Examples" :value="instance.sql_count" />
          </BentoCard>
          <BentoCard>
            <NStatistic label="Documentation" :value="instance.doc_count" />
          </BentoCard>
        </div>

        <!-- Tabs -->
        <BentoCard>
          <NTabs v-model:value="activeTab" type="line">
            <NTabPane name="schema" tab="Schema">
              <SchemaTab
                ref="schemaTabRef"
                :instance-id="instanceId"
                @edit="handleEditTable"
                @refresh="fetchInstance"
              />
            </NTabPane>
            <NTabPane name="sql" tab="SQL Examples">
              <SqlExamplesTab :instance-id="instanceId" @refresh="fetchInstance" />
            </NTabPane>
            <NTabPane name="docs" tab="Documentation">
              <DocsTab :instance-id="instanceId" @refresh="fetchInstance" />
            </NTabPane>
          </NTabs>
        </BentoCard>

        <!-- Schema Sync Modal -->
        <SchemaSyncModal
          :visible="showSyncModal"
          :instance-id="instanceId"
          @update:visible="v => showSyncModal = v"
          @success="handleSchemaChanged"
        />

        <!-- Schema Edit Modal -->
        <SchemaEditModal
          :visible="showEditModal"
          :instance-id="instanceId"
          :table-info="editingTable"
          @update:visible="v => showEditModal = v"
          @success="handleSchemaChanged"
        />
      </template>
    </NSpin>
  </div>
</template>
