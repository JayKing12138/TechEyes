<template>
  <div class="min-h-screen techeyes-page-shell project-detail-shell">
    <Header />

    <main class="container-fluid project-workspace">
      <!-- 左侧面板 -->
      <aside class="project-sidebar techeyes-panel-soft">
        <!-- 项目信息 -->
        <div class="project-info">
          <button class="btn-back" @click="goBackToProjects">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            返回项目列表
          </button>
          <div class="project-title-wrap">
            <h2 class="project-title">{{ project?.name }}</h2>
            <span class="domain-badge" :class="`domain-${project?.domain}`">
              {{ domainLabel(project?.domain) }}
            </span>
          </div>
        </div>

        <!-- 标签页 -->
        <div class="sidebar-tabs">
          <button 
            v-for="tab in tabs" 
            :key="tab.id"
            class="tab-btn"
            :class="{ active: activeTab === tab.id }"
            @click="setActiveTab(tab.id)"
          >
            <component :is="tab.icon" class="w-4 h-4" />
            {{ tab.label }}
          </button>
        </div>

        <!-- 文档库标签页 -->
        <div v-show="activeTab === 'documents'" class="tab-content">
          <div class="documents-header">
            <h3 class="section-title">知识库</h3>
            <span class="doc-count">{{ documents.length }}</span>
            <button class="upload-btn" @click="triggerFileUpload">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              @change="handleFileSelect"
              style="display: none"
            />
          </div>

          <div class="documents-list">
            <div 
              v-for="doc in documents" 
              :key="doc.id" 
              class="document-item"
              :class="{ uploading: doc.status === 'processing' }"
            >
              <div class="doc-icon">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <div class="doc-info">
                <p class="doc-name">{{ doc.filename }}</p>
                <div class="doc-meta">
                  <span v-if="doc.status === 'completed'" class="meta-badge success">
                    {{ doc.chunk_count }} 分块
                  </span>
                  <span v-else-if="doc.status === 'processing'" class="meta-badge processing">
                    处理中...
                  </span>
                  <span class="meta-text">{{ formatFileSize(doc.file_size_kb * 1024) }}</span>
                </div>
              </div>
              <button 
                class="doc-delete-btn"
                @click="deleteDocument(doc.id)"
                :disabled="doc.status === 'processing'"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p v-if="documents.length === 0" class="empty-text">
              还没有文档，点击上传第一个
            </p>
          </div>

          <!-- 上传提示 -->
          <div class="upload-hint">
            <p class="hint-text">💡 支持 PDF、Word、TXT 文档</p>
          </div>
        </div>

        <!-- 对话历史标签页 -->
        <div v-show="activeTab === 'conversations'" class="tab-content">
          <div class="conversations-header">
            <h3 class="section-title">对话历史</h3>
            <span class="conv-count">{{ conversations.length }}</span>
          </div>

          <div class="conversations-list">
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="conversation-item"
              :class="{ active: activeConversationId === conv.id }"
            >
              <button
                class="conversation-main"
                @click="selectConversation(conv.id)"
              >
                <div class="conv-content">
                  <p class="conv-title">{{ conv.title || '未命名对话' }}</p>
                  <p class="conv-time">{{ formatDate(conv.created_at) }}</p>
                </div>
              </button>
              <button
                class="conv-delete-btn"
                title="删除对话"
                @click.stop="deleteConversation(conv.id)"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p v-if="conversations.length === 0" class="empty-text">
              开始一个新对话
            </p>
          </div>
        </div>

      </aside>

      <!-- 主内容区 -->
      <section class="project-main techeyes-panel">
        <header class="chat-header">
          <div class="chat-info">
            <h1 class="chat-title">分析对话</h1>
            <p class="chat-subtitle">此项目已有 {{ documents.length }} 个文档，{{ conversations.length }} 条对话</p>
          </div>
          <button class="new-conversation-btn" @click="createNewConversation">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            新建对话
          </button>
        </header>

        <!-- 消息区域 -->
        <div ref="messageRef" class="messages-container">
          <template v-if="messages.length === 0">
            <div class="empty-messages">
              <svg class="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3>开始分析</h3>
              <p>提出你的问题，AI 将基于项目文档和最新信息给出答案</p>
            </div>
          </template>

          <article v-for="msg in messages" v-else :key="`${msg.id}`" class="message-row" :class="msg.role">
            <div class="msg-badge">{{ msg.role === 'user' ? '您' : 'AI' }}</div>
            <div class="msg-bubble">
              <p v-if="msg.role === 'user'">{{ msg.content }}</p>
              <MarkdownRenderer v-else :content="msg.content" />
              
              <!-- RAG 信息 -->
              <div v-if="msg.rag_info && msg.role === 'assistant'" class="rag-info">
                <div class="rag-header">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>参考信息来源</span>
                </div>
                <div class="rag-sources">
                  <div v-if="msg.rag_info.doc_count > 0" class="source-group">
                    <span class="source-label">📄 项目文档</span>
                    <span class="source-count">{{ msg.rag_info.doc_count }} 份</span>
                  </div>
                  <div
                    v-for="detail in getDocSourceDetails(msg)"
                    :key="`${msg.id}-${detail.docId}`"
                    class="source-detail-row"
                  >
                    <span class="source-detail-name" :title="detail.filename">{{ detail.filename }}</span>
                    <span class="source-detail-count">命中 {{ detail.chunkHits }} 段</span>
                  </div>
                  <div v-if="msg.rag_info.memory_used && msg.rag_info.memory_count" class="source-group">
                    <span class="source-label">🧠 项目记忆</span>
                    <span class="source-count">{{ msg.rag_info.memory_count }} 条</span>
                  </div>
                  <div v-if="msg.rag_info.news_count > 0" class="source-group">
                    <span class="source-label">📰 最新新闻</span>
                    <span class="source-count">{{ msg.rag_info.news_count }} 条</span>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <div v-if="loading" class="message-row assistant">
            <div class="msg-badge">AI</div>
            <div class="msg-bubble thinking">
              <span class="spinner"></span>
              正在分析中...
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <footer class="chat-footer">
          <div class="input-wrap">
            <textarea
              v-model="userInput"
              placeholder="提出你的问题... (Shift+Enter 换行，Enter 发送)"
              @keydown.enter.prevent="!$event.shiftKey && sendMessage()"
              :disabled="loading"
              class="message-input"
            />
            <button 
              @click="sendMessage" 
              :disabled="!userInput.trim() || loading || documents.length === 0"
              class="send-btn"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5.951-2.976 5.951 2.976a1 1 0 001.169-1.409l-7-14z" />
              </svg>
            </button>
          </div>
          <p v-if="documents.length === 0" class="input-hint">
            ⬆️ 请先上传文档开始分析
          </p>
          <p v-else class="input-hint">
            {{ messages.length === 0 ? '💡 分析基于项目文档和最新信息' : '' }}
          </p>
        </footer>
      </section>
    </main>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Header from '@/components/Header.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { apiClient } from '@/services/api'

