import axios from '../lib/axios';
import type {
  RagInstance,
  RagInstanceCreatePayload,
  RagSearchRequest,
  RagUploadOptions,
  RagPreviewResponse,
  RagChatRequest,
  ScoredDocument
} from '../types/rag';

const API_PREFIX = '/rag';

export const ragService = {
  async listInstances(): Promise<RagInstance[]> {
    return await axios.get(`${API_PREFIX}/instance`);
  },

  async createInstance(payload: RagInstanceCreatePayload): Promise<RagInstance> {
    return await axios.post(`${API_PREFIX}/instance`, payload);
  },

  async getInstance(id: number): Promise<RagInstance> {
    return await axios.get(`${API_PREFIX}/instance/${id}`);
  },

  async deleteInstance(id: number): Promise<void> {
    await axios.delete(`${API_PREFIX}/instance/${id}`);
  },

  async uploadFile(
    id: number,
    file: File,
    options?: RagUploadOptions,
    onProgress?: (percent: number) => void
  ): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    const opts: RagUploadOptions = options ?? {};
    if (opts.cleaner) formData.append('cleaner', opts.cleaner);
    if (typeof opts.chunk_size === 'number') formData.append('chunk_size', String(opts.chunk_size));
    if (typeof opts.chunk_overlap === 'number') formData.append('chunk_overlap', String(opts.chunk_overlap));
    await axios.post(`${API_PREFIX}/instance/${id}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
  },

  async previewFile(
    id: number,
    file: File,
    options?: RagUploadOptions,
  ): Promise<RagPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const opts: RagUploadOptions = options ?? {};
    if (opts.cleaner) formData.append('cleaner', opts.cleaner);
    if (typeof opts.chunk_size === 'number') formData.append('chunk_size', String(opts.chunk_size));
    if (typeof opts.chunk_overlap === 'number') formData.append('chunk_overlap', String(opts.chunk_overlap));
    return await axios.post(`${API_PREFIX}/instance/${id}/preview`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  async search(id: number, request: RagSearchRequest): Promise<ScoredDocument[]> {
    return await axios.post(`${API_PREFIX}/instance/${id}/search`, request);
  },

  chat(id: number, request: RagChatRequest): EventSource {
    // Note: Standard EventSource doesn't support POST. 
    // We should use fetch with reader or a custom implementation if POST is needed.
    // For now, let's assume we use a specialized helper for SSE with POST.
    // However, the backend is expecting POST for /chat.
    throw new Error('Chat requires POST SSE which is not supported by standard EventSource');
  }
};
