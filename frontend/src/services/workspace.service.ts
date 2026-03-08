import http from '@/lib/axios'
import type { Workspace, WorkspaceCreatePayload, WorkspaceUser, WorkspaceUserAddPayload } from '@/types/workspace'

const workspaceService = {
    async listWorkspaces(): Promise<Workspace[]> {
        return http.get('/auth/workspaces')
    },

    async getWorkspaceById(id: number): Promise<Workspace> {
        return http.get(`/auth/workspaces/${id}`)
    },

    async createWorkspace(payload: WorkspaceCreatePayload): Promise<Workspace> {
        return http.post('/auth/workspaces', payload)
    },

    async deleteWorkspace(id: number): Promise<void> {
        return http.delete(`/auth/workspaces/${id}`)
    },

    async getWorkspaceUsers(workspaceId: number): Promise<WorkspaceUser[]> {
        return http.get(`/auth/workspaces/${workspaceId}/users`)
    },

    async addUsersToWorkspace(workspaceId: number, payload: WorkspaceUserAddPayload): Promise<WorkspaceUser[]> {
        return http.post(`/auth/workspaces/${workspaceId}/users`, payload)
    },

    async removeUserFromWorkspace(workspaceId: number, userId: number): Promise<void> {
        return http.delete(`/auth/workspaces/${workspaceId}/users/${userId}`)
    },

    async getUserWorkspaces(userId: number): Promise<WorkspaceUser[]> {
        return http.get(`/auth/users/${userId}/workspaces`)
    },
}

export default workspaceService