interface Project {
  id: number
  name: string
  description: string
  domain: string
  doc_count: number
  conversation_count: number
  created_at: string
  updated_at: string
}

interface ProjectDocument {
  id: number
  filename: string
  source_type: string
  chunk_count: number
  file_size_kb: number
  authority_score: number
  uploaded_at: string
  status: 'completed' | 'processing'
}

interface Conversation {
  id: number
  title: string
  created_at: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  rag_info?: {
    used: boolean
    doc_used?: boolean
    news_used?: boolean
    doc_count: number
    news_count: number
    doc_ids?: number[]
    chunk_ids?: number[]
    memory_used?: boolean
    memory_count?: number
  }
}

const router = useRouter()
const route = useRoute()
const projectId = computed(() => parseInt(String(route.params.id)))

const project = ref<Project | null>(null)
const documents = ref<ProjectDocument[]>([])
const conversations = ref<Conversation[]>([])
const messages = ref<Message[]>([])
// 根据 URL 初始化当前标签和对话，支持刷新/分享
const activeTab = ref<string>(route.query.tab === 'conversations' ? 'conversations' : 'documents')
const activeConversationId = ref<number | null>(
  route.query.conversationId ? Number(route.query.conversationId) : null
)
const userInput = ref('')
const loading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const messageRef = ref<HTMLElement | null>(null)
const documentPollingTimer = ref<number | null>(null)

