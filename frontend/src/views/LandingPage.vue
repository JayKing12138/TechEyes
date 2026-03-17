<template>
  <div class="landing-shell min-h-screen">
    <div class="graph-mesh" aria-hidden="true"></div>
    <div class="landing-orb landing-orb-left" aria-hidden="true"></div>
    <div class="landing-orb landing-orb-right" aria-hidden="true"></div>
    <Header />
    
    <!-- Hero Section -->
    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-36 pb-20 md:pb-24 relative">
      <div class="max-w-5xl mx-auto text-center relative z-10">
        <p
          class="eyebrow animate-fade-in"
          style="animation-delay: 0.05s"
        >
          AI Trend Intelligence Platform
        </p>

        <h1 
          class="text-5xl md:text-7xl font-black mb-6 md:mb-8 tracking-tight leading-[1.05] animate-fade-in"
          style="animation-delay: 0.1s"
        >
          <span class="text-gradient">TechEyes</span>
        </h1>
        
        <p 
          class="mx-auto max-w-3xl text-lg md:text-2xl text-slate-200/90 mb-10 md:mb-14 animate-fade-in"
          style="animation-delay: 0.2s"
        >
          Multi-Agent AI 驱动的科技行业智能分析平台
        </p>

        <!-- Search Bar -->
        <div
          class="max-w-4xl mx-auto animate-fade-in"
          style="animation-delay: 0.3s"
        >
          <SearchBar 
            :loading="loading"
            @attach="handleAttach"
            @submit="handleSearch"
          />

          <div v-if="attachedFile" class="mt-4 text-sm text-cyan-200">
            已挂载文档: {{ attachedFile.name }} ({{ formatBytes(attachedFile.size) }})
          </div>
        </div>

        <div v-if="loading" class="thinking-panel mt-7 text-left">
          <p class="thinking-title">推理执行中 (CoT + Reflection)</p>
          <div class="space-y-2 mt-3">
            <div
              v-for="(entry, index) in visibleThinkingLogs"
              :key="`${entry.agent}-${index}`"
              class="thinking-row"
            >
              <span class="thinking-agent">[{{ entry.agent }}]</span>
              <span class="thinking-msg">{{ entry.message }}</span>
            </div>
            <div v-if="visibleThinkingLogs.length === 0" class="thinking-row skeleton-row">正在构建任务骨架...</div>
          </div>
        </div>

        <section v-if="resultLoading || resultError || latestResult" class="inline-result mt-8 text-left">
          <div v-if="resultLoading" class="inline-loading">正在生成分析结果，请稍候...</div>
          <div v-else-if="resultError" class="inline-error">{{ resultError }}</div>

          <template v-else-if="latestResult">
            <h3 class="inline-title">分析结果</h3>
            <p class="inline-summary">{{ latestResult.summary || '暂无摘要' }}</p>

            <div v-if="inlineTimeline.length > 0" class="inline-block mt-4">
              <p class="inline-block-title">关键时间线</p>
              <ul class="inline-list">
                <li v-for="(item, idx) in inlineTimeline.slice(0, 6)" :key="`timeline-${idx}`" class="inline-list-item">
                  <span class="inline-list-key">{{ item.date || '时间未知' }}</span>
                  <span>{{ item.event || item.title || item.description || '无详细内容' }}</span>
                </li>
              </ul>
            </div>

            <div v-if="inlineComparisons.length > 0" class="inline-block mt-4">
              <p class="inline-block-title">对比分析</p>
              <ul class="inline-list">
                <li v-for="(item, idx) in inlineComparisons.slice(0, 6)" :key="`comp-${idx}`" class="inline-list-item">
                  <span class="inline-list-key">{{ item.dimension || `维度 ${idx + 1}` }}</span>
                  <span>{{ item.details || item.analysis || '无详细内容' }}</span>
                </li>
              </ul>
            </div>

            <div v-if="latestResult.futureOutlook" class="inline-block mt-4">
              <p class="inline-block-title">未来展望</p>
              <p class="inline-paragraph">{{ latestResult.futureOutlook }}</p>
            </div>

            <div v-if="inlineSources.length > 0" class="inline-block mt-4">
              <p class="inline-block-title">信息来源</p>
              <ul class="inline-list">
                <li v-for="(item, idx) in inlineSources.slice(0, 5)" :key="`src-${idx}`" class="inline-list-item">
                  <span class="inline-list-key">{{ item.title || '未命名来源' }}</span>
                  <a
                    v-if="item.url"
                    class="inline-link"
                    :href="item.url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ item.url }}
                  </a>
                  <span v-else>无链接</span>
                </li>
              </ul>
            </div>
          </template>
        </section>

        <!-- Search History -->
        <div
          v-if="searchHistory.length > 0"
          class="mt-8 md:mt-10 animate-fade-in"
          style="animation-delay: 0.4s"
        >
          <p class="text-xs tracking-[0.22em] uppercase text-slate-400 mb-3">最近搜索</p>
          <div class="flex flex-wrap gap-2 justify-center">
            <button
              v-for="query in searchHistory.slice(0, 5)"
              :key="query"
              @click="handleQuickSearch(query)"
              class="px-4 py-2 rounded-full text-sm border border-white/15 bg-slate-800/50 hover:bg-slate-700/60 hover:border-cyan-300/40 transition-all"
            >
              {{ query }}
            </button>
          </div>
        </div>
      </div>

      <!-- Features Section -->
      <section
        id="features"
        class="grid md:grid-cols-3 gap-5 md:gap-7 mt-16 md:mt-24 max-w-6xl mx-auto animate-fade-in"
        style="animation-delay: 0.5s"
      >
        <div 
          v-for="(feature, index) in features"
          :key="feature.title"
          class="feature-card p-6 md:p-7 rounded-2xl transition-all duration-300 cursor-pointer"
          :class="selectedFeature === feature.id ? 'feature-active' : ''"
          @click="handleFeatureClick(feature)"
          :style="{ animationDelay: `${0.6 + index * 0.1}s` }"
        >
          <div class="feature-index mb-5">{{ feature.index }}</div>
          <h3 class="text-xl md:text-2xl font-bold mb-3 text-cyan-300">{{ feature.title }}</h3>
          <p class="text-slate-300/85 text-sm md:text-base leading-relaxed">{{ feature.description }}</p>
          <p class="text-cyan-200/90 text-sm mt-3">{{ feature.liveMetric }}</p>

          <div v-if="feature.id === 'agents'" class="status-lights mt-4">
            <span
              v-for="agent in agentStatus"
              :key="agent.name"
              class="status-item"
            >
              <i :class="agent.ready ? 'light-on' : 'light-off'"></i>
              {{ agent.name }}
            </span>
          </div>

          <div v-if="feature.id === 'mcp'" class="status-lights mt-4">
            <span class="status-item"><i class="light-on"></i>Google Search</span>
            <span class="status-item"><i class="light-on"></i>GitHub</span>
            <span class="status-item"><i class="light-on"></i>Local PDF</span>
          </div>
        </div>
      </section>

      <section v-if="activeFeatureDetail" class="max-w-6xl mx-auto mt-6 detail-card">
        <h4 class="text-lg font-bold text-cyan-200">{{ activeFeatureDetail.detailTitle }}</h4>
        <p class="text-slate-300/90 mt-2">{{ activeFeatureDetail.detailText }}</p>
      </section>

      <!-- Memory Vault - Floating Button -->
      <!-- <div class="memory-vault">
        <div class="vault-body">
          <h4 class="vault-title">Memory Vault</h4>
          <p class="vault-sub">短期记忆</p>
          <p class="vault-text">Session: {{ sessionLabel }}</p>
          <p class="vault-text">最近文档: {{ attachedFile ? attachedFile.name : '暂无文档' }}</p>

          <p class="vault-sub mt-4">长期记忆</p>
          <p class="vault-text">基于偏好：已优先关注商业量产指标、供应链稳定性和政策风险。</p>
        </div>
      </div> -->

      <!-- Log Drawer - Sidebar Hover -->
      <!-- <div class="log-drawer">
        <div class="log-tab">Log</div>
        <div class="log-content">
          <h4 class="log-title">A2A / MCP 原始流</h4>
          <pre class="log-pre">{{ logDump }}</pre>
        </div>
      </div> -->
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '@/stores/analysis'
import SearchBar from '@/components/SearchBar.vue'
import Header from '@/components/Header.vue'
import { submitAnalysis, getAnalysisResult, getAnalysisProgress } from '@/services/api'

