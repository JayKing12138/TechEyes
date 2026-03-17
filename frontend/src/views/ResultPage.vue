<template>
  <div class="admin-root min-h-screen techeyes-page-shell">
    <div v-if="loading" class="loading-wrap">
      <div class="spinner"></div>
      <p>正在加载分析结果...</p>
    </div>

    <div v-else-if="result" class="admin-layout">
      <aside class="admin-sidebar">
        <div class="sidebar-brand">
          <div class="brand-dot"></div>
          <div>
            <p class="brand-name">TechEyes</p>
            <p class="brand-sub">风险驾驶舱</p>
          </div>
        </div>

        <nav class="sidebar-nav">
          <button
            v-for="module in modules"
            :key="module.id"
            @click="activeModule = module.id"
            :class="['nav-item', activeModule === module.id ? 'nav-item-active' : '']"
          >
            <span class="nav-dot"></span>
            <span>{{ module.label }}</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <button class="ghost-btn" @click="router.push('/')">返回首页</button>
        </div>
      </aside>

      <main class="admin-main">
        <header class="topbar">
          <div>
            <h1 class="topbar-title">{{ dashboardTitle }}</h1>
            <p class="topbar-sub">{{ dashboardSummary }}</p>
          </div>

          <div class="topbar-actions">
            <input class="search-input" placeholder="搜索模块或企业..." />
            <div class="status-chip">已完成</div>
          </div>
        </header>

        <section class="metrics-grid">
          <article class="metric-card metric-danger">
            <p class="metric-title">高危告警</p>
            <p class="metric-number">{{ highAlertCount }}</p>
            <p class="metric-desc">需要立即处理</p>
          </article>
          <article class="metric-card metric-blue">
            <p class="metric-title">观察名单</p>
            <p class="metric-number">{{ watchListItems.length }}</p>
            <p class="metric-desc">重点跟踪企业</p>
          </article>
          <article class="metric-card metric-green">
            <p class="metric-title">风险信号</p>
            <p class="metric-number">{{ references.length }}</p>
            <p class="metric-desc">外部数据来源</p>
          </article>
          <article class="metric-card metric-orange">
            <p class="metric-title">未来场景</p>
            <p class="metric-number">{{ scenarios.length }}</p>
            <p class="metric-desc">趋势推演结果</p>
          </article>
        </section>

        <section class="module-panel">
          <div v-if="activeModule === 'overview'" class="space-y-5">
            <h3 class="panel-title">总体概览</h3>
            <div class="overview-grid">
              <article class="white-card">
                <p class="white-card-title">核心结论</p>
                <p class="white-card-text">{{ summaryData.text }}</p>
              </article>
              <article class="white-card">
                <p class="white-card-title">风险分布</p>
                <div class="space-y-3 mt-3">
                  <div class="progress-row">
                    <span>高风险</span>
                    <div class="progress-track"><div class="progress-bar bar-red" :style="{ width: `${Math.min(100, highAlertCount * 16)}%` }"></div></div>
                  </div>
                  <div class="progress-row">
                    <span>中风险</span>
                    <div class="progress-track"><div class="progress-bar bar-yellow" :style="{ width: `${Math.min(100, mediumAlertCount * 16)}%` }"></div></div>
                  </div>
                  <div class="progress-row">
                    <span>低风险</span>
                    <div class="progress-track"><div class="progress-bar bar-green" :style="{ width: `${Math.min(100, safeCount * 18)}%` }"></div></div>
                  </div>
                </div>
              </article>
            </div>
          </div>

          <div v-else-if="activeModule === 'alerts'" class="space-y-4">
            <h3 class="panel-title">高危告警</h3>
            <article
              v-for="(item, idx) in alertItems"
              :key="`${item.title}-${idx}`"
              :class="['alert-item', item.level === 'high' ? 'alert-item-high' : 'alert-item-medium']"
            >
              <div class="alert-head">
                <h4>{{ item.title }}</h4>
                <span class="alert-pill">{{ item.tag }}</span>
              </div>
              <p class="alert-main">{{ item.description }}</p>
              <p class="alert-evidence">{{ item.evidence }}</p>
            </article>
            <p v-if="alertItems.length === 0" class="empty-tip">暂无告警。</p>
          </div>

          <div v-else-if="activeModule === 'watchlist'">
            <h3 class="panel-title mb-3">观察名单</h3>
            <div class="table-shell">
              <table class="module-table">
                <thead>
                  <tr>
                    <th>企业</th>
                    <th>风险分</th>
                    <th>研判说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in watchListItems" :key="`${row.name}-${idx}`">
                    <td>{{ row.name }}</td>
                    <td class="score-text">{{ row.score }}%</td>
                    <td>{{ row.analysis }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else-if="activeModule === 'comparisons'" class="space-y-4">
            <h3 class="panel-title">对比分析</h3>
            <article v-for="(group, idx) in normalizedComparisons" :key="`${group.dimension}-${idx}`" class="white-card">
              <p class="white-card-title">{{ group.dimension }}</p>
              <p class="text-sm text-slate-300 mb-3">{{ group.dimensionDescription }}</p>
              <div class="space-y-2">
                <div v-for="(row, rowIdx) in group.rows" :key="`${row.name}-${rowIdx}`" class="compare-row">
                  <div class="compare-meta">
                    <span>{{ row.name }}</span>
                    <span class="score-text">{{ row.score }}%</span>
                  </div>
                  <div class="progress-track"><div class="progress-bar bar-blue" :style="{ width: `${Math.min(100, row.score)}%` }"></div></div>
                </div>
              </div>
            </article>
          </div>

          <div v-else-if="activeModule === 'timeline'" class="space-y-3">
            <h3 class="panel-title">风险时间线</h3>
            <article v-for="(event, idx) in timelineData" :key="`${event.title}-${idx}`" class="timeline-item">
              <div class="timeline-date">{{ event.date }}</div>
              <div>
                <p class="font-semibold text-slate-100">{{ event.title }}</p>
                <p class="text-sm text-slate-300 mt-1">{{ event.description }}</p>
              </div>
            </article>
          </div>

          <div v-else-if="activeModule === 'future'" class="space-y-4">
            <h3 class="panel-title">趋势展望</h3>
            <div class="overview-grid">
              <article class="white-card">
                <p class="white-card-title">未来场景</p>
                <ul class="space-y-2 mt-2 text-sm text-slate-200">
                  <li v-for="(scenario, idx) in scenarios" :key="`${scenario.name}-${idx}`">
                    {{ scenario.name }} ({{ formatProbability(scenario.probability) }})
                  </li>
                </ul>
              </article>
              <article class="white-card">
                <p class="white-card-title">行动建议</p>
                <ul class="space-y-2 mt-2 text-sm text-slate-200">
                  <li v-for="(item, idx) in recommendations" :key="`${item}-${idx}`">{{ item }}</li>
                </ul>
              </article>
            </div>
          </div>

          <div v-else-if="activeModule === 'sources'" class="space-y-3">
            <h3 class="panel-title">数据来源</h3>
            <article v-for="(refItem, idx) in references" :key="`${refItem.title}-${idx}`" class="white-card">
              <a :href="refItem.url || '#'" target="_blank" class="source-link">
                <p class="white-card-title">{{ refItem.title || '未命名来源' }}</p>
                <p class="text-xs text-slate-400 mt-1">{{ refItem.source || '未知来源' }} · {{ refItem.date || '-' }}</p>
                <p class="text-sm text-slate-200 mt-2">{{ refItem.snippet || '无摘要信息' }}</p>
              </a>
            </article>
          </div>
        </section>
      </main>
    </div>

    <div v-else class="loading-wrap">
      <p>未找到分析结果</p>
      <button class="ghost-btn mt-3" @click="router.push('/')">返回首页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getAnalysisResult } from '@/services/api'

