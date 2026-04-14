<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { 
  NButton, NInput, NSpace, NTabs, NTabPane, NUpload, 
  NUploadDragger, NProgress, NCard, NDataTable, NInputNumber,
  NSlider, NForm, NFormItem, NSpin, NModal, NSelect, useMessage 
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import { ragService } from '@/services/rag.service'
import type { RagInstance, RagUploadOptions, RagPreviewResponse, RagPreviewItem, ScoredDocument } from '@/types/rag'

const route = useRoute()
const message = useMessage()
const instanceId = Number(route.params.instanceId)

const loading = ref(true)
const instance = ref<RagInstance | null>(null)
const uploadProgress = ref(0)
const uploading = ref(false)
const uploadModalVisible = ref(false)
const pendingUpload = ref<any>(null)
const uploadOptions = ref<Required<RagUploadOptions>>({
  cleaner: 'basic',
  chunk_size: 512,
  chunk_overlap: 64,
})
const previewLoading = ref(false)
const previewData = ref<RagPreviewResponse | null>(null)
const selectedChunkId = ref<string | null>(null)
let previewTimer: ReturnType<typeof setTimeout> | null = null

const cleanerOptions = [
  { label: 'Basic (Recommended)', value: 'basic' },
  { label: 'Strip', value: 'strip' },
  { label: 'None', value: 'none' },
]

// Retrieval debug state
const searchQuery = ref('')
const searchTopK = ref(5)
const searchResults = ref<ScoredDocument[]>([])
const searching = ref(false)

// Chat debug state
const chatQuery = ref('')
const chatResponse = ref('')
const chatting = ref(false)
const chatParams = ref({
  system_prompt: 'You are a helpful assistant. Answer based on the provided context.',
  temperature: 0.7,
  max_tokens: 1000
})

async function fetchInstance() {
  loading.value = true
  try {
    instance.value = await ragService.getInstance(instanceId)
  } catch (err) {
    message.error('Failed to load instance details')
  } finally {
    loading.value = false
  }
}

function handleUpload(options: any) {
  pendingUpload.value = options
  uploadModalVisible.value = true
}

async function fetchPreview() {
  if (!pendingUpload.value?.file?.file) return
  previewLoading.value = true
  try {
    previewData.value = await ragService.previewFile(
      instanceId,
      pendingUpload.value.file.file,
      uploadOptions.value,
    )
    if (previewData.value?.raw_chunks?.length && !selectedChunkId.value) {
      selectedChunkId.value = previewData.value.raw_chunks[0]?.id ?? null
    }
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Preview failed')
    previewData.value = null
  } finally {
    previewLoading.value = false
  }
}

async function confirmUpload() {
  if (!pendingUpload.value?.file?.file) {
    uploadModalVisible.value = false
    return
  }
  uploading.value = true
  uploadProgress.value = 0
  try {
    await ragService.uploadFile(
      instanceId,
      pendingUpload.value.file.file,
      uploadOptions.value,
      (percent) => {
        uploadProgress.value = percent
      },
    )
    pendingUpload.value?.onFinish?.()
    message.success('File processed and indexed')
  } catch (err) {
    pendingUpload.value?.onError?.()
    message.error(err instanceof Error ? err.message : 'Upload failed')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    pendingUpload.value = null
    uploadModalVisible.value = false
  }
}

function cancelUpload() {
  pendingUpload.value?.onError?.()
  pendingUpload.value = null
  uploadModalVisible.value = false
}

watch(uploadModalVisible, (v) => {
  if (v) {
    fetchPreview()
  } else {
    previewData.value = null
    selectedChunkId.value = null
  }
})

watch(uploadOptions, () => {
  if (!uploadModalVisible.value) return
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    fetchPreview()
  }, 300)
}, { deep: true })

function getSelectedChunk(rawChunks: RagPreviewItem[], cleanChunks: RagPreviewItem[]) {
  if (!selectedChunkId.value) return { raw: null, clean: null }
  const raw = rawChunks.find(c => c.id === selectedChunkId.value) || null
  const clean = cleanChunks.find(c => c.id === selectedChunkId.value) || null
  return { raw, clean }
}

const selectedChunk = computed(() => {
  if (!previewData.value) return { raw: null as RagPreviewItem | null, clean: null as RagPreviewItem | null }
  return getSelectedChunk(previewData.value.raw_chunks, previewData.value.clean_chunks)
})

const firstPreviewDocument = computed(() => {
  return previewData.value?.documents?.[0] ?? null
})