const router = useRouter()

const store = useAnalysisStore()

const loading = ref(false)
const resultLoading = ref(false)
const resultError = ref('')
const latestResult = ref<any | null>(null)
const searchHistory = computed(() => store.searchHistory)
const attachedFile = ref<File | null>(null)
const selectedFeature = ref('agents')
const visibleThinkingLogs = ref<Array<{ agent: string; message: string }>>([])
let thinkingTimer: ReturnType<typeof setInterval> | null = null

const sessionLabel = computed(() => store.analysisState?.session_id || 'not-started')

const baseThinkingLogs = [
  { agent: 'Planner', message: '正在拆解任务为 3 个子目标并生成执行图...' },
  { agent: 'Historian', message: '正在通过 MCP 调取 2022-2024 行业数据...' },
  { agent: 'Researcher', message: '正在抓取最新新闻与财报摘要，构建证据链...' },
  { agent: 'Logic Check', message: '发现信源冲突，正在启动自纠错机制 (Reflection)...' },
  { agent: 'Synthesizer', message: '正在聚合结论并组织结构化输出...' },
]

const agentStatus = [
  { name: 'Orchestrator', ready: true },
  { name: 'Researcher', ready: true },
  { name: 'Analyzer', ready: true },
  { name: 'Critic', ready: true },
  { name: 'Synthesizer', ready: true },
]

