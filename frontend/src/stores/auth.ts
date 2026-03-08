import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { UserInfo, LoginResponse, JwtPayload } from '@/types/auth'

function decodeJwtPayload(token: string): JwtPayload | null {
    try {
        const base64 = token.split('.')[1]
        if (!base64) return null
        const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
        return JSON.parse(json)
    } catch {
        return null
    }
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<UserInfo | null>(
        (() => {
            const stored = localStorage.getItem('user')
            return stored ? JSON.parse(stored) : null
        })(),
    )

    const isAuthenticated = computed(() => !!token.value)
    const isAdmin = computed(() => {
        return !!user.value && user.value.email === 'dms@admin.com'
    })

    function setAuth(loginRes: LoginResponse) {
        token.value = loginRes.access_token
        const payload = decodeJwtPayload(loginRes.access_token)
        user.value = payload?.user ?? { id: 0, email: '', oid: 0, status: 0 }
        localStorage.setItem('token', token.value)
        localStorage.setItem('user', JSON.stringify(user.value))
    }

    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('sessionId')
    }

    return {
        token,
        user,
        isAuthenticated,
        isAdmin,
        setAuth,
        logout,
    }
})
