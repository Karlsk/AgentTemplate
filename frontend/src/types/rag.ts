export interface RagInstance {
  id: number;
  workspace_id: number;
  name: string;
  collection_name: string;
  embedding_model_id: number;
  config?: string;
  created_at?: string;
}

export interface RagInstanceCreatePayload {
  name: string;
  embedding_model_id: number;
  dimension: number;
  config?: Record<string, any>;
}

export interface RagSearchRequest {
  query: string;
  top_k?: number;
  filters?: Record<string, any>;
}

export type RagCleanerType = 'none' | 'basic' | 'strip';

export interface RagUploadOptions {
  cleaner?: RagCleanerType;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface RagPreviewItem {
  id: string;
  document_id?: string;
  index?: number;
  metadata: any;
  content: string;
  truncated: boolean;
}

export interface RagPreviewResponse {
  documents: RagPreviewItem[];
  raw_chunks: RagPreviewItem[];
  clean_chunks: RagPreviewItem[];
  counts: {
    documents: number;
    chunks: number;
  };
  options: Required<RagUploadOptions>;
}

export interface RagChatRequest {
  query: string;
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
  llm_model?: string;
}

export interface ScoredDocument {
  chunk: {
    id: string;
    content: string;
    document_id: string;
    metadata: any;
  };
  score: number;
}
