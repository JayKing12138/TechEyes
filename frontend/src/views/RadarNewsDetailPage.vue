<template>
  <div class="min-h-screen techeyes-page-shell radar-detail-shell">
    <Header />

    <main class="container mx-auto px-4 md:px-8 pt-24 pb-10">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <svg class="w-16 h-16 mx-auto mb-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 class="text-xl font-semibold text-red-100 mb-2">加载失败</h3>
        <p class="text-red-200 mb-6">{{ error }}</p>
        <button class="btn-primary" @click="$router.push('/radar')">返回雷达</button>
      </div>

      <div v-else class="detail-content">
        <button class="back-btn" @click="$router.push('/radar')">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          返回雷达
        </button>

        <div class="news-header">
          <h1 class="news-title">{{ newsDetail.news.title }}</h1>
          <div class="news-meta">
            <span v-if="newsDetail.news.source" class="meta-item">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              {{ newsDetail.news.source }}
            </span>
            <span v-if="newsDetail.news.created_at" class="meta-item">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ formatTime(newsDetail.news.created_at) }}
            </span>
            <a v-if="newsDetail.news.url" :href="newsDetail.news.url" target="_blank" class="meta-link">
              查看原文 →
            </a>
          </div>
        </div>

        <div class="content-grid">
          <div class="left-panel">
            <div class="section news-content-section">
              <h2 class="section-title">新闻内容</h2>
              <div class="news-content">
                {{ newsDetail.news.content || newsDetail.news.snippet }}
              
                            <!-- 原始新闻链接列表 -->
                            <div v-if="sourceUrls && sourceUrls.length > 0" class="source-links-section">
                              <h3 class="source-links-title">📰 参考新闻</h3>
                              <div class="source-links-list">
                                <a
                                  v-for="(source, index) in sourceUrls"
                                  :key="index"
                                  :href="source.url"
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class="source-link-item"
                                >
                                  <svg class="link-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                  </svg>
                                  <span class="link-text">{{ source.title }}</span>
                                </a>
                              </div>
                            </div>
              </div>
            </div>

            <div class="section graph-section">
              <h2 class="section-title">实体图谱</h2>
              <p class="section-desc">点击实体节点可选中，用于按图索骥分析</p>
              <div class="graph-wrapper">
                <EntityGraph
                  :nodes="graphNodes"
                  :edges="graphEdges"
                  v-model="selectedEntities"
                  @node-click="handleEntityClick"
                  @node-drag-start="handleEntityDragStart"
                  @node-drag-end="handleEntityDragEnd"
                />
              </div>
            </div>

            <div 
              class="section analysis-section"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
              :class="{ 'drag-over': isDragOver }"
            >
              <h2 class="section-title">按图索骥</h2>
              <p class="section-desc">拖拽或选择上方图谱中的实体，分析它们在最新新闻中的动向</p>
              
              <div class="analysis-input-area">
                <div class="selected-entities">
                  <span
                    v-for="entity in selectedEntities"
                    :key="entity.id"
                    class="entity-tag"
                  >
                    {{ entity.name }}
                    <button @click="removeEntity(entity.id)" class="remove-btn">×</button>
                  </span>
                  <span v-if="selectedEntities.length === 0" class="empty-hint">
                    点击图谱中的实体或拖拽至此
                  </span>
                </div>
                
                <div class="analysis-controls">
                  <input
                    v-model="customQuestion"
                    type="text"
                    placeholder="自定义分析问题（可选）"
                    class="question-input"
                  />
                  <button
                    class="analyze-btn"
                    @click="handleAnalyze"
                    :disabled="selectedEntities.length === 0 || analyzing"
                  >
                    {{ analyzing ? '分析中...' : '开始分析' }}
                  </button>
                </div>
              </div>

              <div v-if="analysisHistory.length > 0" class="analysis-history">
                <h3 class="result-title">分析记录（{{ analysisHistory.length }}）</h3>
                <div v-for="run in analysisHistory" :key="run.id" class="analysis-run-card">
                  <button class="analysis-run-header" @click="toggleAnalysisExpanded(run.id)">
                    <div>
                      <div class="analysis-run-title">{{ run.title }}</div>
                      <div class="analysis-run-meta">
                        实体: {{ run.requestEntities.join('、') }} | 新闻: {{ run.result.news_count }}
                        <span v-if="run.result.local_news_count !== undefined">（本地 {{ run.result.local_news_count }}）</span>
                        <span v-if="run.result.web_news_count !== undefined">（互联网 {{ run.result.web_news_count }}）</span>
                      </div>
                    </div>
                    <span class="analysis-expand-icon">{{ run.expanded ? '收起' : '展开' }}</span>
                  </button>

                  <div v-if="run.expanded" class="result-content">
                    <MarkdownRenderer :content="run.result.answer" />
                    <div class="result-news">
                      <h4>相关新闻 ({{ run.result.news_count }})</h4>
                      <div
                        v-for="(news, index) in run.result.news"
                        :key="`${run.id}-${index}`"
                        class="result-news-item"
                      >
                        <span class="news-index">{{ index + 1 }}</span>
                        <div class="news-info">
                          <a v-if="news.url" :href="news.url" target="_blank" class="news-link">
                            {{ news.title }}
                          </a>
                          <span v-else class="news-title">{{ news.title }}</span>
                          <span v-if="news.snippet" class="news-snippet">{{ news.snippet }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="followup-panel">
                <h3 class="result-title">继续追问</h3>
                <div class="analysis-controls">
                  <input
                    v-model="followupQuestion"
                    type="text"
                    placeholder="例如：这些变化对阿里云短期竞争意味着什么？"
                    class="question-input"
                  />
                  <button class="analyze-btn" @click="handleFollowup" :disabled="followupLoading">
                    {{ followupLoading ? '追问中...' : '提交追问' }}
                  </button>
                </div>

                <div v-if="followupHistory.length > 0" class="analysis-history">
                  <h3 class="result-title">追问记录（{{ followupHistory.length }}）</h3>
                  <div v-for="(item, index) in followupHistory" :key="index" class="analysis-run-card">
                    <button class="analysis-run-header" @click="toggleFollowupExpanded(index)">
                      <div>
                        <div class="analysis-run-title">Q: {{ item.question }}</div>
                      </div>
                      <span class="analysis-expand-icon">{{ item.expanded ? '收起' : '展开' }}</span>
                    </button>
                    <div v-if="item.expanded" class="result-content">
                      <MarkdownRenderer :content="item.answer" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="right-panel">
            <div class="section entities-section">
              <h2 class="section-title">实体列表</h2>
              <div class="entities-list">
                <div
                  v-for="entity in entityList"
                  :key="entity.id"
                  class="entity-item"
                  :class="{ 'entity-selected': isEntitySelected(entity.id) }"
                  @click="toggleEntitySelection(entity)"
                >
                  <span class="entity-type-badge" :class="`type-${entity.type}`">
                    {{ entity.type }}
                  </span>
                  <span class="entity-name">{{ entity.name }}</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Header from '@/components/Header.vue'
import EntityGraph from '@/components/EntityGraph.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import {
  getNewsDetail,
  analyzeEntities,
  askRadarFollowup,
  getNewsMyHistory,
  type NewsDetail,
  type AnalyzeEntitiesRequest,
  type AnalyzeEntitiesResponse,
  type FollowupResponse,
} from '@/services/api'

