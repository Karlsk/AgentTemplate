export interface Workspace {
    id: number
    name: string
    description: string
    created_at: string
}

export interface WorkspaceCreatePayload {
    name: string
    description?: string
}

export interface WorkspaceUser {
    id: number
    uid: number
    oid: number
    role: number
    created_at: string
}

export interface WorkspaceUserAddPayload {
    uid_list: number[]
    oid: number
    role: number
}

export const WorkspaceUserRole = {
    Member: 0,
    Admin: 1,
} as const

export const WorkspaceUserRoleLabels: Record<number, string> = {
    [WorkspaceUserRole.Member]: 'Member',
    [WorkspaceUserRole.Admin]: 'Admin',
}
