<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NSpace, NTag, NSwitch, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import TableSkeleton from '@/components/skeleton/TableSkeleton.vue'
import UserModal from './UserModal.vue'
import userService from '@/services/user.service'
import workspaceService from '@/services/workspace.service'
import type { User } from '@/types/user'
import type { Workspace } from '@/types/workspace'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const users = ref<User[]>([])
const workspaces = ref<Workspace[]>([])
const updatingStatus = ref<number | null>(null)

const modalVisible = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const [usersRes, workspacesRes] = await Promise.all([
      userService.listUsers(),
      workspaceService.listWorkspaces(),
    ])
    users.value = usersRes
    workspaces.value = workspacesRes
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load data')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  modalVisible.value = true
}

function handleModalSuccess() {
  modalVisible.value = false
  fetchData()
}

function getWorkspaceName(oid: number): string {
  const ws = workspaces.value.find((w) => w.id === oid)
  return ws?.name ?? `Workspace #${oid}`
}

async function toggleStatus(user: User) {
  const newStatus = user.status === 1 ? 0 : 1
  updatingStatus.value = user.id
  try {
    await userService.updateUserStatus({ id: user.id, status: newStatus })
    user.status = newStatus
    message.success(`User ${newStatus === 1 ? 'activated' : 'deactivated'}`)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to update status')
  } finally {
    updatingStatus.value = null
  }
}

function confirmDelete(user: User) {
  dialog.warning({
    title: 'Delete User',
    content: `Are you sure you want to delete "${user.email}"? This action cannot be undone.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: async () => {
      try {
        await userService.deleteUser(user.id)
        message.success('User deleted')
        fetchData()
      } catch (err) {
        message.error(err instanceof Error ? err.message : 'Failed to delete user')
      }
    },
  })
}

const columns: DataTableColumns<User> = [
  {
    title: 'ID',
    key: 'id',
    width: 80,
  },
  {
    title: 'Email',
    key: 'email',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Workspace',
    key: 'oid',
    width: 150,
    render(row) {
      return h(NTag, { size: 'small', round: true }, { default: () => getWorkspaceName(row.oid) })
    },
  },
  {
    title: 'Status',
    key: 'status',
    width: 100,
    render(row) {
      return h(NSwitch, {
        value: row.status === 1,
        loading: updatingStatus.value === row.id,
        disabled: row.email === 'dms@admin.com',
        onUpdateValue: () => toggleStatus(row),
      })
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
    width: 100,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
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
    <PageHeader title="User Management" subtitle="Manage user accounts">
      <template #actions>
        <NButton type="primary" @click="openCreateModal">
          + New User
        </NButton>
      </template>
    </PageHeader>

    <TableSkeleton v-if="loading" :rows="5" :cols="5" />
    <BentoCard v-else>
      <NDataTable
        :columns="columns"
        :data="users"
        :bordered="false"
        :single-line="false"
        striped
      />
    </BentoCard>

    <UserModal
      v-model:visible="modalVisible"
      :workspaces="workspaces"
      @success="handleModalSuccess"
    />
  </div>
</template>