const route = useRoute()
const newsId = route.params.id as string

const loading = ref(true)
const error = ref('')
const newsDetail = ref<NewsDetail>({
  news: {
    id: '',
    title: '',
    url: '',
    snippet: '',
    content: '',
    source: '',
    created_at: ''
  },
  graph: {
    nodes: [],
    edges: []
  }
})

const selectedEntities = ref<any[]>([])
const customQuestion = ref('')
const analyzing = ref(false)
const analysisHistory = ref<Array<{
  id: string
  title: string
  requestEntities: string[]
  result: AnalyzeEntitiesResponse
  expanded: boolean
}>>([])
const followupQuestion = ref('')
const followupLoading = ref(false)
const followupHistory = ref<Array<FollowupResponse & { expanded: boolean }>>([])

const isDragOver = ref(false)
const draggingEntity = ref<any | null>(null)

const graphNodes = computed(() => {
  return newsDetail.value.graph.nodes.map(node => ({
    ...node,
    x: node.x || 0,
    y: node.y || 0
  }))
})

const graphEdges = computed(() => {
  return newsDetail.value.graph.edges
})

const entityList = computed(() => {
  return newsDetail.value.graph.nodes.filter(n => n.type !== 'News')
})

const sourceUrls = computed(() => {
  // 从newsDetail中提取原始新闻链接列表
  return newsDetail.value.news.source_urls || []
})