const previewChunkColumns = [
  {
    title: '#',
    key: 'index',
    width: 60,
    render(row: RagPreviewItem) {
      return row.index ?? '-'
    },
  },
  {
    title: 'Chunk',
    key: 'content',
    render(row: RagPreviewItem) {
      const suffix = row.truncated ? ' …' : ''
      return h('div', { class: 'whitespace-pre-wrap text-sm' }, `${row.content}${suffix}`)
    },
  },
]

async function handleSearch() {
  if (!searchQuery.value) return
  searching.value = true
  try {
    searchResults.value = await ragService.search(instanceId, {
      query: searchQuery.value,
      top_k: searchTopK.value
    })
  } catch (err) {
    message.error('Search failed')
  } finally {
    searching.value = false
  }
}

async function handleChat() {
  if (!chatQuery.value) return
  chatting.value = true
  chatResponse.value = ''
  
  try {
    // Note: This is a placeholder for SSE POST. In a real project,
    // you'd use fetch with a ReadableStream.
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/rag/instance/${instanceId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        query: chatQuery.value,
        ...chatParams.value
      })
    });

    if (!response.body) throw new Error('No response body');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.error) {
              message.error(data.error);
            } else if (data.content) {
              chatResponse.value += data.content;
            }
          } catch (e) {}
        }
      }
    }
  } catch (err) {
    message.error('Chat failed');
  } finally {
    chatting.value = false;
  }
}

const searchColumns = [
  {
    title: 'Content',
    key: 'chunk.content',
    render(row: ScoredDocument) {
      return h('div', { class: 'whitespace-pre-wrap' }, row.chunk.content)
    }
  },
  {
    title: 'Score',
    key: 'score',
    width: 100,
    render(row: ScoredDocument) {
      return row.score.toFixed(4)
    }
  }
]

onMounted(fetchInstance)
</script>

<script lang="ts">
import { h } from 'vue'
export default {}
</script>

