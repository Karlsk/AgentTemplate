<script setup lang="ts">
import { h, ref, watch, computed } from 'vue'
import {
  NModal,
  NButton,
  NSpace,
  NDataTable,
  NEmpty,
  NSpin,
  NAlert,
  NInput,
  NText,
  NTag,
  NCard,
  NCollapse,
  NCollapseItem,
  NCode,
  NDivider,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import mcpServerService from '@/services/mcpServer.service'
import type { McpServerGridItem, ToolInfo, ToolCallResponse } from '@/types/mcpServer'

const props = defineProps<{
  visible: boolean
  server: McpServerGridItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const message = useMessage()
const loadingTools = ref(false)
const tools = ref<ToolInfo[]>([])

const callingTool = ref(false)
const callResult = ref<ToolCallResponse | null>(null)
const selectedTool = ref<ToolInfo | null>(null)
const toolArguments = ref('')

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.server) {
      fetchTools()
    } else {
      tools.value = []
      callResult.value = null
      selectedTool.value = null
      toolArguments.value = ''
    }
  },
)

async function fetchTools() {
  if (!props.server) return
  loadingTools.value = true
  tools.value = []
  try {
    tools.value = await mcpServerService.getServerTools(props.server.id)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load tools')
  } finally {
    loadingTools.value = false
  }
}

function selectTool(tool: ToolInfo) {
  selectedTool.value = tool
  callResult.value = null
  if (tool.args_schema?.properties) {
    const template: Record<string, string> = {}
    for (const key of Object.keys(tool.args_schema.properties as Record<string, unknown>)) {
      template[key] = ''
    }
    toolArguments.value = JSON.stringify(template, null, 2)
  } else {
    toolArguments.value = '{}'
  }
}

async function callTool() {
  if (!props.server || !selectedTool.value) return

  let args: Record<string, unknown>
  try {
    args = JSON.parse(toolArguments.value || '{}')
  } catch {
    message.error('Arguments must be valid JSON')
    return
  }

  callingTool.value = true
  callResult.value = null
  try {
    callResult.value = await mcpServerService.callTool(props.server.id, {
      tool_name: selectedTool.value.name,
      arguments: args,
    })
    if (callResult.value.ok) {
      message.success(`Tool executed in ${callResult.value.elapsed_ms?.toFixed(0) ?? '?'}ms`)
    }
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Tool call failed')
  } finally {
    callingTool.value = false
  }
}

function handleClose() {
  emit('update:visible', false)
}

function formatResult(result: unknown): string {
  if (result === null || result === undefined) return 'null'
  if (typeof result === 'string') return result
  return JSON.stringify(result, null, 2)
}

const columns = computed<DataTableColumns<ToolInfo>>(() => [
  {
    title: 'Tool Name',
    key: 'name',
    width: 180,
    render(row) {
      const isSelected = selectedTool.value?.name === row.name
      return h('span', {
        style: {
          fontWeight: isSelected ? '600' : '400',
          color: isSelected ? 'var(--primary-color)' : undefined,
        },
      }, row.name)
    },
  },
  {
    title: 'Description',
    key: 'description',
    ellipsis: { tooltip: true },
  },
  {
    title: '',
    key: 'actions',
    width: 80,
    render(row) {
      const isSelected = selectedTool.value?.name === row.name
      return h(
        NButton,
        {
          size: 'small',
          type: isSelected ? 'primary' : 'default',
          secondary: !isSelected,
          onClick: () => selectTool(row),
        },
        { default: () => 'Call' },
      )
    },
  },
])
</script>

<template>
  <NModal
    :show="visible"
    :mask-closable="false"
    preset="card"
    :title="`Tools - ${server?.name ?? ''}`"
    class="!w-[860px] !max-w-[90vw]"
    :bordered="false"
    :segmented="{ content: true }"
    @update:show="handleClose"
  >
    <!-- Loading -->
    <div v-if="loadingTools" class="flex items-center justify-center py-12">
      <NSpin size="medium" />
      <NText depth="3" class="ml-3">Loading tools from server...</NText>
    </div>

    <!-- No tools -->
    <NEmpty v-else-if="tools.length === 0" description="No tools available on this server" class="py-8" />

    <!-- Tools list -->
    <div v-else>
      <NDataTable
        :columns="columns"
        :data="tools"
        :bordered="false"
        :single-line="false"
        :max-height="280"
        striped
        size="small"
      />

      <!-- Tool Call Panel -->
      <template v-if="selectedTool">
        <NDivider style="margin: 16px 0 12px" />

        <NCard
          size="small"
          :bordered="true"
          :segmented="{ content: true }"
          style="background: var(--card-color)"
        >
          <template #header>
            <NSpace align="center" :size="8">
              <NTag type="primary" size="small" round>{{ selectedTool.name }}</NTag>
              <NText depth="3" style="font-size: 13px">{{ selectedTool.description }}</NText>
            </NSpace>
          </template>

          <!-- Args Schema -->
          <NCollapse v-if="selectedTool.args_schema" style="margin-bottom: 12px">
            <NCollapseItem title="Arguments Schema" name="schema">
              <NCode
                :code="JSON.stringify(selectedTool.args_schema, null, 2)"
                language="json"
                style="font-size: 12px"
              />
            </NCollapseItem>
          </NCollapse>

          <!-- Arguments Input -->
          <div style="margin-bottom: 12px">
            <NText depth="2" style="font-size: 13px; display: block; margin-bottom: 4px">
              Arguments (JSON)
            </NText>
            <NInput
              v-model:value="toolArguments"
              type="textarea"
              placeholder="{}"
              :autosize="{ minRows: 2, maxRows: 8 }"
              style="font-family: monospace"
            />
          </div>

          <!-- Call Button -->
          <NButton
            type="primary"
            :loading="callingTool"
            @click="callTool"
          >
            {{ callingTool ? 'Calling...' : 'Call Tool' }}
          </NButton>

          <!-- Result Display -->
          <template v-if="callResult">
            <NDivider style="margin: 12px 0" />

            <!-- Success -->
            <NAlert
              v-if="callResult.ok"
              type="success"
              style="margin: 0"
            >
              <template #header>
                <NSpace align="center" :size="8">
                  <span>Execution Succeeded</span>
                  <NTag size="tiny" round :bordered="false">
                    {{ callResult.elapsed_ms?.toFixed(0) ?? '?' }} ms
                  </NTag>
                </NSpace>
              </template>
              <NCode
                :code="formatResult(callResult.result)"
                language="json"
                style="font-size: 12px; max-height: 300px; overflow: auto"
              />
            </NAlert>

            <!-- Error -->
            <NAlert
              v-else
              type="error"
              title="Execution Failed"
              style="margin: 0"
            >
              <NCode
                :code="callResult.error ?? 'Unknown error'"
                language="text"
                style="font-size: 12px"
              />
            </NAlert>
          </template>
        </NCard>
      </template>
    </div>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Close</NButton>
        <NButton @click="fetchTools" :loading="loadingTools">Refresh</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