const isEntitySelected = (entityId: string) => {
  return selectedEntities.value.some(e => e.id === entityId)
}

const toggleEntitySelection = (entity: any) => {
  const index = selectedEntities.value.findIndex(e => e.id === entity.id)
  if (index >= 0) {
    selectedEntities.value.splice(index, 1)
  } else {
    selectedEntities.value.push(entity)
  }
}

const removeEntity = (entityId: string) => {
  const index = selectedEntities.value.findIndex(e => e.id === entityId)
  if (index >= 0) {
    selectedEntities.value.splice(index, 1)
  }
}

const handleEntityClick = (entity: any) => {
  // EntityGraph 内部点击已通过 v-model 同步 selectedEntities，
  // 这里不再二次 toggle，避免“点一下又取消”的问题。
  if (entity.type === 'News') {
    return
  }
}

const handleEntityDragStart = (entity: any) => {
  draggingEntity.value = entity
}

const handleEntityDragEnd = (entity: any) => {
  draggingEntity.value = null
  isDragOver.value = false
}

const handleDrop = (event: DragEvent) => {
  isDragOver.value = false
  
  if (draggingEntity.value) {
    const entity = draggingEntity.value
    const index = selectedEntities.value.findIndex(e => e.id === entity.id)
    if (index < 0) {
      selectedEntities.value.push(entity)
    }
    draggingEntity.value = null
  }
}

const handleAnalyze = async () => {
  if (selectedEntities.value.length === 0) return

  try {
    analyzing.value = true
    const entities = selectedEntities.value.map(e => e.name)
    const request: AnalyzeEntitiesRequest = {
      entities,
      news_id: newsId,
      question: customQuestion.value || undefined
    }
    const result = await analyzeEntities(request)
    const title = customQuestion.value?.trim() || `${entities.join('、')} 动向分析`
    analysisHistory.value.unshift({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      title,
      requestEntities: entities,
      result,
      expanded: true
    })
    customQuestion.value = ''
    // 通知其他页面刷新档案列表（如 RadarPage）——使用 localStorage 作为简单的跨窗口通知
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('radar_archive_updated', String(Date.now()))
      }
    } catch (e) {
      console.warn('无法写入 localStorage 通知档案更新', e)
    }
  } catch (err: any) {
    console.error('分析失败:', err)
    error.value = err.message || '分析失败，请重试'
  } finally {
    analyzing.value = false
  }
}

const toggleAnalysisExpanded = (id: string) => {
  const target = analysisHistory.value.find(item => item.id === id)
  if (target) {
    target.expanded = !target.expanded
  }
}

const handleFollowup = async () => {
  if (!followupQuestion.value.trim()) return
  try {
    followupLoading.value = true
    const response = await askRadarFollowup({
      news_id: newsId,
      question: followupQuestion.value.trim(),
      entities: selectedEntities.value.map(e => e.name),
      analysis_history: analysisHistory.value.map(item => ({
        question: item.result.question,
        answer: item.result.answer
      }))
    })
    followupHistory.value.unshift({ ...response, expanded: true })
    followupQuestion.value = ''
  } catch (err: any) {
    console.error('追问失败:', err)
    error.value = err.message || '追问失败，请重试'
  } finally {
    followupLoading.value = false
  }
}

