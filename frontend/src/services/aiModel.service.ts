import http from '@/lib/axios'
import type { AiModel, AiModelCreatePayload, AiModelUpdatePayload } from '@/types/aiModel'

export interface TestLlmResult {
    content?: string
    error?: string
}

const aiModelService = {
    async listModels(keyword?: string): Promise<AiModel[]> {
        const params = keyword ? { keyword } : {}
        return http.get('/system/aimodel', { params })
    },

    async getModelById(id: number): Promise<AiModelUpdatePayload> {
        return http.get(`/system/aimodel/${id}`)
    },

    async createModel(payload: AiModelCreatePayload): Promise<AiModel> {
        return http.post('/system/aimodel', payload)
    },

    async updateModel(payload: AiModelUpdatePayload): Promise<AiModel> {
        return http.put('/system/aimodel', payload)
    },

    async deleteModel(id: number): Promise<void> {
        return http.delete(`/system/aimodel/${id}`)
    },

    async getDefaultModel(): Promise<AiModel | null> {
        return http.get('/system/aimodel/default')
    },

    async getBackupModel(): Promise<AiModel | null> {
        return http.get('/system/aimodel/backup')
    },

    async setDefaultModel(id: number): Promise<void> {
        return http.put(`/system/aimodel/default/${id}`)
    },

    async setBackupModel(id: number): Promise<void> {
        return http.put(`/system/aimodel/backup/${id}`)
    },

    async testLlmStatus(
        payload: AiModelCreatePayload,
        onChunk: (result: TestLlmResult) => void,
    ): Promise<void> {
        const token = localStorage.getItem('token')
        const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
        const response = await fetch(`${baseURL}/system/aimodel/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(payload),
        })

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() ?? ''

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const result: TestLlmResult = JSON.parse(line)
                        onChunk(result)
                    } catch {
                        // ignore parse errors
                    }
                }
            }
        }

        // Process remaining buffer
        if (buffer.trim()) {
            try {
                const result: TestLlmResult = JSON.parse(buffer)
                onChunk(result)
            } catch {
                // ignore
            }
        }
    },
}

export default aiModelService
