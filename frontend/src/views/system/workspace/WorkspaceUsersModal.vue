<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  NModal,
  NDataTable,
  NButton,
  NSpace,
  NSelect,
  NTag,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import workspaceService from '@/services/workspace.service'
import type { Workspace, WorkspaceUser } from '@/types/workspace'
import { WorkspaceUserRole, WorkspaceUserRoleLabels } from '@/types/workspace'
import type { User } from '@/types/user'

const props = defineProps<{
  visible: boolean
  workspace: Workspace | null
  allUsers: User[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  updated: []
}>()

const message = useMessage()
const loading = ref(false)
const workspaceUsers = ref<WorkspaceUser[]>([])

const selectedUserId = ref<number | null>(null)
const selectedRole = ref(WorkspaceUserRole.Member)

watch(
  () => props.visible,
  async (visible) => {
    if (visible && props.workspace) {
      await fetchWorkspaceUsers()
    }
  },
)

async function fetchWorkspaceUsers() {
  if (!props.workspace) return
  loading.value = true
  try {
    workspaceUsers.value = await workspaceService.getWorkspaceUsers(props.workspace.id)
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load workspace users')
  } finally {
    loading.value = false
  }
}

function getUserEmail(uid: number): string {
  const user = props.allUsers.find((u) => u.id === uid)
  return user?.email ?? `User #${uid}`
}

const availableUsers = computed(() => {
  const existingUids = new Set(workspaceUsers.value.map((wu) => wu.uid))
  return props.allUsers
    .filter((u) => !existingUids.has(u.id))
    .map((u) => ({ label: u.email, value: u.id }))
})

const roleOptions = [
  { label: 'Member', value: WorkspaceUserRole.Member },
  { label: 'Admin', value: WorkspaceUserRole.Admin },
]

async function addUser() {
  if (!props.workspace || !selectedUserId.value) return
  try {
    await workspaceService.addUsersToWorkspace(props.workspace.id, {
      uid_list: [selectedUserId.value],
      oid: props.workspace.id,
      role: selectedRole.value,
    })
    message.success('User added')
    selectedUserId.value = null
    await fetchWorkspaceUsers()
    emit('updated')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to add user')
  }
}

async function removeUser(wu: WorkspaceUser) {
  if (!props.workspace) return
  try {
    await workspaceService.removeUserFromWorkspace(props.workspace.id, wu.uid)
    message.success('User removed')
    await fetchWorkspaceUsers()
    emit('updated')
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to remove user')
  }
}

function handleClose() {
  emit('update:visible', false)
}

const columns: DataTableColumns<WorkspaceUser> = [
  {
    title: 'User',
    key: 'uid',
    render(row) {
      return getUserEmail(row.uid)
    },
  },
  {
    title: 'Role',
    key: 'role',
    width: 100,
    render(row) {
      const type = row.role === WorkspaceUserRole.Admin ? 'warning' : 'default'
      return h(NTag, { size: 'small', type, round: true }, { default: () => WorkspaceUserRoleLabels[row.role] ?? 'Unknown' })
    },
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 100,
    render(row) {
      return h(NButton, { size: 'small', secondary: true, type: 'error', onClick: () => removeUser(row) }, { default: () => 'Remove' })
    },
  },
]
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <NModal
    :show="visible"
    :mask-closable="true"
    preset="card"
    :title="`Users in ${workspace?.name ?? 'Workspace'}`"
    class="!w-[720px] !max-w-[90vw]"
    :bordered="false"
    :segmented="{ content: true }"
    @update:show="handleClose"
  >
    <!-- Add User Section -->
    <div class="mb-4 flex items-center gap-3">
      <NSelect
        v-model:value="selectedUserId"
        :options="availableUsers"
        placeholder="Select user to add..."
        filterable
        clearable
        style="flex: 1 1 auto; min-width: 300px"
      />
      <NSelect
        v-model:value="selectedRole"
        :options="roleOptions"
        style="width: 100px; flex-shrink: 0"
      />
      <NButton type="primary" class="shrink-0" :disabled="!selectedUserId" @click="addUser">
        Add
      </NButton>
    </div>

    <!-- Users Table -->
    <NDataTable
      :columns="columns"
      :data="workspaceUsers"
      :loading="loading"
      :bordered="false"
      size="small"
    />

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">Close</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
