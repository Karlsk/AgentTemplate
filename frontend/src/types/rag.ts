export interface KnowledgeBase {
    id: number
    workspace_id: number
    name: string
    description: string
    embedding_model_id: number | null
    chunk_method: string
    chunk_size: number
    chunk_overlap: number
    retrieval_mode: string
    semantic_weight: number
    keyword_weight: number
    default_top_k: number
    enable_score_threshold: boolean
    default_score_threshold: number
    status: number
    doc_count: number
    chunk_count: number
    created_at: string
}

export interface KnowledgeBaseListItem {
    id: number
    name: string
    description: string
    chunk_method: string
    retrieval_mode: string
    status: number
    doc_count: number
    chunk_count: number
    created_at: string
}

export interface KnowledgeBaseCreatePayload {
    name: string
    description: string
    embedding_model_id: number | null
    chunk_method: string
    chunk_size: number
    chunk_overlap: number
    retrieval_mode: string
    semantic_weight: number
    keyword_weight: number
    default_top_k: number
    enable_score_threshold: boolean
    default_score_threshold: number
}

export interface KnowledgeBaseUpdatePayload {
    id: number
    name?: string
    description?: string
    embedding_model_id?: number | null
    chunk_method?: string
    chunk_size?: number
    chunk_overlap?: number
    retrieval_mode?: string
    semantic_weight?: number
    keyword_weight?: number
    default_top_k?: number
    enable_score_threshold?: boolean
    default_score_threshold?: number
    status?: number
}

export interface RagDocument {
    id: number
    kb_id: number
    name: string
    file_type: string
    file_size: number
    chunk_method: string | null
    chunk_size: number | null
    chunk_overlap: number | null
    chunk_separator: string | null
    chunk_count: number
    status: number
    error_msg: string | null
    processing_step: string | null
    parse_progress: number
    chunk_progress: number
    embed_progress: number
    created_at: string
}

export interface RagDocumentListItem {
    id: number
    name: string
    file_type: string
    file_size: number
    chunk_count: number
    status: number
    processing_step: string | null
    parse_progress: number
    chunk_progress: number
    embed_progress: number
    created_at: string
}

export interface DocumentUploadOptions {
    chunk_method?: string
    chunk_size?: number
    chunk_overlap?: number
    chunk_separator?: string
}

export interface DocumentProgressResponse {
    doc_id: number
    status: number
    processing_step: string | null
    parse_progress: number
    chunk_progress: number
    embed_progress: number
    error_msg: string | null
}

export interface ChunkPreviewItem {
    chunk_index: number
    content: string
    char_count: number
    metadata: Record<string, unknown> | null
}

export interface ChunkPreviewResponse {
    doc_id: number
    doc_name: string
    total_chunks: number
    chunks: ChunkPreviewItem[]
}

export interface RAGSearchRequest {
    kb_ids: number[]
    query: string
    top_k?: number
    search_mode?: 'vector' | 'keyword' | 'hybrid'
    score_threshold?: number
    rerank: boolean
    semantic_weight?: number
    keyword_weight?: number
}

export interface ChunkResult {
    chunk_id: string
    doc_id: number | null
    kb_id: number | null
    content: string
    score: number
    metadata: Record<string, unknown> | null
    doc_name: string | null
}

export interface RAGSearchResponse {
    query: string
    results: ChunkResult[]
    total: number
    trace: Record<string, unknown> | null
}

export const ChunkMethodLabels: Record<string, string> = {
    naive: 'Naive',
    sentence: 'Sentence',
    token: 'Token',
    delimiter: 'Delimiter',
}

export const SearchModeLabels: Record<string, string> = {
    vector: 'Vector',
    keyword: 'Keyword',
    hybrid: 'Hybrid',
}

export const RetrievalModeLabels: Record<string, string> = {
    vector: 'Vector',
    hybrid: 'Hybrid',
}

export const DocStatusLabels: Record<number, string> = {
    0: 'Pending',
    1: 'Processing',
    2: 'Completed',
    3: 'Failed',
}