const toggleFollowupExpanded = (index: number) => {
  if (followupHistory.value[index]) {
    followupHistory.value[index].expanded = !followupHistory.value[index].expanded
  }
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadNewsDetail = async () => {
  try {
    loading.value = true
    error.value = ''
    newsDetail.value = await getNewsDetail(newsId)
  } catch (err: any) {
    console.error('加载新闻详情失败:', err)
    error.value = err.message || '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

/** 从后端恢复本用户在此新闻下的历史记录（按图索骥 + 追问） */
const loadMyHistory = async () => {
  try {
    const data = await getNewsMyHistory(newsId)

    // 恢复按图索骥记录
    if (data.analysis_runs && data.analysis_runs.length > 0) {
      analysisHistory.value = data.analysis_runs.map((run: any, idx: number) => ({
        id: `${run.ts || idx}-restored`,
        title: run.question || `${(run.entities || []).join('、')} 动向分析`,
        requestEntities: run.entities || [],
        result: {
          question: run.question || '',
          entities: run.entities || [],
          news_count: (run.local_news_count || 0) + (run.web_news_count || 0),
          news: [],
          local_news_count: run.local_news_count || 0,
          web_news_count: run.web_news_count || 0,
          answer: run.answer || '',
        },
        expanded: idx === 0,  // 最新一条默认展开
      }))
    }

    // 恢复追问记录
    if (data.followups && data.followups.length > 0) {
      followupHistory.value = data.followups.map((f: any, idx: number) => ({
        question: f.question,
        entities: [],
        answer: f.answer,
        news: [],
        expanded: idx === 0,
      }))
    }
  } catch (err) {
    // 未登录或接口失败时静默降级，不影响主流程
    console.warn('[RadarDetail] 无法加载历史记录（未登录或出错）', err)
  }
}

onMounted(() => {
  loadNewsDetail()
  loadMyHistory()
})
</script>

<style scoped>
.radar-detail-shell {
  background: linear-gradient(140deg, #0a162f 0%, #162a4f 55%, #111f43 100%);
  color: #e2e8f0;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.spinner {
  width: 3rem;
  height: 3rem;
  border: 3px solid rgba(125, 211, 252, 0.2);
  border-top-color: #7dd3fc;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(125, 211, 252, 0.1);
  border: 1px solid rgba(125, 211, 252, 0.3);
  color: #7dd3fc;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 1.5rem;
}

.back-btn:hover {
  background: rgba(125, 211, 252, 0.2);
  transform: translateX(-4px);
}

.news-header {
  margin-bottom: 2rem;
}

.news-title {
  font-size: clamp(1.5rem, 3vw, 2.25rem);
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, #7dd3fc 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.news-meta {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: rgba(226, 232, 240, 0.6);
  font-size: 0.875rem;
}

.meta-link {
  color: #7dd3fc;
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.3s;
}

.meta-link:hover {
  color: #a78bfa;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 2rem;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(125, 211, 252, 0.15);
  border-radius: 1rem;
  padding: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #7dd3fc;
  margin-bottom: 0.75rem;
}

.section-desc {
  font-size: 0.875rem;
  color: rgba(226, 232, 240, 0.6);
  margin-bottom: 1rem;
}

.news-content-section .news-content {
  line-height: 1.8;
  color: rgba(226, 232, 240, 0.9);
  white-space: pre-wrap;
}

/* 原始新闻链接列表样式 */
.source-links-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(125, 211, 252, 0.2);
}

.source-links-title {
  font-size: 1rem;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.9);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.source-links-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-link-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 0.5rem;
  text-decoration: none;
  color: rgba(125, 211, 252, 0.9);
  transition: all 0.3s;
}

.source-link-item:hover {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(125, 211, 252, 0.4);
  transform: translateX(4px);
}

.source-link-item .link-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
  color: rgba(125, 211, 252, 0.7);
}

.source-link-item:hover .link-icon {
  color: rgba(125, 211, 252, 1);
}

.source-link-item .link-text {
  flex: 1;
  font-size: 0.9rem;
  line-height: 1.5;
}

.graph-wrapper {
  height: 500px;
  border-radius: 0.5rem;
  overflow: hidden;
}

.analysis-input-area {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 0.75rem;
  padding: 1rem;
}

.selected-entities {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  min-height: 3rem;
  margin-bottom: 1rem;
}

.entity-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(125, 211, 252, 0.2);
  color: #7dd3fc;
  padding: 0.375rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.remove-btn {
  background: none;
  border: none;
  color: #7dd3fc;
  cursor: pointer;
  font-size: 1.25rem;
  line-height: 1;
  padding: 0;
  width: 1rem;
  height: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-btn:hover {
  color: #f87171;
}

.empty-hint {
  color: rgba(226, 232, 240, 0.4);
  font-size: 0.875rem;
  font-style: italic;
}

.analysis-section {
  transition: all 0.3s ease;
}

.analysis-section.drag-over {
  border-color: rgba(125, 211, 252, 0.5);
  background: rgba(125, 211, 252, 0.1);
  box-shadow: 0 0 20px rgba(125, 211, 252, 0.2);
}

.analysis-controls {
  display: flex;
  gap: 0.75rem;
}

.question-input {
  flex: 1;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  color: #e2e8f0;
  font-size: 0.875rem;
  outline: none;
}

.question-input::placeholder {
  color: rgba(226, 232, 240, 0.4);
}

.question-input:focus {
  border-color: rgba(125, 211, 252, 0.5);
}

.analyze-btn {
  background: linear-gradient(135deg, #7dd3fc 0%, #38bdf8 100%);
  color: #0f172a;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  white-space: nowrap;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(125, 211, 252, 0.3);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.analysis-history,
.followup-panel {
  margin-top: 1.5rem;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.analysis-run-card {
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 0.75rem;
  margin-bottom: 0.75rem;
  overflow: hidden;
}

.analysis-run-header {
  width: 100%;
  background: rgba(125, 211, 252, 0.08);
  border: none;
  padding: 0.875rem 1rem;
  color: #dbeafe;
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: left;
  cursor: pointer;
}

.analysis-run-title {
  font-size: 0.95rem;
  font-weight: 600;
}

.analysis-run-meta {
  font-size: 0.78rem;
  color: rgba(226, 232, 240, 0.65);
  margin-top: 0.25rem;
}

.analysis-expand-icon {
  color: #7dd3fc;
  font-size: 0.82rem;
}

.result-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #7dd3fc;
  margin-bottom: 1rem;
}

.result-content {
  line-height: 1.7;
  color: rgba(226, 232, 240, 0.9);
}

.result-news {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(125, 211, 252, 0.2);
}

.result-news h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #a78bfa;
  margin-bottom: 1rem;
}

.result-news-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(125, 211, 252, 0.1);
}

.result-news-item:last-child {
  border-bottom: none;
}

.news-index {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(125, 211, 252, 0.2);
  color: #7dd3fc;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
}

.news-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.news-link {
  color: #7dd3fc;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s;
}

.news-link:hover {
  color: #a78bfa;
}

.news-title {
  color: rgba(226, 232, 240, 0.9);
  font-weight: 500;
}

.news-snippet {
  font-size: 0.875rem;
  color: rgba(226, 232, 240, 0.6);
}

.entities-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(125, 211, 252, 0.15);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.entity-item:hover {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(125, 211, 252, 0.3);
}

.entity-selected {
  background: rgba(125, 211, 252, 0.1);
  border-color: rgba(125, 211, 252, 0.5);
}

.entity-type-badge {
  flex-shrink: 0;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.type-company {
  background: rgba(167, 139, 250, 0.2);
  color: #a78bfa;
}

.type-person {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.type-product {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.type-technology {
  background: rgba(248, 113, 113, 0.2);
  color: #f87171;
}

.type-country {
  background: rgba(156, 163, 175, 0.2);
  color: #9ca3af;
}

.type-other {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
}

.entity-name {
  flex: 1;
  color: rgba(226, 232, 240, 0.9);
  font-size: 0.875rem;
}

.report-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);
  color: #0f172a;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.report-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(167, 139, 250, 0.3);
}

.report-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.report-preview {
  margin-top: 1rem;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 0.75rem;
  padding: 1rem;
}

.report-summary h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #a78bfa;
  margin-bottom: 0.75rem;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stat {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #7dd3fc;
}

.stat-label {
  font-size: 0.75rem;
  color: rgba(226, 232, 240, 0.6);
}

.view-full-report-btn {
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.3);
  color: #a78bfa;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.view-full-report-btn:hover {
  background: rgba(167, 139, 250, 0.2);
}

.report-actions {
  display: flex;
  gap: 0.75rem;
}

.report-actions .view-full-report-btn,
.report-actions .download-report-btn {
  flex: 1;
}

.download-report-btn {
  background: rgba(34, 197, 94, 0.14);
  border: 1px solid rgba(34, 197, 94, 0.35);
  color: #86efac;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.download-report-btn:hover {
  background: rgba(34, 197, 94, 0.22);
}


</style>
