import axios from 'axios'
import type { ApiResponse } from '@/types/api'
import router from '@/router'

const http = axios.create({
    baseURL: '/api/v1',
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json',
    },
})

http.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    const sessionId = localStorage.getItem('sessionId')
    if (sessionId) {
        config.headers['X-Session-Id'] = sessionId
    }
    return config
})

http.interceptors.response.use(
    (response) => {
        const data = response.data as ApiResponse<unknown>
        if (data.code !== 0) {
            return Promise.reject(new Error(data.msg ?? 'Request failed'))
        }
        return data.data as never
    },
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            router.push('/login')
        }
        const msg =
            error.response?.data?.detail ??
            error.response?.data?.msg ??
            error.message ??
            'Network error'
        return Promise.reject(new Error(msg))
    },
)

export default http