const features = [
  {
    id: 'agents',
    index: '01',
    title: '智能决策问答',
    description: 'Multi-Agent协作分析，基于RAG和最新新闻，提供深度行业洞察',
    liveMetric: '活跃 Agent: 5/5 就绪',
    detailTitle: 'Agent 实时分工状态',
    detailText: '任务被拆解后，Planner 将子任务广播到研究、分析和质检链路，最终由 Synthesizer 汇总为结构化结论。',
  },
  {
    id: 'cache',
    index: '02',
    title: '项目知识工作台',
    description: '创建独立分析项目，上传文档，构建专属知识库，支持长期对话',
    liveMetric: '今日已节省 14,200 Tokens',
    detailTitle: '项目知识库管理',
    detailText: '每个项目独立管理文档和对话历史，支持文档上传、向量检索和项目级记忆，实现专业领域的深度分析。',
  },
  {
    id: 'mcp',
    index: '03',
    title: '科技新闻雷达',
    description: '实时追踪科技动态，智能分析实体关系，支持按图索骥和雷达报告',
    liveMetric: '已收录 1,234 条新闻',
    detailTitle: '新闻雷达系统',
    detailText: '基于Neo4j图数据库构建新闻实体关系网络，支持新闻热榜、实体图谱、按图索骥分析和雷达报告生成。',
    link: '/radar'
  },
]

const activeFeatureDetail = computed(() => features.find((item) => item.id === selectedFeature.value))

const logDump = computed(() => {
  const payload = visibleThinkingLogs.value.map((item, index) => ({
    seq: index + 1,
    protocol: index % 2 === 0 ? 'A2A' : 'MCP',
    agent: item.agent,
    message: item.message,
    timestamp: new Date().toISOString(),
  }))

  return JSON.stringify(payload, null, 2)
})

const inlineTimeline = computed(() => {
  const rows = latestResult.value?.timeline
  return Array.isArray(rows) ? rows : []
})

const inlineComparisons = computed(() => {
  const rows = latestResult.value?.comparisons
  return Array.isArray(rows) ? rows : []
})

const inlineSources = computed(() => {
  const rows = latestResult.value?.sources || latestResult.value?.references
  return Array.isArray(rows) ? rows : []
})

const isNotReadyResponse = (error: any) => {
  const status = error?.response?.status
  const detail = String(error?.response?.data?.detail || '')

  if (status === 404) return true
  if (status === 500 && /未完成|不存在|not\s*ready|not\s*found/i.test(detail)) return true
  return false
}

const waitForResult = async (sessionId: string, maxAttempts = 60, delayMs = 1500) => {
  for (let i = 0; i < maxAttempts; i += 1) {
    try {
      const result = await getAnalysisResult(sessionId)
      if (result) {
        return result
      }
    } catch (error: any) {
      // 分析尚未完成时，继续轮询
      if (!isNotReadyResponse(error)) {
        throw error
      }

      // 结果还未产出时，顺便检查是否已经进入错误状态
      try {
        const progress = await getAnalysisProgress(sessionId)
        if (progress?.status === 'error') {
          const reason = Array.isArray(progress?.errors) ? progress.errors[0] : ''
          throw new Error(reason || '搜索失败，请稍后重试')
        }
      } catch (progressError: any) {
        // 如果是我们主动抛出的错误，向外抛出结束轮询
        if (progressError instanceof Error && progressError.message) {
          throw progressError
        }
      }
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs))
  }

  throw new Error('分析超时，请稍后在历史记录中查看')
}

const startThinking = () => {
  visibleThinkingLogs.value = []
  let idx = 0

  if (thinkingTimer) {
    clearInterval(thinkingTimer)
    thinkingTimer = null
  }

  thinkingTimer = setInterval(() => {
    if (idx < baseThinkingLogs.length) {
      visibleThinkingLogs.value.push(baseThinkingLogs[idx])
      idx += 1
      return
    }

    if (thinkingTimer) {
      clearInterval(thinkingTimer)
      thinkingTimer = null
    }
  }, 850)
}

