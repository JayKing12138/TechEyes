<template>
  <div class="min-h-screen techeyes-page-shell history-shell">
    <Header />

    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-32 pb-14">
      <section class="techeyes-panel p-5 md:p-6">
        <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <p class="history-eyebrow">History Center</p>
            <h1 class="text-3xl md:text-4xl font-black mt-1">历史分析记录</h1>
            <p class="text-slate-300/85 mt-2">可按关键词检索过往问题，并一键回看分析结果。</p>
          </div>

          <div class="w-full md:w-auto flex gap-2">
            <input
              v-model="keyword"
              type="text"
              class="history-search"
              placeholder="搜索历史问题..."
              @keyup.enter="loadHistory"
            />
            <button class="history-btn" @click="loadHistory">查询</button>
          </div>
        </div>
      </section>

      <section class="mt-6 techeyes-panel-soft p-4 md:p-5">
        <div class="flex items-center justify-between mb-3">
          <p class="text-sm text-slate-300">共 {{ items.length }} 条</p>
          <button class="text-xs text-cyan-300 hover:text-cyan-200" @click="loadHistory">刷新</button>
        </div>

        <div v-if="loading" class="empty-wrap">正在加载历史记录...</div>
        <div v-else-if="items.length === 0" class="empty-wrap">暂无历史记录，先去首页提一个问题吧。</div>

        <div v-else class="space-y-3">
          <article v-for="item in items" :key="item.session_id" class="history-item">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <p class="query-line">{{ item.query || '未命名问题' }}</p>
                <p class="summary-line">{{ item.summary || '分析已完成，可点击查看详情。' }}</p>
                <p class="meta-line">
                  {{ formatDate(item.start_time) }}
                  <span class="mx-2">|</span>
                  {{ statusText(item.status) }}
                  <span class="mx-2">|</span>
                  进度 {{ item.progress }}%
                </p>
              </div>

              <div class="flex gap-2">
                <button 
                  class="history-btn-sm"
                  :class="{ 'btn-active': selectedSessionId === item.session_id }"
                  @click="toggleResult(item.session_id)"
                >
                  {{ selectedSessionId === item.session_id ? '收起' : '查看结果' }}
                </button>
                <button 
                  class="history-btn-delete"
                  @click="confirmDelete(item.session_id, item.query)"
                  title="删除记录"
                >
                  删除
                </button>
              </div>
            </div>

            <!-- 展开的结果详情 -->
            <div v-if="selectedSessionId === item.session_id" class="result-detail mt-4">
              <div v-if="resultLoading" class="result-loading">正在加载结果...</div>
              <div v-else-if="resultError" class="result-error">{{ resultError }}</div>
              <div v-else-if="resultData" class="result-content">
                <div class="result-section">
                  <h3 class="result-section-title">分析摘要</h3>
                  <p class="result-text">{{ resultData.summary || '暂无摘要' }}</p>
                </div>

                <div v-if="resultTimeline.length > 0" class="result-section">
                  <h3 class="result-section-title">关键时间线</h3>
                  <div class="timeline-list">
                    <div v-for="(tItem, idx) in resultTimeline" :key="`t-${idx}`" class="timeline-row">
                      <span class="timeline-date">{{ tItem.date || '时间未知' }}</span>
                      <span class="timeline-event">{{ tItem.event || tItem.title || tItem.description || '无详细内容' }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="resultComparisons.length > 0" class="result-section">
                  <h3 class="result-section-title">对比分析</h3>
                  <div class="compare-list">
                    <div v-for="(cItem, idx) in resultComparisons" :key="`c-${idx}`" class="compare-row">
                      <span class="compare-dim">{{ cItem.dimension || `维度 ${idx + 1}` }}</span>
                      <span class="compare-detail">{{ cItem.details || cItem.analysis || '无详细内容' }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="resultData.futureOutlook" class="result-section">
                  <h3 class="result-section-title">未来展望</h3>
                  <p class="result-text">{{ resultData.futureOutlook }}</p>
                </div>

                <div v-if="resultSources.length > 0" class="result-section">
                  <h3 class="result-section-title">信息来源</h3>
                  <div class="source-list">
                    <div v-for="(sItem, idx) in resultSources" :key="`s-${idx}`" class="source-row">
                      <span class="source-title">{{ sItem.title || '未命名来源' }}</span>
                      <a
                        v-if="sItem.url"
                        :href="sItem.url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="source-link"
                      >
                        {{ sItem.url }}
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- 删除确认对话框 -->
      <div v-if="deleteConfirm.show" class="confirm-overlay" @click="cancelDelete">
        <div class="confirm-dialog" @click.stop>
          <h3 class="confirm-title">确认删除</h3>
          <p class="confirm-message">
            确定要删除这条历史记录吗？
          </p>, deleteAnalysisHistory } from '@/services/api'

interface HistoryItem {
  session_id: string
  query: string
  status: string
  progress: number
  summary: string
  start_time?: string | null
}

const loading = ref(false)
const keyword = ref('')
const items = ref<HistoryItem[]>([])

const selectedSessionId = ref<string | null>(null)
const resultLoading = ref(false)
const resultError = ref('')
const resultData = ref<any | null>(null)

const deleteConfirm = ref({
  show: false,
  sessionId: '',
  query: '',
})

const resultTimeline = computed(() => {
  const rows = resultData.value?.timeline
  return Array.isArray(rows) ? rows : []
})

const resultComparisons = computed(() => {
  const rows = resultData.value?.comparisons
  return Array.isArray(rows) ? rows : []
})

const resultSources = computed(() => {
  const rows = resultData.value?.sources || resultData.value?.references
  return Array.isArray(rows) ? rows : []
})

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await getAnalysisHistory({ limit: 100, query: keyword.value.trim() || undefined })
    items.value = res?.items || []
  } catch (error) {
    console.error('加载历史记录失败:', error)
    items.value = []
  } finally {
    loading.value = false
  }
}

