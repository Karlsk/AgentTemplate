<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NSpace, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import WorkspaceUsersModal from './WorkspaceUsersModal.vue'
import workspaceService from '@/services/workspace.service'
import userService from '@/services/user.service'
import type { Workspace } from '@/types/workspace'
import type { User } from '@/types/user'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const workspaces = ref<Workspace[]>([])
const users = ref<User[]>([])

const createModalVisible = ref(false)
const usersModalVisible = ref(false)
const selectedWorkspace = ref<Workspace | null>(null)

async function fetchData() {
  loading.value = true
  try {
    const [wsRes, usersRes] = await Promise.all([
      workspaceService.listWorkspaces(),
      userService.listUsers(),
    ])
    workspaces.value = wsRes
    users.value = usersRes
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load data')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  createModalVisible.value = true
}

function openUsersModal(workspace: Workspace) {
  selectedWorkspace.value = workspace
  usersModalVisible.value = true
}

function handleCreateSuccess() {
  createModalVisible.value = false
  fetchData()
}

function confirmDelete(workspace: Workspace) {
  dialog.warning({
    title: 'Delete Workspace',
    content: `Are you sure you want to delete "${workspace.name}"? All user relations will also be removed.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await workspaceService.deleteWorkspace(workspace.id)
        message.success('Workspace deleted')
        fetchData()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete workspace')
      }
    },
  })
}

const columns: DataTableColumns<Workspace> = [
  {
    title: 'ID',
    key: 'id',
    width: 80,
  },
  {
    title: 'Name',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', { class: 'font-medium' }, row.name)
    },
  },
  {
    title: 'Description',
    key: 'description',
    ellipsis: { tooltip: true },
    render(row) {
      return row.description || '-'
    },
  },
  {
    title: 'Created',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString()
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 200,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => openUsersModal(row) }, { default: () => 'Users' }),
          h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => 'Delete' }),
        ],
      })
    },
  },
]

onMounted(fetchData)
</script>

<template>
  <div>
    <PageHeader title="Workspace" subtitle="Manage workspaces and team memberships">
      <template #actions>
        <NButton type="primary" @click="openCreateModal">
          + New Workspace
        </NButton>
      </template>
    </PageHeader>

    <TableSkeleton v-if="loading" :rows="5" :cols="4" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="workspaces"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <WorkspaceModal
      v-model:visible="createModalVisible"
      @success="handleCreateSuccess"
    />

    <WorkspaceUsersModal
      v-model:visible="usersModalVisible"
      :workspace="selectedWorkspace"
      :all-users="users"
      @updated="fetchData"
    />
  </div>
</template>
