<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NDataTable, NTag, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import McpServerModal from './McpServerModal.vue'
import McpServerToolsModal from './McpServerToolsModal.vue'
import mcpServerService from '@/services/mcpServer.service'
import type { McpServerGridItem } from '@/types/mcpServer'
import { McpTransportLabels, type McpTransport } from '@/types/mcpServer'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const servers = ref<McpServerGridItem[]>([])

const modalVisible = ref(false)
const editingServer = ref<McpServerGridItem | null>(null)

const toolsModalVisible = ref(false)
const toolsServer = ref<McpServerGridItem | null>(null)

async function fetchServers() {
  loading.value = true
  try {
    servers.value = await mcpServerService.listServers()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load MCP servers')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  editingServer.value = null
  modalVisible.value = true
}

function openEditModal(server: McpServerGridItem) {
  editingServer.value = server
  modalVisible.value = true
}

function openToolsModal(server: McpServerGridItem) {
  toolsServer.value = server
  toolsModalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchServers()
}

function confirmDelete(server: McpServerGridItem) {
  dialog.warning({
    title: 'Delete MCP Server',
    content: `Are you sure you want to delete "${server.name}"?`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await mcpServerService.deleteServer(server.id)
        message.success('MCP server deleted')
        fetchServers()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete server')
      }
    },
  })
}

const columns: DataTableColumns<McpServerGridItem> = [
  {
    title: 'Name',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', { class: 'font-medium' }, row.name)
    },
  },
  {
    title: 'URL',
    key: 'url',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Transport',
    key: 'transport',
    width: 160,
    render(row) {
      return h(NTag, { size: 'small', type: 'info', round: true }, {
        default: () => McpTransportLabels[row.transport as McpTransport] ?? row.transport,
      })
    },
  },
  {
    title: 'Created At',
    key: 'created_at',
    width: 180,
    render(row) {
      return row.created_at ? new Date(row.created_at).toLocaleString() : '-'
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 280,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => openEditModal(row) }, { default: () => 'Edit' }),
          h(NButton, { size: 'small', secondary: true, type: 'info', onClick: () => openToolsModal(row) }, { default: () => 'Tools' }),
          h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => 'Delete' }),
        ],
      })
    },
  },
]

onMounted(fetchServers)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div>
    <PageHeader title="MCP Servers" subtitle="Manage your MCP server configurations">
      <template #actions>
        <NButton type="primary" @click="openCreateModal">
          + New Server
        </NButton>
      </template>
    </PageHeader>

    <!-- Table -->
    <TableSkeleton v-if="loading" :rows="5" :cols="5" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="servers"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <!-- Create/Edit Modal -->
    <McpServerModal
      v-model:visible="modalVisible"
      :server="editingServer"
      @success="handleModalSuccess"
    />

    <!-- Tools Modal -->
    <McpServerToolsModal
      v-model:visible="toolsModalVisible"
      :server="toolsServer"
    />
  </div>
</template>