interface Props {
  sessionId: string
}

interface AlertItem {
  title: string
  description: string
  evidence: string
  level: 'high' | 'medium'
  tag: string
}

interface NormalizedComparisonRow {
  name: string
  score: number
  value: string | number
  analysis: string
}

interface NormalizedComparisonGroup {
  dimension: string
  dimensionDescription: string
  rows: NormalizedComparisonRow[]
}

const props = defineProps<Props>()
const router = useRouter()

const loading = ref(true)
const result = ref<any | null>(null)
const activeModule = ref('overview')

const modules = [
  { id: 'overview', label: '总体概览' },
  { id: 'alerts', label: '高危告警' },
  { id: 'watchlist', label: '观察名单' },
  { id: 'comparisons', label: '对比分析' },
  { id: 'timeline', label: '风险时间线' },
  { id: 'future', label: '趋势展望' },
  { id: 'sources', label: '数据来源' },
]

const summaryData = computed(() => {
  const summary = result.value?.summary
  if (typeof summary === 'string') {
    return {
      title: '风险驾驶舱',
      text: summary,
    }
  }

  return {
    title: summary?.title || '风险驾驶舱',
    text: summary?.executive_summary || summary?.summary || '分析已完成，可通过左侧导航查看各模块信息。',
  }
})