const stopThinking = () => {
  if (thinkingTimer) {
    clearInterval(thinkingTimer)
    thinkingTimer = null
  }
}

const handleSearch = async (query: string) => {
  if (!query.trim() || loading.value) return
  
  // 跳转到聊天页并携带搜索问题
  router.push({
    path: '/chat',
    query: { q: query.trim() }
  })
}

const handleQuickSearch = (query: string) => {
  handleSearch(query)
}

const handleFeatureClick = (feature: any) => {
  selectedFeature.value = feature.id
  if (feature.link) {
    router.push(feature.link)
  }
}

const handleAttach = (file: File) => {
  attachedFile.value = file
}

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onBeforeUnmount(() => {
  stopThinking()
})
</script>

<style scoped>
.landing-shell {
  position: relative;
  background:
    radial-gradient(1200px 800px at 20% 0%, rgba(34, 211, 238, 0.12), transparent 65%),
    radial-gradient(1000px 700px at 85% 20%, rgba(59, 130, 246, 0.14), transparent 62%),
    linear-gradient(130deg, #050a1b 0%, #091730 45%, #0a1230 100%);
  overflow: hidden;
}

.graph-mesh {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 1px 1px, rgba(125, 211, 252, 0.16) 1px, transparent 0),
    linear-gradient(110deg, transparent 0%, rgba(56, 189, 248, 0.08) 50%, transparent 100%);
  background-size: 24px 24px, 240px 240px;
  animation: meshShift 18s linear infinite;
  opacity: 0.35;
  pointer-events: none;
}

.landing-orb {
  position: absolute;
  width: 20rem;
  height: 20rem;
  border-radius: 9999px;
  filter: blur(70px);
  opacity: 0.4;
  pointer-events: none;
  animation: drift 10s ease-in-out infinite;
}

.landing-orb-left {
  left: -6rem;
  top: 8rem;
  background: rgba(34, 211, 238, 0.28);
}

.landing-orb-right {
  right: -5rem;
  bottom: 4rem;
  background: rgba(59, 130, 246, 0.24);
  animation-delay: 1.2s;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 1rem;
  padding: 0.35rem 0.7rem;
  border: 1px solid rgba(103, 232, 249, 0.35);
  border-radius: 9999px;
  background: rgba(13, 26, 54, 0.6);
  color: #a5f3fc;
  font-size: 0.72rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.feature-card {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: linear-gradient(155deg, rgba(11, 28, 56, 0.82), rgba(13, 35, 70, 0.55));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.feature-card:hover {
  transform: translateY(-6px);
  border-color: rgba(103, 232, 249, 0.45);
  box-shadow: 0 18px 38px rgba(4, 12, 28, 0.42);
}

.feature-active {
  border-color: rgba(125, 211, 252, 0.58);
  box-shadow: 0 16px 34px rgba(4, 14, 35, 0.46);
}

.feature-index {
  width: fit-content;
  padding: 0.24rem 0.55rem;
  border-radius: 0.55rem;
  border: 1px solid rgba(125, 211, 252, 0.5);
  background: rgba(8, 31, 57, 0.65);
  color: #7dd3fc;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  font-weight: 700;
}

.status-lights {
  display: flex;
  flex-wrap: wrap;
  gap: 0.42rem;
}

.status-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 9999px;
  font-size: 0.74rem;
  padding: 0.2rem 0.45rem;
  color: #dbeafe;
}

.light-on,
.light-off {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 9999px;
  display: inline-block;
}

.light-on {
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.65);
}

.light-off {
  background: #64748b;
}

.thinking-panel {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.95rem;
  background: rgba(7, 19, 45, 0.75);
  backdrop-filter: blur(10px);
  padding: 0.9rem 1rem;
}

.thinking-title {
  color: #7dd3fc;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.inline-result {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 1rem;
  background: rgba(7, 19, 45, 0.78);
  backdrop-filter: blur(10px);
  padding: 1rem 1.05rem;
}

.inline-loading,
.inline-error {
  color: #cbd5e1;
  font-size: 0.95rem;
}

.inline-error {
  color: #fda4af;
}

.inline-title {
  font-size: 1.2rem;
  font-weight: 800;
  color: #e0f2fe;
}

.inline-summary {
  margin-top: 0.5rem;
  color: #dbeafe;
  line-height: 1.68;
}

