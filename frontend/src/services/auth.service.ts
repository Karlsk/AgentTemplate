import http from '@/lib/axios'
import type { LoginResponse } from '@/types/auth'

const authService = {
    async login(email: string, password: string): Promise<LoginResponse> {
        const formData = new URLSearchParams()
        formData.append('username', email)
        formData.append('password', password)
        return http.post('/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        })
    },

    async register(payload: { email: string; password: string; oid: number }) {
        return http.post('/auth/register', payload)
    },
}

export default authService
