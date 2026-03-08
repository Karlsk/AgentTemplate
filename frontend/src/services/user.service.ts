import http from '@/lib/axios'
import type { User, UserCreatePayload } from '@/types/user'

export interface ChangePasswordPayload {
    password: string
    new_password: string
}

export interface UpdateUserStatusPayload {
    id: number
    status: number
}

const userService = {
    async listUsers(): Promise<User[]> {
        return http.get('/auth/users')
    },

    async getUserByEmail(email: string): Promise<User> {
        return http.get('/auth/users/by-email', { params: { email } })
    },

    async createUser(payload: UserCreatePayload): Promise<User> {
        return http.post('/auth/register', payload)
    },

    async deleteUser(userId: number): Promise<void> {
        return http.delete(`/auth/users/${userId}`)
    },

    async changePassword(payload: ChangePasswordPayload): Promise<{ message: string }> {
        return http.patch('/auth/users/me/password', payload)
    },

    async updateUserStatus(payload: UpdateUserStatusPayload): Promise<{ message: string; user_id: number; status: number }> {
        return http.patch('/auth/users/status', payload)
    },
}

export default userService