.inline-block {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 0.8rem;
  background: rgba(10, 23, 45, 0.6);
  padding: 0.75rem 0.8rem;
}

.inline-block-title {
  color: #7dd3fc;
  font-size: 0.86rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.inline-list {
  margin-top: 0.5rem;
  display: grid;
  gap: 0.5rem;
}

.inline-list-item {
  font-size: 0.9rem;
  color: #dbeafe;
  line-height: 1.55;
}

.inline-list-key {
  color: #67e8f9;
  font-weight: 700;
  margin-right: 0.45rem;
}

.inline-paragraph {
  margin-top: 0.48rem;
  color: #dbeafe;
  line-height: 1.64;
}

.inline-link {
  color: #7dd3fc;
  text-decoration: underline;
  word-break: break-all;
}

.thinking-row {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 0.65rem;
  padding: 0.45rem 0.6rem;
  background: rgba(15, 23, 42, 0.65);
  font-size: 0.85rem;
}

.thinking-agent {
  color: #67e8f9;
  font-weight: 700;
  margin-right: 0.38rem;
}

.thinking-msg {
  color: #dbeafe;
}

.skeleton-row {
  color: #93c5fd;
  animation: pulse 1.2s ease-in-out infinite;
}

.detail-card {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.95rem;
  padding: 0.95rem 1rem;
  background: rgba(10, 23, 45, 0.62);
}

/* Memory Vault - Floating Button (Right Side Upper) */
.memory-vault {
  position: fixed;
  right: 0;
  top: 35%;
  transform: translateX(calc(100% - 3rem));
  width: 20rem;
  max-width: calc(100vw - 2rem);
  z-index: 40;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.memory-vault:hover {
  transform: translateX(0);
}

.vault-body {
  border: 1px solid rgba(125, 211, 252, 0.35);
  border-right: none;
  border-radius: 0.85rem 0 0 0.85rem;
  background: rgba(8, 21, 43, 0.96);
  backdrop-filter: blur(16px);
  padding: 1rem;
  box-shadow: -6px 0 24px rgba(0, 0, 0, 0.3);
}

.vault-title {
  font-size: 1rem;
  font-weight: 700;
  color: #dff8ff;
  margin-bottom: 0.5rem;
}

.vault-sub {
  margin-top: 0.7rem;
  font-size: 0.76rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #7dd3fc;
  font-weight: 600;
}

.vault-text {
  margin-top: 0.3rem;
  color: #cbd5e1;
  font-size: 0.82rem;
  line-height: 1.5;
}

/* Log Drawer - Sidebar Hover (Right Side Lower) */
.log-drawer {
  position: fixed;
  right: 0;
  top: 55%;
  width: 28rem;
  max-width: calc(100vw - 2rem);
  max-height: 45vh;
  z-index: 40;
  transform: translateX(calc(100% - 3rem));
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.log-drawer:hover {
  transform: translateX(0);
}

.log-tab {
  position: absolute;
  left: 0;
  top: 0;
  width: 3rem;
  height: 6rem;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  border: 1px solid rgba(125, 211, 252, 0.4);
  border-right: none;
  border-radius: 0.65rem 0 0 0.65rem;
  background: rgba(8, 21, 43, 0.96);
  backdrop-filter: blur(16px);
  color: #67e8f9;
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  box-shadow: -6px 0 18px rgba(0, 0, 0, 0.25);
}

.log-content {
  position: absolute;
  right: 0;
  top: 0;
  width: calc(100% - 3rem);
  max-height: 50vh;
  overflow-y: auto;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-right: none;
  border-radius: 0.85rem 0 0 0.85rem;
  background: rgba(8, 18, 40, 0.97);
  backdrop-filter: blur(16px);
  padding: 1rem;
  box-shadow: -6px 0 24px rgba(0, 0, 0, 0.3);
}

.log-title {
  color: #67e8f9;
  font-weight: 700;
  margin-bottom: 0.6rem;
  font-size: 0.95rem;
}

.log-pre {
  color: #dbeafe;
  font-size: 0.74rem;
  line-height: 1.45;
  white-space: pre-wrap;
  font-family: 'Monaco', 'Courier New', monospace;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.6s ease-out forwards;
  opacity: 0;
}

@keyframes drift {
  0%, 100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(12px, -14px, 0) scale(1.05);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

@keyframes meshShift {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(0, -18px, 0);
  }
}

@media (max-width: 1024px) {
  .memory-vault {
    position: static;
    width: 100%;
    margin-top: 0.9rem;
  }

  .memory-open {
    width: 100%;
  }
}
</style>