const toggleResult = async (sessionId: string) => {
  if (selectedSessionId.value === sessionId) {
    // 收起
    selectedSessionId.value = null
    resultData.value = null
    resultError.value = ''
    return
  }

  // 展开并加载结果
  selectedSessionId.value = sessionId
  resultLoading.value = true
  resultError.value = ''
  resultData.value = null

  try {
    const result = await getAnalysisResult(sessionId)
    resultData.value = result
  } catch (error: any) {
    console.error('加载结果失败:', error)
    resultError.value = error?.response?.data?.detail || '加载结果失败，请稍后重试'
  } finally {
    resultLoading.value = false
  }
}

const confirmDelete = (sessionId: string, query: string) => {
  deleteConfirm.value = {
    show: true,
    sessionId,
    query,
  }
}

const cancelDelete = () => {
  deleteConfirm.value = {
    show: false,
    sessionId: '',
    query: '',
  }
}

const executeDelete = async () => {
  const sessionId = deleteConfirm.value.sessionId
  cancelDelete()

  try {
    await deleteAnalysisHistory(sessionId)
    
    // 从列表中移除
    items.value = items.value.filter(item => item.session_id !== sessionId)
    
    // 如果当前正在查看该记录，关闭详情
    if (selectedSessionId.value === sessionId) {
      selectedSessionId.value = null
      resultData.value = null
      resultError.value = ''
    }
  } catch (error: any) {
    console.error('删除失败:', error)
    alert(error?.response?.data?.detail || '删除失败，请稍后重试')

  // 展开并加载结果
  selectedSessionId.value = sessionId
  resultLoading.value = true
  resultError.value = ''
  resultData.value = null

  try {
    const result = await getAnalysisResult(sessionId)
    resultData.value = result
  } catch (error: any) {
    console.error('加载结果失败:', error)
    resultError.value = error?.response?.data?.detail || '加载结果失败，请稍后重试'
  } finally {
    resultLoading.value = false
  }
}

const formatDate = (value?: string | null) => {
  if (!value) return '未知时间'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '未知时间' : d.toLocaleString()
}

const statusText = (status: string) => {
  if (status === 'completed') return '已完成'
  if (status === 'error') return '失败'
  if (status === 'analyzing' || status === 'running') return '分析中'
  return status || '未知'
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.history-shell {
  color: #dbeafe;
}

.history-eyebrow {
  display: inline-block;
  padding: 0.3rem 0.62rem;
  border: 1px solid rgba(103, 232, 249, 0.36);
  border-radius: 9999px;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #a5f3fc;
  background: rgba(8, 29, 56, 0.75);
}

.history-search {
  width: 100%;
  min-width: 240px;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 0.65rem;
  padding: 0.55rem 0.75rem;
  color: #e2e8f0;
  background: rgba(7, 19, 42, 0.82);
}

.history-btn,
.history-btn-sm {
  border: 1px solid rgba(103, 232, 249, 0.4);
  border-radius: 0.65rem;
  color: #cffafe;
  background: rgba(6, 36, 66, 0.82);
  transition: all 0.2s;
}

.history-btn {
  padding: 0.55rem 0.9rem;
}

.history-btn-sm {
  padding: 0.4rem 0.75rem;
  font-size: 0.84rem;
  white-space: nowrap;
}

.history-btn-delete {
  padding: 0.4rem 0.75rem;
  font-size: 0.84rem;
  white-space: nowrap;
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 0.65rem;
  color: #fca5a5;
  background: rgba(127, 29, 29, 0.3);
  transition: all 0.2s;
}

.history-btn-delete:hover {
  border-color: rgba(239, 68, 68, 0.7);
  background: rgba(127, 29, 29, 0.5);
  color: #fecaca;
}

.history-btn:hover,
.history-btn-sm:hover {
  border-color: rgba(103, 232, 249, 0.62);
  background: rgba(8, 48, 86, 0.9);
}

.btn-active {
  border-color: rgba(56, 189, 248, 0.7);
  background: rgba(14, 116, 144, 0.4);
  color: #ecfeff;
}

.history-item {
  border: 1px solid rgba(148, 163, 184, 0.23);
  border-radius: 0.78rem;
  background: rgba(8, 21, 43, 0.76);
  padding: 0.8rem 0.9rem;
  transition: all 0.25s;
}

.history-item:hover {
  border-color: rgba(103, 232, 249, 0.28);
  background: rgba(8, 21, 43, 0.88);
}

.query-line {
  font-weight: 700;
  color: #e2e8f0;
}

.summary-line {
  margin-top: 0.35rem;
  color: #cbd5e1;
  font-size: 0.9rem;
  line-height: 1.5;
}

.meta-line {
  margin-top: 0.45rem;
  color: #9fb4cf;
  font-size: 0.78rem;
}

.empty-wrap {
  padding: 1.3rem 0.8rem;
  text-align: center;
  color: #9fb4cf;
}

/* 结果详情展开区域 */
.result-detail {
  border-top: 1px solid rgba(103, 232, 249, 0.18);
  padding-top: 1rem;
  margin-top: 1rem;
}

.result-loading,
.result-error {
  padding: 1rem;
  text-align: center;
  border-radius: 0.5rem;
}

.result-loading {
  color: #a5f3fc;
  background: rgba(6, 36, 66, 0.5);
}

.result-error {
  color: #fca5a5;
  background: rgba(127, 29, 29, 0.3);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.result-section {
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 0.62rem;
  background: rgba(15, 23, 42, 0.6);
  padding: 0.9rem 1rem;
}

.result-section-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: #a5f3fc;
  margin-bottom: 0.6rem;
  letter-spacing: 0.02em;
}

.result-text {
  color: #cbd5e1;
  line-height: 1.6;
  font-size: 0.9rem;
}

.timeline-list,
.compare-list,
.source-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.timeline-row,
.compare-row,
.source-row {
  display: flex;
  gap: 0.75rem;
  padding: 0.5rem 0.6rem;
  border-radius: 0.4rem;
  background: rgba(8, 21, 43, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 0.85rem;
}

.timeline-date,
.compare-dim {
  flex-shrink: 0;
  font-weight: 600;
  color: #7dd3fc;
  min-width: 6rem;
}

.timeline-event,
.compare-detail {
  color: #cbd5e1;
  line-height: 1.5;
}

.source-title {
  font-weight: 600;
  color: #7dd3fc;
  flex-shrink: 0;
  min-width: 8rem;
}

.source-link {
  color: #a5f3fc;
  text-decoration: none;
  word-break: break-all;
  font-size: 0.8rem;
}

.source-link:hover {
  color: #ecfeff;
  text-decoration: underline;
}

@media (max-width: 768px) {
  .history-search {
    min-width: 0;
  }

  .timeline-row,
  .compare-row,
  .source-row {
    flex-direction: column;
    gap: 0.3rem;
  }

  .timeline-date,
  .compare-dim,
  .source-title {
    min-width: auto;
  }
}

/* 删除确认对话框 */
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.confirm-dialog {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(7, 19, 42, 0.95));
  border: 1px solid rgba(103, 232, 249, 0.3);
  border-radius: 1rem;
  padding: 1.5rem;
  max-width: 28rem;
  width: 90%;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  animation: slideIn 0.25s ease;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.confirm-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 0.8rem;
}

.confirm-message {
  color: #cbd5e1;
  margin-bottom: 0.6rem;
  line-height: 1.5;
}

.confirm-query {
  color: #a5f3fc;
  font-weight: 600;
  padding: 0.6rem 0.8rem;
  background: rgba(6, 36, 66, 0.5);
  border-radius: 0.5rem;
  border: 1px solid rgba(103, 232, 249, 0.2);
  margin-bottom: 1.2rem;
  word-break: break-word;
}

.confirm-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.confirm-btn {
  padding: 0.5rem 1.2rem;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.confirm-btn-cancel {
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(15, 23, 42, 0.6);
  color: #cbd5e1;
}

.confirm-btn-cancel:hover {
  border-color: rgba(148, 163, 184, 0.6);
  background: rgba(15, 23, 42, 0.8);
  color: #e2e8f0;
}

.confirm-btn-delete {
  border: 1px solid rgba(239, 68, 68, 0.6);
  background: rgba(127, 29, 29, 0.6);
  color: #fecaca;
}

.confirm-btn-delete:hover {
  border-color: rgba(239, 68, 68, 0.8);
  background: rgba(127, 29, 29, 0.8);
  color: #fee2e2;
}
</style>