const dashboardTitle = computed(() => summaryData.value.title)
const dashboardSummary = computed(() => summaryData.value.text)

const timelineData = computed(() => result.value?.timeline || [])
const futureData = computed(() => result.value?.future_outlook || result.value?.futureOutlook || {})
const scenarios = computed(() => futureData.value?.scenarios || [])
const recommendations = computed(() => futureData.value?.recommendations || [])
const references = computed(() => result.value?.references || result.value?.sources || [])

const normalizedComparisons = computed<NormalizedComparisonGroup[]>(() => {
  const raw = result.value?.comparisons || []
  return raw.map((item: any) => {
    const sourceRows = item?.company_comparisons || item?.companies || []
    const rows = sourceRows.map((company: any) => ({
      name: company?.company || company?.name || '未知企业',
      score: Number(company?.score || 0),
      value: company?.value || '-',
      analysis: company?.analysis || item?.analysis || '暂无研判说明',
    }))

    return {
      dimension: item?.dimension || '对比维度',
      dimensionDescription: item?.description || item?.dimension_description || '暂无维度描述',
      rows,
    }
  })
})

const watchListItems = computed(() => {
  const rows = normalizedComparisons.value.flatMap((group) => group.rows)
  return rows
    .sort((a, b) => b.score - a.score)
    .slice(0, 12)
})

const alertItems = computed<AlertItem[]>(() => {
  return watchListItems.value.slice(0, 6).map((item, idx) => {
    const highRisk = item.score >= 75 || idx < 2
    return {
      title: `${item.name} 风险预警`,
      description: `当前风险评分 ${item.score}% ，建议重点关注交付连续性与合规风险。`,
      evidence: item.analysis,
      level: highRisk ? 'high' : 'medium',
      tag: highRisk ? '高危' : '中危',
    }
  })
})

const highAlertCount = computed(() => alertItems.value.filter((item) => item.level === 'high').length)
const mediumAlertCount = computed(() => alertItems.value.filter((item) => item.level === 'medium').length)
const safeCount = computed(() => Math.max(watchListItems.value.length - highAlertCount.value - mediumAlertCount.value, 0))

const formatProbability = (value: number | string) => {
  if (typeof value === 'string') return value
  if (value <= 1) return `${Math.round(value * 100)}%`
  return `${Math.round(value)}%`
}

