import http from '@/lib/axios'
import type {
    KnowledgeBase,
    KnowledgeBaseListItem,
    KnowledgeBaseCreatePayload,
    KnowledgeBaseUpdatePayload,
    RagDocument,
    RagDocumentListItem,
    DocumentUploadOptions,
    DocumentProgressResponse,
    ChunkPreviewResponse,
    RAGSearchRequest,
    RAGSearchResponse,
} from '@/types/rag'

const ragService = {
    // ==================== Knowledge Base ====================

    async listKnowledgeBases(keyword?: string): Promise<KnowledgeBaseListItem[]> {
        const params = keyword ? { keyword } : {}
        return http.get('/rag/kb', { params })
    },

    async getKnowledgeBase(id: number): Promise<KnowledgeBase> {
        return http.get(`/rag/kb/${id}`)
    },

    async createKnowledgeBase(payload: KnowledgeBaseCreatePayload): Promise<KnowledgeBase> {
        return http.post('/rag/kb', payload)
    },

    async updateKnowledgeBase(payload: KnowledgeBaseUpdatePayload): Promise<KnowledgeBase> {
        return http.put('/rag/kb', payload)
    },

    async deleteKnowledgeBase(id: number): Promise<void> {
        return http.delete(`/rag/kb/${id}`)
    },

    // ==================== Documents ====================

    async listDocuments(kbId: number): Promise<RagDocumentListItem[]> {
        return http.get(`/rag/kb/${kbId}/documents`)
    },

    async uploadDocument(kbId: number, file: File, options?: DocumentUploadOptions): Promise<RagDocument> {
        const formData = new FormData()
        formData.append('file', file)
        if (options?.chunk_method) {
            formData.append('chunk_method', options.chunk_method)
        }
        if (options?.chunk_size != null) {
            formData.append('chunk_size', String(options.chunk_size))
        }
        if (options?.chunk_overlap != null) {
            formData.append('chunk_overlap', String(options.chunk_overlap))
        }
        if (options?.chunk_separator) {
            formData.append('chunk_separator', options.chunk_separator)
        }
        return http.post(`/rag/kb/${kbId}/documents`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120000,
        })
    },

    async deleteDocument(kbId: number, docId: number): Promise<void> {
        return http.delete(`/rag/kb/${kbId}/documents/${docId}`)
    },

    async getDocumentProgress(kbId: number, docId: number): Promise<DocumentProgressResponse> {
        return http.get(`/rag/kb/${kbId}/documents/${docId}/progress`)
    },

    async getDocumentChunks(kbId: number, docId: number, offset = 0, limit = 20): Promise<ChunkPreviewResponse> {
        return http.get(`/rag/kb/${kbId}/documents/${docId}/chunks`, {
            params: { offset, limit },
        })
    },

    // ==================== Search ====================

    async search(request: RAGSearchRequest): Promise<RAGSearchResponse> {
        return http.post('/rag/search', request)
    },
}

export default ragService
