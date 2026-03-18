<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import {
  NButton,
  NInput,
  NSelect,
  NInputNumber,
  NSwitch,
  NSpace,
  NCard,
  NTag,
  NSpin,
  NEmpty,
  NText,
  NScrollbar,
  NSlider,
  useMessage,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import BentoCard from '@/components/common/BentoCard.vue'
import ragService from '@/services/rag.service'
import type { KnowledgeBaseListItem, KnowledgeBase, ChunkResult } from '@/types/rag'

const message = useMessage()

const knowledgeBases = ref<KnowledgeBaseListItem[]>([])
const selectedKbIds = ref<number[]>([])
const query = ref('')
const topK = ref<number | null>(null)
const searchMode = ref<string | null>(null)
const scoreThreshold = ref<number | null>(null)
const rerank = ref(false)
const semanticWeight = ref<number | null>(null)
const keywordWeight = ref<number | null>(null)

// KB defaults display
const kbDefaults = ref<KnowledgeBase | null>(null)

const searching = ref(false)
const results = ref<ChunkResult[]>([])
const totalResults = ref(0)
const hasSearched = ref(false)

const searchModeOptions = [
  { label: 'Hybrid (Vector + Keyword)', value: 'hybrid' },
  { label: 'Vector (Semantic)', value: 'vector' },
  { label: 'Keyword (BM25)', value: 'keyword' },
]

const isHybridMode = computed(() => (searchMode.value || kbDefaults.value?.retrieval_mode) === 'hybrid')

async function loadKnowledgeBases() {
  try {
    knowledgeBases.value = await ragService.listKnowledgeBases()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Failed to load knowledge bases')
  }
}

const kbOptions = ref<{ label: string; value: number }[]>([])

async function refreshKbOptions() {
  await loadKnowledgeBases()
  kbOptions.value = knowledgeBases.value.map((kb) => ({
    label: `${kb.name} (${kb.doc_count} docs)`,
    value: kb.id,
  }))
}

// Load KB defaults when selection changes
watch(selectedKbIds, async (ids) => {
  if (ids.length > 0) {
    try {
      const kb = await ragService.getKnowledgeBase(ids[0])
      kbDefaults.value = kb
    } catch {
      kbDefaults.value = null
    }
  } else {
    kbDefaults.value = null
  }
})

function handleSemanticWeightChange(val: number) {
  semanticWeight.value = val
  keywordWeight.value = Math.round((1 - val) * 100) / 100
}

async function handleSearch() {
  if (selectedKbIds.value.length === 0) {
    message.warning('Please select at least one knowledge base')
    return
  }
  if (!query.value.trim()) {
    message.warning('Please enter a search query')
    return
  }

  searching.value = true
  hasSearched.value = true
  results.value = []
  totalResults.value = 0

  try {
    const request: Record<string, unknown> = {
      kb_ids: selectedKbIds.value,
      query: query.value.trim(),
      rerank: rerank.value,
    }
    if (topK.value != null) request.top_k = topK.value
    if (searchMode.value) request.search_mode = searchMode.value
    if (scoreThreshold.value != null) request.score_threshold = scoreThreshold.value
    if (semanticWeight.value != null) request.semantic_weight = semanticWeight.value
    if (keywordWeight.value != null) request.keyword_weight = keywordWeight.value

    const response = await ragService.search(request as any)
    results.value = response.results
    totalResults.value = response.total
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Search failed')
  } finally {
    searching.value = false
  }
}

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error' | 'primary'

function scoreColor(score: number): TagType {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'info'
  if (score >= 0.3) return 'warning'
  return 'default'
}

onMounted(refreshKbOptions)
</script>

<template>
  <div>
    <PageHeader title="RAG Search" subtitle="Search across knowledge bases using vector, keyword, or hybrid retrieval" />

    <!-- Search Controls -->
    <BentoCard class="mb-4">
      <div class="space-y-4">
        <!-- KB Selection -->
        <div>
          <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
            Knowledge Bases
          </label>
          <NSelect
            v-model:value="selectedKbIds"
            :options="kbOptions"
            multiple
            placeholder="Select knowledge bases to search"
            clearable
          />
        </div>

        <!-- KB Defaults Hint -->
        <div v-if="kbDefaults" class="rounded bg-gray-50 px-3 py-2 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
          KB defaults: mode={{ kbDefaults.retrieval_mode }}, top_k={{ kbDefaults.default_top_k }},
          weights={{ kbDefaults.semantic_weight }}/{{ kbDefaults.keyword_weight }}
          <span v-if="kbDefaults.enable_score_threshold">, threshold={{ kbDefaults.default_score_threshold }}</span>
          <span class="ml-2 italic">Override below or leave empty to use these.</span>
        </div>

        <!-- Query Input -->
        <div>
          <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
            Search Query
          </label>
          <NInput
            v-model:value="query"
            type="textarea"
            placeholder="Enter your search query..."
            :autosize="{ minRows: 2, maxRows: 5 }"
            @keydown.ctrl.enter="handleSearch"
            @keydown.meta.enter="handleSearch"
          />
        </div>

        <!-- Options Row -->
        <div class="flex flex-wrap items-end gap-4">
          <div class="w-48">
            <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
              Search Mode
            </label>
            <NSelect
              v-model:value="searchMode"
              :options="searchModeOptions"
              clearable
              :placeholder="kbDefaults ? kbDefaults.retrieval_mode : 'hybrid'"
            />
          </div>
          <div class="w-28">
            <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
              Top K
            </label>
            <NInputNumber
              v-model:value="topK"
              :min="1"
              :max="50"
              size="medium"
              clearable
              :placeholder="String(kbDefaults?.default_top_k ?? 5)"
            />
          </div>
          <div class="w-32">
            <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
              Score Threshold
            </label>
            <NInputNumber
              v-model:value="scoreThreshold"
              :min="0"
              :max="1"
              :step="0.05"
              size="medium"
              clearable
              placeholder="KB default"
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
              Rerank
            </label>
            <NSwitch v-model:value="rerank" />
          </div>
          <NButton type="primary" :loading="searching" @click="handleSearch">
            Search
          </NButton>
        </div>

        <!-- Hybrid Weights (shown when hybrid mode) -->
        <div v-if="isHybridMode" class="w-80">
          <label class="mb-1 block text-sm font-medium text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
            Semantic / Keyword Weight
          </label>
          <NSlider
            :value="semanticWeight ?? kbDefaults?.semantic_weight ?? 0.7"
            :min="0"
            :max="1"
            :step="0.05"
            :tooltip="true"
            @update:value="handleSemanticWeightChange"
          />
          <div class="mt-1 flex justify-between text-xs text-(--color-text-secondary)">
            <span>Keyword: {{ keywordWeight ?? kbDefaults?.keyword_weight ?? 0.3 }}</span>
            <span>Semantic: {{ semanticWeight ?? kbDefaults?.semantic_weight ?? 0.7 }}</span>
          </div>
        </div>
      </div>
    </BentoCard>

    <!-- Results -->
    <div v-if="searching" class="flex items-center justify-center py-12">
      <NSpin size="large" />
      <NText class="ml-3" depth="3">Searching...</NText>
    </div>

    <template v-else-if="hasSearched">
      <div class="mb-3 text-sm text-(--color-text-secondary) dark:text-(--color-text-secondary-dark)">
        {{ totalResults }} result(s) found
      </div>

      <NEmpty v-if="results.length === 0" description="No results found. Try adjusting your query or search parameters." />

      <NScrollbar v-else style="max-height: calc(100vh - 400px)">
        <NSpace vertical :size="12">
          <NCard
            v-for="(chunk, idx) in results"
            :key="chunk.chunk_id"
            size="small"
            :bordered="true"
            hoverable
          >
            <template #header>
              <NSpace align="center" :size="8">
                <NTag size="tiny" round>
                  #{{ idx + 1 }}
                </NTag>
                <NTag :type="scoreColor(chunk.score)" size="small" round>
                  Score: {{ chunk.score.toFixed(4) }}
                </NTag>
                <NTag v-if="chunk.doc_name" size="tiny" round type="info">
                  {{ chunk.doc_name }}
                </NTag>
              </NSpace>
            </template>
            <pre class="whitespace-pre-wrap break-words text-sm leading-relaxed text-(--color-text-primary) dark:text-(--color-text-primary-dark)">{{ chunk.content }}</pre>
            <template v-if="chunk.metadata" #footer>
              <NText depth="3" class="text-xs">
                Metadata: {{ JSON.stringify(chunk.metadata) }}
              </NText>
            </template>
          </NCard>
        </NSpace>
      </NScrollbar>
    </template>
  </div>
</template>