onMounted(async () => {
  try {
    result.value = await getAnalysisResult(props.sessionId)
  } catch (error) {
    console.error('获取结果失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.admin-root {
  color: #dbeafe;
}

.admin-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 250px 1fr;
}

.admin-sidebar {
  background: linear-gradient(180deg, rgba(7, 21, 45, 0.95) 0%, rgba(10, 24, 50, 0.9) 100%);
  color: #dbeafe;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(125, 211, 252, 0.2);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 1.2rem 1rem;
  border-bottom: 1px solid rgba(125, 211, 252, 0.16);
}

.brand-dot {
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 9999px;
  background: #22d3ee;
}

.brand-name {
  font-size: 1.3rem;
  font-weight: 800;
  line-height: 1.1;
}

.brand-sub {
  font-size: 0.76rem;
  color: #93c5fd;
}

.sidebar-nav {
  padding: 0.8rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  border: none;
  background: transparent;
  color: #cbd5e1;
  border-radius: 0.6rem;
  padding: 0.62rem 0.7rem;
  text-align: left;
  cursor: pointer;
}

.nav-item:hover {
  background: rgba(8, 31, 57, 0.54);
}

.nav-item-active {
  background: linear-gradient(120deg, rgba(6, 182, 212, 0.34), rgba(37, 99, 235, 0.46));
  color: #ecfeff;
}

.nav-dot {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 9999px;
  background: currentColor;
}

.sidebar-footer {
  margin-top: auto;
  padding: 1rem;
}

.admin-main {
  padding: 1rem;
}

.topbar {
  background: rgba(10, 25, 52, 0.9);
  border-radius: 0.75rem;
  border: 1px solid rgba(125, 211, 252, 0.24);
  padding: 1rem 1.1rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.85rem;
}

.topbar-title {
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1.1;
  color: #dff8ff;
}

.topbar-sub {
  margin-top: 0.3rem;
  font-size: 0.9rem;
  color: #a9bfd9;
  max-width: 46rem;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.search-input {
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 0.5rem;
  padding: 0.45rem 0.75rem;
  min-width: 200px;
  color: #dbeafe;
  background: rgba(6, 17, 40, 0.75);
}

.status-chip {
  font-size: 0.75rem;
  border-radius: 9999px;
  padding: 0.24rem 0.6rem;
  background: rgba(16, 185, 129, 0.16);
  color: #86efac;
  border: 1px solid rgba(16, 185, 129, 0.32);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.metric-card {
  border-radius: 0.7rem;
  color: #ffffff;
  padding: 0.9rem 0.95rem;
  box-shadow: 0 5px 15px rgba(15, 23, 42, 0.08);
}

.metric-danger { background: #ef6f65; }
.metric-blue { background: #6a88c6; }
.metric-green { background: #52b7b2; }
.metric-orange { background: #d7a55d; }

.metric-title {
  font-size: 0.77rem;
  opacity: 0.92;
}

.metric-number {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.1;
  margin-top: 0.28rem;
}

.metric-desc {
  margin-top: 0.2rem;
  font-size: 0.74rem;
  opacity: 0.95;
}

.module-panel {
  background: rgba(10, 25, 52, 0.9);
  border-radius: 0.8rem;
  border: 1px solid rgba(125, 211, 252, 0.2);
  padding: 1rem;
  min-height: 420px;
}

.panel-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #e0f2fe;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.white-card {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.75rem;
  background: rgba(6, 18, 40, 0.72);
  padding: 0.9rem;
}

.white-card-title {
  font-weight: 700;
  color: #e2e8f0;
}

.white-card-text {
  margin-top: 0.45rem;
  font-size: 0.92rem;
  color: #cbd5e1;
  line-height: 1.6;
}

.progress-row {
  display: grid;
  grid-template-columns: 70px 1fr;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: #9fb4cf;
}

.progress-track {
  width: 100%;
  background: rgba(15, 23, 42, 0.72);
  border-radius: 9999px;
  height: 8px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: inherit;
}

.bar-red { background: #ef4444; }
.bar-yellow { background: #f59e0b; }
.bar-green { background: #22c55e; }
.bar-blue { background: #3b82f6; }

.alert-item {
  border-radius: 0.75rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(8, 20, 44, 0.74);
  padding: 0.9rem;
}

.alert-item-high { border-left: 4px solid #ef4444; }
.alert-item-medium { border-left: 4px solid #f59e0b; }

.alert-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.alert-head h4 {
  font-weight: 700;
  color: #e2e8f0;
}

.alert-pill {
  font-size: 0.72rem;
  padding: 0.16rem 0.5rem;
  border-radius: 9999px;
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.alert-main {
  margin-top: 0.55rem;
  font-size: 0.9rem;
  color: #cbd5e1;
}

.alert-evidence {
  margin-top: 0.35rem;
  font-size: 0.82rem;
  color: #9fb4cf;
}

.table-shell {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 0.75rem;
  overflow: auto;
}

.module-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.module-table thead {
  background: rgba(8, 24, 50, 0.92);
}

.module-table th,
.module-table td {
  text-align: left;
  padding: 0.7rem 0.75rem;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
  color: #dbeafe;
}

.module-table th {
  border-top: none;
  color: #a9bfd9;
  font-weight: 600;
}

.score-text {
  font-weight: 700;
  color: #2563eb;
}

.compare-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.35rem;
}

.compare-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.88rem;
  color: #dbeafe;
}

.timeline-item {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.75rem;
  padding: 0.85rem;
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.7rem;
  background: rgba(8, 20, 44, 0.72);
}

.timeline-date {
  font-size: 0.8rem;
  color: #a9bfd9;
  font-weight: 600;
}

.source-link {
  color: inherit;
  text-decoration: none;
}

.source-link:hover .white-card-title {
  color: #7dd3fc;
}

.loading-wrap {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #cbd5e1;
}

.spinner {
  width: 40px;
  height: 40px;
  border-radius: 9999px;
  border: 4px solid #cbd5e1;
  border-top-color: #2563eb;
  animation: spin 0.7s linear infinite;
}

.ghost-btn {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 0.55rem;
  padding: 0.45rem 0.7rem;
  background: rgba(8, 21, 43, 0.86);
  color: #dbeafe;
}

.ghost-btn:hover {
  background: rgba(10, 33, 62, 0.95);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1100px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .admin-sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
  }

  .nav-item {
    white-space: nowrap;
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .topbar-actions {
    width: 100%;
  }

  .search-input {
    flex: 1;
    min-width: 0;
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }

  .timeline-item {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