<template>
  <div v-if="!loading && instance">
    <PageHeader :title="instance.name" :subtitle="`Collection: ${instance.collection_name}`" back-button />

    <BentoCard>
      <NTabs type="line" animated>
        <!-- Upload Tab -->
        <NTabPane name="upload" tab="Upload Documents">
          <NSpace vertical size="large" class="py-4">
            <NUpload
              multiple
              directory-dnd
              :custom-request="handleUpload"
              :show-file-list="false"
            >
              <NUploadDragger>
                <div style="margin-bottom: 12px">
                  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <div class="text-lg">Click or drag file to this area to upload</div>
                <div class="text-gray-400 mt-2">Support for PDF, Docx, Markdown, TXT, CSV, Excel</div>
              </NUploadDragger>
            </NUpload>
            
            <div v-if="uploading">
              <div class="mb-2 flex justify-between">
                <span>Processing...</span>
                <span>{{ uploadProgress }}%</span>
              </div>
              <NProgress type="line" :percentage="uploadProgress" :show-indicator="false" processing />
            </div>

            <NModal
              :show="uploadModalVisible"
              preset="card"
              title="Upload Settings"
              style="width: 980px"
              @update:show="(v) => (uploadModalVisible = v)"
            >
              <NForm label-placement="top">
                <NFormItem label="Cleaner">
                  <NSelect
                    v-model:value="uploadOptions.cleaner"
                    :options="cleanerOptions"
                  />
                </NFormItem>
                <div class="grid grid-cols-2 gap-4">
                  <NFormItem label="Chunk Size">
                    <NInputNumber v-model:value="uploadOptions.chunk_size" :min="64" :max="4096" style="width: 100%" />
                  </NFormItem>
                  <NFormItem label="Chunk Overlap">
                    <NInputNumber v-model:value="uploadOptions.chunk_overlap" :min="0" :max="1024" style="width: 100%" />
                  </NFormItem>
                </div>

                <div class="mt-4">
                  <div class="mb-2 flex items-center justify-between">
                    <div class="text-sm font-medium">Preview</div>
                    <div v-if="previewData" class="text-xs text-gray-500">
                      docs: {{ previewData.counts.documents }}, chunks: {{ previewData.counts.chunks }}
                    </div>
                  </div>

                  <div v-if="previewLoading" class="py-6 flex justify-center">
                    <NSpin />
                  </div>

                  <div v-else-if="previewData" class="grid grid-cols-3 gap-4">
                    <NCard size="small" title="Load Result">
                      <div class="text-xs text-gray-500 mb-2">
                        showing first {{ previewData.documents.length }} doc(s)
                      </div>
                      <div v-if="firstPreviewDocument" class="whitespace-pre-wrap text-sm max-h-[320px] overflow-auto">
                        {{ firstPreviewDocument.content }}<span v-if="firstPreviewDocument.truncated"> …</span>
                      </div>
                      <div v-else class="text-gray-400 text-sm">No content</div>
                    </NCard>

                    <NCard size="small" title="Split Result">
                      <div class="text-xs text-gray-500 mb-2">
                        showing first {{ previewData.raw_chunks.length }} chunk(s)
                      </div>
                      <NDataTable
                        size="small"
                        :columns="previewChunkColumns"
                        :data="previewData.raw_chunks"
                        :bordered="false"
                        :row-props="(row) => ({ onClick: () => (selectedChunkId = row.id) })"
                        :max-height="320"
                      />
                    </NCard>

                    <NCard size="small" title="Clean Result">
                      <div class="text-xs text-gray-500 mb-2">
                        selected chunk compare
                      </div>
                      <div v-if="selectedChunk.raw && selectedChunk.clean" class="grid grid-cols-1 gap-3">
                        <div>
                          <div class="text-xs font-medium mb-1">Raw</div>
                          <div class="whitespace-pre-wrap text-sm max-h-[140px] overflow-auto bg-gray-50 border border-gray-200 rounded p-2">
                            {{ selectedChunk.raw.content }}<span v-if="selectedChunk.raw.truncated"> …</span>
                          </div>
                        </div>
                        <div>
                          <div class="text-xs font-medium mb-1">Clean</div>
                          <div class="whitespace-pre-wrap text-sm max-h-[140px] overflow-auto bg-gray-50 border border-gray-200 rounded p-2">
                            {{ selectedChunk.clean.content }}<span v-if="selectedChunk.clean.truncated"> …</span>
                          </div>
                        </div>
                      </div>
                      <div v-else class="text-gray-400 text-sm">Select a chunk to compare</div>
                    </NCard>
                  </div>
                </div>

                <NSpace justify="end">
                  <NButton @click="cancelUpload">Cancel</NButton>
                  <NButton type="primary" :loading="uploading" @click="confirmUpload">Start Upload</NButton>
                </NSpace>
              </NForm>
            </NModal>
          </NSpace>
        </NTabPane>

        <!-- Search Tab -->
        <NTabPane name="search" tab="Retrieval Debug">
          <NSpace vertical size="large" class="py-4">
            <NSpace align="center">
              <NInput v-model:value="searchQuery" placeholder="Enter query to test retrieval..." style="width: 400px" @keyup.enter="handleSearch" />
              <NInputNumber v-model:value="searchTopK" :min="1" :max="50" placeholder="Top K" style="width: 100px" />
              <NButton type="primary" :loading="searching" @click="handleSearch">Search</NButton>
            </NSpace>
            
            <NDataTable
              :columns="searchColumns"
              :data="searchResults"
              :bordered="false"
              striped
            />
          </NSpace>
        </NTabPane>

        <!-- Chat Tab -->
        <NTabPane name="chat" tab="Chat Debug">
          <div class="grid grid-cols-3 gap-6 py-4">
            <div class="col-span-2">
              <NSpace vertical size="large">
                <div class="bg-gray-50 p-4 rounded min-h-[400px] whitespace-pre-wrap border border-gray-200">
                  <div v-if="!chatResponse && !chatting" class="text-gray-400 italic">No conversation yet...</div>
                  <div v-else>{{ chatResponse }}</div>
                  <div v-if="chatting" class="inline-block w-1 h-5 bg-blue-500 animate-pulse ml-1"></div>
                </div>
                
                <NSpace align="end">
                  <NInput
                    v-model:value="chatQuery"
                    type="textarea"
                    placeholder="Ask something based on your knowledge base..."
                    :autosize="{ minRows: 2, maxRows: 5 }"
                    style="width: 500px"
                    @keyup.enter.ctrl="handleChat"
                  />
                  <NButton type="primary" :loading="chatting" @click="handleChat">Send</NButton>
                </NSpace>
              </NSpace>
            </div>

            <div class="col-span-1 border-l pl-6">
              <h3 class="font-medium mb-4">Chat Parameters</h3>
              <NForm label-placement="top">
                <NFormItem label="System Prompt">
                  <NInput v-model:value="chatParams.system_prompt" type="textarea" :autosize="{ minRows: 3 }" />
                </NFormItem>
                <NFormItem label="Temperature">
                  <NSlider v-model:value="chatParams.temperature" :min="0" :max="1" :step="0.1" />
                </NFormItem>
                <NFormItem label="Max Tokens">
                  <NInputNumber v-model:value="chatParams.max_tokens" :min="1" :max="4000" style="width: 100%" />
                </NFormItem>
              </NForm>
            </div>
          </div>
        </NTabPane>
      </NTabs>
    </BentoCard>
  </div>
  <div v-else-if="loading" class="flex justify-center py-20">
    <NSpin size="large" />
  </div>
</template>
