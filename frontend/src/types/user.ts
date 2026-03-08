export interface User {
    id: number
    email: string
    oid: number
    status: number
    created_at: string
}

export interface UserCreatePayload {
    email: string
    oid: number
    status?: number
    oid_list?: number[]
}

export const UserStatus = {
    Inactive: 0,
    Active: 1,
} as const

export const UserStatusLabels: Record<number, string> = {
    [UserStatus.Inactive]: 'Inactive',
    [UserStatus.Active]: 'Active',
}