const tabs = [
  {
    id: 'documents',
    label: '文档库',
    icon: 'DocumentIcon'
  },
  {
    id: 'conversations',
    label: '对话历史',
    icon: 'ChatIcon'
  }
]

// 加载项目数据
const loadProject = async () => {
  try {
    const data = await apiClient.get(`/projects/${projectId.value}`)
    project.value = data
  } catch (error) {
    console.error('Failed to load project:', error)
    router.push('/projects')
  }
}

// 加载文档
const loadDocuments = async () => {
  try {
    const { documents: data } = await apiClient.get(`/projects/${projectId.value}/documents`)
    documents.value = data || []

    // 有文档仍在处理中时，自动轮询；全部完成后自动停止。
    if (documents.value.some(d => d.status === 'processing')) {
      startDocumentPolling()
    } else {
      stopDocumentPolling()
    }
  } catch (error) {
    console.error('Failed to load documents:', error)
  }
}

const startDocumentPolling = () => {
  if (documentPollingTimer.value !== null) return

  documentPollingTimer.value = window.setInterval(async () => {
    await loadDocuments()
  }, 2000)
}

const stopDocumentPolling = () => {
  if (documentPollingTimer.value === null) return

  window.clearInterval(documentPollingTimer.value)
  documentPollingTimer.value = null
}

// 加载对话
const loadConversations = async () => {
  try {
    const { conversations: data } = await apiClient.get(`/projects/${projectId.value}/conversations`)
    conversations.value = data || []
  } catch (error) {
    console.error('Failed to load conversations:', error)
  }
}

// 选择对话
const selectConversation = async (conversationId: number) => {
  activeConversationId.value = conversationId
  // 同步到 URL，刷新后还能回到当前对话
  router.replace({
    name: route.name || undefined,
    params: route.params,
    query: {
      ...route.query,
      conversationId: String(conversationId),
      tab: 'conversations',
    },
  })
  activeTab.value = 'conversations'
  // 加载对话消息
  try {
    const { messages: data } = await apiClient.get(
      `/projects/${projectId.value}/conversations/${conversationId}`
    )
    messages.value = data || []
  } catch (error) {
    console.error('Failed to load conversation messages:', error)
  }
}

// 创建新对话
const createNewConversation = () => {
  activeConversationId.value = null
  messages.value = []
  userInput.value = ''
  activeTab.value = 'documents'
  // 清理 URL 中的对话参数
  router.replace({
    name: route.name || undefined,
    params: route.params,
    query: {
      ...route.query,
      conversationId: undefined,
      tab: 'documents',
    },
  })
}

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || documents.value.length === 0) return

  const content = userInput.value
  userInput.value = ''
  loading.value = true

  try {
    const response = await apiClient.post(`/projects/${projectId.value}/chat`, {
      message: content,
      conversation_id: activeConversationId.value
    })

    // 更新对话ID
    if (!activeConversationId.value) {
      activeConversationId.value = response.conversation_id
    }

    // 添加用户消息
    messages.value.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content
    })

    // 添加助手消息
    messages.value.push({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: response.response,
      rag_info: response.rag_info
    })

    // 重新加载对话历史
    await loadConversations()

    // 滚动到最新消息
    setTimeout(() => {
      if (messageRef.value) {
        messageRef.value.scrollTop = messageRef.value.scrollHeight
      }
    }, 100)
  } catch (error) {
    console.error('Failed to send message:', error)
  } finally {
    loading.value = false
  }
}

// 文件上传
const triggerFileUpload = () => {
  fileInput.value?.click()
}

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (!files) return

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await apiClient.post(
        `/projects/${projectId.value}/documents`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )

      console.log('文档上传成功:', response.filename)
    } catch (error) {
      console.error('文档上传失败:', error)
      alert(`文件 ${file.name} 上传失败，请重试`)
    }
  }

  // 立即从服务器重新加载文档列表（确保显示的是服务端真实数据）
  await loadDocuments()

  // 清空input
  target.value = ''
}

