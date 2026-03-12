<template>
  <div class="min-h-screen techeyes-page-shell radar-shell">
    <Header />

    <main class="container mx-auto px-4 md:px-8 pt-24 pb-10">
      <div class="radar-header">
        <div>
          <h1 class="page-title">科技新闻雷达</h1>
          <p class="page-subtitle">实时追踪科技动态，智能分析实体关系</p>
        </div>
      </div>

      <div class="search-section">
        <div class="search-box">
          <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索科技新闻..."
            class="search-input"
            @keyup.enter="handleSearch"
          />
          <button class="search-btn" @click="handleSearch" :disabled="searching">
            {{ searching ? '搜索中...' : '搜索' }}
          </button>
        </div>
      </div>

      <div class="tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'hot' }"
          @click="activeTab = 'hot'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          新闻热榜
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'history' }"
          @click="activeTab = 'history'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          雷达档案
        </button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="activeTab === 'hot'" class="news-list">
        <div v-if="hotNews.length === 0" class="empty-state">
          <svg class="w-16 h-16 mx-auto mb-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
          </svg>
          <h3 class="text-xl font-semibold text-slate-100 mb-2">暂无新闻</h3>
          <p class="text-slate-300">新闻数据正在更新中...</p>
        </div>

        <div v-else class="news-grid">
          <div
            v-for="(news, index) in hotNews"
            :key="news.id"
            class="news-card techeyes-panel-soft"
          >
            <div class="news-rank" :class="`rank-${Math.min(index + 1, 3)}`">
              {{ index + 1 }}
            </div>
            <div class="news-content" @click="goToNewsDetail(news.id)">
              <h3 class="news-title">{{ news.title }}</h3>
              <p class="news-snippet">{{ news.snippet }}</p>
              <div class="news-meta">
                <span v-if="news.created_at" class="news-time">
                  {{ formatTime(news.created_at) }}
                </span>
                <span v-if="news.source" class="news-source">{{ news.source }}</span>
              </div>
            </div>
            <button
              class="delete-btn"
              @click.stop="confirmDeleteNews(news.id, news.title)"
              title="删除新闻"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'history'" class="news-list">
        <div v-if="archiveItems.length === 0" class="empty-state">
          <svg class="w-16 h-16 mx-auto mb-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
          <h3 class="text-xl font-semibold text-slate-100 mb-2">暂无搜索档案</h3>
          <p class="text-slate-300">搜索科技新闻，档案会自动生成并保存</p>
        </div>

        <div v-else class="news-grid">
          <div
            v-for="(item, index) in archiveItems"
            :key="item.id"
            class="news-card techeyes-panel-soft archive-card"
          >
            <div class="archive-badge">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
              <span>档案 {{ index + 1 }}</span>
            </div>
            <div class="news-content" @click="goToNewsDetail(item.id)">
              <h3 class="news-title">{{ item.title }}</h3>
              <p class="news-snippet">{{ item.snippet }}</p>
              <div class="news-meta">
                <span v-if="item.created_at" class="news-time">
                  {{ formatTime(item.created_at) }}
                </span>
                <span v-if="item.source" class="news-source">{{ item.source }}</span>
              </div>
            </div>
            <button
              class="delete-btn"
              @click.stop="confirmDeleteNews(item.id, item.title)"
              title="删除档案"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import Header from '@/components/Header.vue'
import { getHotNews, searchNews, getSearchArchives, deleteNews, type HotNewsItem } from '@/services/api'

const router = useRouter()

const activeTab = ref<'hot' | 'history'>('hot')
const searchQuery = ref('')
const searching = ref(false)
const loading = ref(false)
const hotNews = ref<HotNewsItem[]>([])
const archiveItems = ref<HotNewsItem[]>([])

const isAuthenticated = computed(() => {
  return !!localStorage.getItem('techeyes_auth_token')
})

const loadHotNews = async () => {
  try {
    loading.value = true
    const response = await getHotNews(20)
    hotNews.value = response.items
  } catch (error) {
    console.error('加载热榜失败:', error)
  } finally {
    loading.value = false
  }
}