// 删除文档
const deleteDocument = async (docId: number) => {
  if (!confirm('确认删除此文档？')) return

  try {
    await apiClient.delete(`/projects/${projectId.value}/documents/${docId}`)
    documents.value = documents.value.filter(d => d.id !== docId)
  } catch (error) {
    console.error('Failed to delete document:', error)
  }
}

// 删除对话
const deleteConversation = async (conversationId: number) => {
  if (!confirm('确认删除此对话及其消息？')) return

  try {
    await apiClient.delete(`/projects/${projectId.value}/conversations/${conversationId}`)
    conversations.value = conversations.value.filter(c => c.id !== conversationId)

    if (activeConversationId.value === conversationId) {
      activeConversationId.value = null
      messages.value = []
      userInput.value = ''
      const next = conversations.value[0]
      router.replace({
        name: route.name || undefined,
        params: route.params,
        query: {
          ...route.query,
          conversationId: next ? String(next.id) : undefined,
        },
      })
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
  }
}

// 返回项目列表
const goBackToProjects = () => {
  router.push('/projects')
}

// 切换标签时同步到 URL
const setActiveTab = (tabId: string) => {
  activeTab.value = tabId
  router.replace({
    name: route.name || undefined,
    params: route.params,
    query: {
      ...route.query,
      tab: tabId,
    },
  })
}

// 格式化日期
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return `${Math.floor(days / 30)}月前`
}

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 域名标签
const domainLabel = (domain?: string) => {
  const labels: Record<string, string> = {
    'technology': '科技/IT',
    'finance': '金融经济',
    'healthcare': '医疗健康',
    'energy': '能源环保',
    'industry': '产业发展',
    'other': '其他'
  }
  return labels[domain || 'other'] || domain || '其他'
}

const getDocDisplayName = (docId: number) => {
  const hit = documents.value.find(d => d.id === docId)
  return hit?.filename || `文档 #${docId}`
}

const getDocSourceDetails = (msg: Message) => {
  const rag = msg.rag_info
  if (!rag?.doc_ids || rag.doc_ids.length === 0) {
    return [] as Array<{ docId: number; filename: string; chunkHits: number }>
  }

  const chunkIds = Array.isArray(rag.chunk_ids) ? rag.chunk_ids : []
  const stats = new Map<number, number>()

  rag.doc_ids.forEach((docId, idx) => {
    const id = Number(docId)
    if (!Number.isFinite(id)) return

    // 如果有 chunk_ids，按命中条数累计；没有则至少记 1 次命中。
    const hasChunk = idx < chunkIds.length && chunkIds[idx] !== null && chunkIds[idx] !== undefined
    const delta = hasChunk ? 1 : 1
    stats.set(id, (stats.get(id) || 0) + delta)
  })

  return Array.from(stats.entries())
    .map(([docId, chunkHits]) => ({
      docId,
      filename: getDocDisplayName(docId),
      chunkHits,
    }))
    .sort((a, b) => b.chunkHits - a.chunkHits)
}

onMounted(async () => {
  await Promise.all([
    loadProject(),
    loadDocuments(),
    loadConversations()
  ])

  // 初始化时，根据 URL 或现有列表选中一个对话
  const fromQuery = route.query.conversationId ? Number(route.query.conversationId) : null
  const hasConversations = conversations.value.length > 0

  if (fromQuery && !Number.isNaN(fromQuery)) {
    await selectConversation(fromQuery)
  } else if (hasConversations && activeConversationId.value == null) {
    await selectConversation(conversations.value[0].id)
  }
})

onBeforeUnmount(() => {
  stopDocumentPolling()
})
</script>

<style scoped>
.project-detail-shell {
  background:
    radial-gradient(1100px 700px at 16% 4%, rgba(34, 211, 238, 0.1), transparent 64%),
    radial-gradient(900px 620px at 92% 12%, rgba(59, 130, 246, 0.12), transparent 62%),
    linear-gradient(130deg, #050a1b 0%, #091730 50%, #0a1230 100%);
}

.project-workspace {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
  max-width: 100%;
  padding-left: 1rem;
  padding-right: 1rem;
  margin-top: 5rem;
  margin-bottom: 2rem;
  min-height: calc(100vh - 5rem);
}

/* 左侧面板 */
.project-sidebar {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 7rem);
  overflow-y: auto;
  border-radius: 0.75rem;
  padding: 0;
}

.project-info {
  padding: 1.5rem;
  border-bottom: 1px solid rgba(125, 211, 252, 0.2);
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: none;
  border: none;
  color: #7dd3fc;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 1rem;
  transition: color 0.2s ease;
}

.btn-back:hover {
  color: #22d3ee;
}

.project-title-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
}

.domain-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.sidebar-tabs {
  display: flex;
  gap: 0;
  padding: 1rem;
  border-bottom: 1px solid rgba(125, 211, 252, 0.2);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  color: #9fb4cf;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  margin-bottom: -1rem;
  padding-bottom: 1rem;
}

.tab-btn:hover {
  color: #7dd3fc;
}

.tab-btn.active {
  color: #7dd3fc;
  border-bottom-color: #7dd3fc;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

/* 文档库 */
.documents-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
  flex: 1;
}

.doc-count {
  background: rgba(59, 130, 246, 0.78);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.upload-btn {
  background: none;
  border: none;
  color: #7dd3fc;
  padding: 0.5rem;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.upload-btn:hover {
  transform: scale(1.1);
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.document-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(8, 24, 50, 0.72);
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 0.5rem;
  transition: all 0.2s ease;
}

.document-item:hover {
  border-color: rgba(34, 211, 238, 0.5);
  background: rgba(9, 34, 64, 0.84);
}

.document-item.uploading {
  opacity: 0.6;
}

.doc-icon {
  color: #7dd3fc;
  flex-shrink: 0;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 0.25rem 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.75rem;
  color: #9fb4cf;
}

.meta-badge {
  padding: 0.1rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 600;
}

.meta-badge.success {
  background: rgba(52, 211, 153, 0.2);
  color: #86efac;
}

.meta-badge.processing {
  background: rgba(251, 191, 36, 0.2);
  color: #fcd34d;
}

.doc-delete-btn {
  background: none;
  border: none;
  color: #94a3b8;
  padding: 0.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.doc-delete-btn:hover:not(:disabled) {
  color: #e53e3e;
}

.doc-delete-btn:disabled {
  cursor: not-allowed;
}

.upload-hint {
  padding: 0.75rem;
  background: rgba(8, 24, 50, 0.64);
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 0.5rem;
  text-align: center;
}

.hint-text {
  font-size: 0.75rem;
  color: #9fb4cf;
  margin: 0;
}

/* 对话历史 */
.conversations-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.conv-count {
  background: rgba(59, 130, 246, 0.78);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.conversations-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.conversation-item {
  padding: 0.75rem;
  background: rgba(8, 24, 50, 0.72);
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 0.5rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.conversation-item:hover {
  border-color: rgba(34, 211, 238, 0.5);
  background: rgba(9, 34, 64, 0.84);
}

.conversation-item.active {
  background: rgba(37, 99, 235, 0.74);
  color: white;
  border-color: rgba(125, 211, 252, 0.52);
}

.conv-content {
  display: flex;
  flex-direction: column;
}

.conv-title {
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-time {
  font-size: 0.75rem;
  color: #94a3b8;
  margin: 0.25rem 0 0 0;
}

.conversation-item.active .conv-time {
  color: rgba(255, 255, 255, 0.7);
}

/* 项目设置 */
.settings-section {
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid rgba(125, 211, 252, 0.2);
  background: rgba(8, 24, 50, 0.72);
  border-radius: 0.5rem;
}

.settings-section.danger {
  border-color: rgba(248, 113, 113, 0.4);
  background: rgba(127, 29, 29, 0.2);
}

.setting-item {
  margin-bottom: 1rem;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-item label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #9fb4cf;
  margin-bottom: 0.25rem;
}

.setting-item p {
  margin: 0;
  font-size: 0.875rem;
  color: #e2e8f0;
}

.btn-danger {
  width: 100%;
  padding: 0.75rem;
  background: #e53e3e;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-danger:hover {
  background: #c53030;
}

.empty-text {
  text-align: center;
  padding: 1rem;
  color: #94a3b8;
  font-size: 0.875rem;
  margin: 0;
}

/* 主内容区 */
.project-main {
  display: flex;
  flex-direction: column;
  border-radius: 0.75rem;
  overflow: hidden;
}

.chat-header {
  padding: 1.5rem;
  border-bottom: 1px solid rgba(125, 211, 252, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-info {
  flex: 1;
}

.chat-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 0.5rem 0;
}

.chat-subtitle {
  font-size: 0.875rem;
  color: #9fb4cf;
  margin: 0;
}

.new-conversation-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(120deg, #22d3ee, #3b82f6);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.new-conversation-btn:hover {
  filter: brightness(1.08);
}

/* 消息区域 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  background: linear-gradient(135deg, rgba(6, 18, 40, 0.88) 0%, rgba(8, 20, 45, 0.92) 100%);
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  text-align: center;
}

.empty-messages svg {
  margin-bottom: 1.5rem;
  color: #475569;
  opacity: 0.8;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.empty-messages h3 {
  font-size: 1.35rem;
  color: #e2e8f0;
  margin: 0 0 0.625rem 0;
  font-weight: 700;
}

.empty-messages p {
  font-size: 0.875rem;
  color: #9fb4cf;
  margin: 0;
  max-width: 300px;
}

.message-row {
  display: flex;
  gap: 1rem;
  animation: fadeIn 0.3s ease;
}

.message-row.user {
  justify-content: flex-start;
  flex-direction: row-reverse;
}

.message-row.assistant {
  justify-content: flex-start;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-badge {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  flex-shrink: 0;
  margin-top: 0.25rem;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.message-row.user .msg-badge {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.msg-bubble {
  max-width: 70%;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, rgba(12, 30, 58, 0.92) 0%, rgba(8, 24, 50, 0.88) 100%);
  color: #e0f2fe;
  border-radius: 1.125rem;
  border: 1px solid rgba(34, 211, 238, 0.25);
  box-shadow: 0 8px 16px rgba(8, 24, 50, 0.3), inset 0 1px 0 rgba(125, 211, 252, 0.1);
  backdrop-filter: blur(10px);
  transition: all 0.2s ease;
}

.message-row.user .msg-bubble {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.82) 0%, rgba(29, 78, 216, 0.78) 100%);
  color: #f0f9ff;
  border-color: rgba(125, 211, 252, 0.35);
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.25), inset 0 1px 0 rgba(191, 219, 254, 0.1);
}

.message-row.user .msg-bubble:hover {
  box-shadow: 0 12px 20px rgba(37, 99, 235, 0.3), inset 0 1px 0 rgba(191, 219, 254, 0.15);
  transform: translateY(-2px);
}

.message-row.assistant .msg-bubble:hover {
  box-shadow: 0 12px 20px rgba(8, 24, 50, 0.4), inset 0 1px 0 rgba(125, 211, 252, 0.15);
  transform: translateY(-2px);
}

.msg-bubble p {
  margin: 0;
  line-height: 1.7;
  word-break: break-word;
  font-size: 0.95rem;
  letter-spacing: 0.3px;
}

.msg-bubble.thinking {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(148, 163, 184, 0.35);
  border-top-color: #7dd3fc;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* RAG 信息 */
.rag-info {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(125, 211, 252, 0.2);
  font-size: 0.85rem;
}

.rag-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #7dd3fc;
  margin-bottom: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.rag-sources {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.source-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.625rem 0.875rem;
  background: linear-gradient(135deg, rgba(8, 30, 58, 0.7) 0%, rgba(12, 35, 60, 0.6) 100%);
  border-radius: 0.5rem;
  border: 1px solid rgba(34, 211, 238, 0.15);
  transition: all 0.2s ease;
}

.source-group:hover {
  background: linear-gradient(135deg, rgba(12, 40, 70, 0.8) 0%, rgba(16, 45, 75, 0.7) 100%);
  border-color: rgba(34, 211, 238, 0.25);
  box-shadow: 0 2px 8px rgba(34, 211, 238, 0.1);
}

.source-label {
  font-weight: 700;
  color: #cffafe;
  letter-spacing: 0.5px;
}

.source-count {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.2) 0%, rgba(34, 211, 238, 0.12) 100%);
  padding: 0.25rem 0.75rem;
  border-radius: 0.375rem;
  font-weight: 700;
  color: #7dd3fc;
  border: 1px solid rgba(34, 211, 238, 0.2);
  font-size: 0.8rem;
}

.source-detail-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.45rem 0.7rem;
  margin-top: -0.2rem;
  border-left: 2px solid rgba(34, 211, 238, 0.25);
  background: rgba(8, 30, 58, 0.35);
  border-radius: 0.4rem;
  cursor: pointer;
}

.source-detail-row.expanded {
  border-left-color: rgba(56, 189, 248, 0.55);
  background: rgba(8, 36, 66, 0.5);
}

.source-detail-main {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.source-ref-index {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: #7dd3fc;
  border: 1px solid rgba(34, 211, 238, 0.4);
  background: rgba(34, 211, 238, 0.12);
}

.source-detail-name {
  color: #cfe6ff;
  font-size: 0.83rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-detail-count {
  color: #8acfff;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
}

.source-detail-content {
  margin: 0.15rem 0 0.65rem 0;
  padding: 0.7rem 0.9rem;
  border-radius: 0.5rem;
  border: 1px dashed rgba(125, 211, 252, 0.28);
  background: rgba(7, 26, 48, 0.75);
}

.source-detail-text {
  margin: 0;
  color: #c8def8;
  line-height: 1.65;
  white-space: pre-wrap;
}

.source-detail-loading {
  margin: 0;
  color: #8db4dc;
  font-size: 0.85rem;
}

/* 输入区域 */
.chat-footer {
  padding: 1.5rem;
  border-top: 1px solid rgba(125, 211, 252, 0.15);
  background: linear-gradient(180deg, rgba(6, 18, 40, 0.95) 0%, rgba(4, 12, 28, 0.98) 100%);
  backdrop-filter: blur(8px);
}

.input-wrap {
  display: flex;
  gap: 0.875rem;
  margin-bottom: 0.75rem;
}

.message-input {
  flex: 1;
  padding: 0.875rem 1.125rem;
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 0.75rem;
  font-family: inherit;
  font-size: 0.95rem;
  color: #e2e8f0;
  background: linear-gradient(135deg, rgba(7, 20, 42, 0.88) 0%, rgba(5, 15, 35, 0.9) 100%);
  resize: none;
  max-height: 120px;
  transition: all 0.2s ease;
  box-shadow: inset 0 1px 3px rgba(8, 24, 50, 0.3);
}

.message-input::placeholder {
  color: #64748b;
}

.message-input:focus {
  outline: none;
  border-color: #7dd3fc;
  box-shadow: inset 0 1px 3px rgba(8, 24, 50, 0.3), 0 0 0 3px rgba(34, 211, 238, 0.15);
  background: linear-gradient(135deg, rgba(10, 25, 50, 0.92) 0%, rgba(8, 20, 40, 0.95) 100%);
}

.message-input:disabled {
  background: rgba(15, 23, 42, 0.65);
  color: #64748b;
}

.send-btn {
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, #22d3ee 0%, #3b82f6 100%);
  color: white;
  border: none;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(34, 211, 238, 0.25);
  letter-spacing: 0.5px;
}

.send-btn:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(34, 211, 238, 0.35);
}

.send-btn:active:not(:disabled) {
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: linear-gradient(135deg, #64748b, #475569);
  cursor: not-allowed;
  opacity: 0.6;
}

.input-hint {
  font-size: 0.75rem;
  color: #94a3b8;
  margin: 0;
  text-align: center;
}

/* 响应式 */
@media (max-width: 1024px) {
  .project-workspace {
    grid-template-columns: 280px 1fr;
    gap: 1rem;
  }

  .msg-bubble {
    max-width: 80%;
  }
}

@media (max-width: 768px) {
  .project-workspace {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .project-sidebar {
    max-height: 400px;
  }

  .msg-bubble {
    max-width: 95%;
  }

  .chat-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .new-conversation-btn {
    width: 100%;
  }
}
</style>