const loadArchives = async () => {
  try {
    loading.value = true
    const response = await getSearchArchives(50)
    archiveItems.value = response.items
  } catch (error) {
    console.error('加载搜索档案失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    activeTab.value = 'hot'
    await loadHotNews()
    return
  }

  try {
    searching.value = true
    loading.value = true
    const response = await searchNews(searchQuery.value.trim(), 20)
    
    // 更新搜索结果
    if (response.items && Array.isArray(response.items)) {
      hotNews.value = response.items
      activeTab.value = 'hot'
    } else {
      console.warn('搜索返回数据格式异常:', response)
      hotNews.value = []
    }
    
    // 更新搜索档案列表
    await loadArchives()
  } catch (error: any) {
    console.error('搜索失败:', error)
    const errorMsg = error?.response?.data?.detail || error?.message || '搜索失败'
    alert(`搜索出错: ${errorMsg}`)
  } finally {
    searching.value = false
    loading.value = false
  }
}

const goToNewsDetail = (newsId: string) => {
  router.push(`/radar/news/${newsId}`)
}

const confirmDeleteNews = async (newsId: string, newsTitle: string) => {
  if (!confirm(`确定要删除新闻"${newsTitle}"吗？\n\n删除后将无法恢复，且会清除所有用户的相关历史记录。`)) {
    return
  }
  
  try {
    await deleteNews(newsId)
    // 从列表中移除
    hotNews.value = hotNews.value.filter(n => n.id !== newsId)
    alert('新闻删除成功')
  } catch (error: any) {
    console.error('删除新闻失败:', error)
    alert(error?.response?.data?.detail || '删除新闻失败，请重试')
  }
}

const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadHotNews()
  loadArchives()
})

// 监听 tab 切换，加载对应数据
watch(activeTab, (newTab) => {
  if (newTab === 'history' && archiveItems.value.length === 0) {
    loadArchives()
  }
})
</script>

<style scoped>
.radar-shell {
  background: linear-gradient(140deg, #0a162f 0%, #162a4f 55%, #111f43 100%);
  color: #e2e8f0;
}

.radar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-title {
  font-size: clamp(2rem, 4.5vw, 3.2rem);
  font-weight: 800;
  background: linear-gradient(135deg, #7dd3fc 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  margin-top: 0.5rem;
  color: rgba(226, 232, 240, 0.7);
  font-size: 1.1rem;
}

.search-section {
  margin-bottom: 2rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(125, 211, 252, 0.3);
  border-radius: 1rem;
  padding: 0.75rem 1rem;
  backdrop-filter: blur(10px);
}

.search-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: rgba(125, 211, 252, 0.7);
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e2e8f0;
  font-size: 1rem;
}

.search-input::placeholder {
  color: rgba(226, 232, 240, 0.5);
}

.search-btn {
  background: linear-gradient(135deg, #7dd3fc 0%, #38bdf8 100%);
  color: #0f172a;
  border: none;
  padding: 0.5rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.search-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(125, 211, 252, 0.3);
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 1px solid rgba(125, 211, 252, 0.2);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  color: rgba(226, 232, 240, 0.7);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.3s;
}

.tab-btn:hover {
  color: #7dd3fc;
}

.tab-btn.active {
  color: #7dd3fc;
  border-bottom-color: #7dd3fc;
}

.loading-state,
.empty-state {
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

.news-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.news-card {
  position: relative;
  padding: 1.5rem;
  border-radius: 1rem;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid rgba(125, 211, 252, 0.15);
}

.news-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(125, 211, 252, 0.15);
  border-color: rgba(125, 211, 252, 0.3);
}

.news-rank {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.875rem;
}

.rank-1 {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #0f172a;
}

.rank-2 {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
  color: #0f172a;
}

.rank-3 {
  background: linear-gradient(135deg, #b45309 0%, #92400e 100%);
  color: #0f172a;
}

.news-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: rgba(226, 232, 240, 0.6);
}

.news-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 0.5rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-snippet {
  font-size: 0.875rem;
  color: rgba(226, 232, 240, 0.6);
  margin-bottom: 1rem;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.875rem;
}

.news-time {
  color: rgba(226, 232, 240, 0.5);
}

.news-source {
  color: rgba(125, 211, 252, 0.7);
}

.report-badge {
  background: rgba(125, 211, 252, 0.2);
  color: #7dd3fc;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.news-content {
  flex: 1;
  cursor: pointer;
}

.delete-btn {
  position: absolute;
  top: 1rem;
  left: 1rem;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.5rem;
  padding: 0.5rem;
  color: #ef4444;
  cursor: pointer;
  opacity: 0;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.news-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.5);
  transform: scale(1.05);
}

/* 搜索档案特有样式 */
.archive-card {
  position: relative;
  border: 1px solid rgba(167, 139, 250, 0.3) !important;
}

.archive-badge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, rgba(167, 139, 250, 0.2) 0%, rgba(125, 211, 252, 0.2) 100%);
  border: 1px solid rgba(167, 139, 250, 0.4);
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: #a78bfa;
}

.archive-badge svg {
  width: 1rem;
  height: 1rem;
}

.archive-card:hover {
  border-color: rgba(167, 139, 250, 0.5) !important;
  box-shadow: 0 0 20px rgba(167, 139, 250, 0.15);
}

</style>
