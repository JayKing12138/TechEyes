import axios from 'axios'
import { AnalysisRequest, AnalysisState, ChatMessage, ConversationItem } from '../types'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
})

const TOKEN_KEY = 'techeyes_auth_token'
const USER_KEY = 'techeyes_auth_user'

const CLIENT_ID_KEY = 'techeyes_client_id'

const generateClientId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `guest_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
}

const getClientId = () => {
  let clientId = localStorage.getItem(CLIENT_ID_KEY)
  if (!clientId) {
    clientId = generateClientId()
    localStorage.setItem(CLIENT_ID_KEY, clientId)
  }
  return clientId
}

export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }
}

api.interceptors.request.use((config) => {
  const clientId = getClientId()

  config.headers = config.headers || {}
  config.headers['X-Client-Id'] = clientId

  // 每次请求时从localStorage读取最新token
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const tokenExpired = response.headers['x-token-expired']
    if (tokenExpired === 'true') {
      console.warn('Token已过期，清除认证信息')
      setAuthToken(null)
    }
    return response
  },
  (error) => {
    return Promise.reject(error)
  }
)

export const registerUser = async (request: { username: string; password: string }) => {
  const response = await api.post('/auth/register', request)
  return response.data
}

export const loginUser = async (request: { username: string; password: string }) => {
  const response = await api.post('/auth/login', request)
  return response.data
}

/** 提交分析请求 */
export const submitAnalysis = async (request: AnalysisRequest) => {
  const response = await api.post('/analyze', request)
  return response.data
}

/** 获取实时分析进度 */
export const getAnalysisProgress = async (sessionId: string): Promise<AnalysisState> => {
  const response = await api.get(`/analysis/${sessionId}/progress`)
  return response.data
}

/** 获取完整分析结果 */
export const getAnalysisResult = async (sessionId: string) => {
  const response = await api.get(`/analysis/${sessionId}/result`)
  return response.data
}

/** 获取流式分析数据 */
export const subscribeToAnalysis = (sessionId: string, onUpdate: (data: any) => void) => {
  const params = new URLSearchParams()
  params.set('client_id', getClientId())
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    params.set('access_token', token)
  }

  const eventSource = new EventSource(`${API_BASE}/analysis/${sessionId}/stream?${params.toString()}`)
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onUpdate(data)
  }

  eventSource.onerror = () => {
    eventSource.close()
  }

  return eventSource
}

/** 检查语义缓存 */
export const checkSemanticCache = async (query: string) => {
  const response = await api.post('/cache/check', { query })
  return response.data
}

/** 获取历史分析记录 */
export const getAnalysisHistory = async (params?: { limit?: number; query?: string }) => {
  const response = await api.get('/history', { params })
  return response.data
}

/** 删除历史记录 */
export const deleteAnalysisHistory = async (sessionId: string) => {
  const response = await api.delete(`/history/${sessionId}`)
  return response.data
}

/** 创建对话会话 */
export const createConversation = async (title?: string): Promise<ConversationItem> => {
  const response = await api.post('/chat/conversations', { title })
  return response.data
}

/** 获取会话列表 */
export const getConversations = async (limit = 50): Promise<{ items: ConversationItem[]; total: number }> => {
  const response = await api.get('/chat/conversations', { params: { limit } })
  return response.data
}

/** 获取会话消息 */
export const getConversationMessages = async (
  conversationId: string,
  limit = 100,
): Promise<{ items: ChatMessage[]; total: number }> => {
  const response = await api.get(`/chat/conversations/${conversationId}/messages`, { params: { limit } })
  return response.data
}

/** 发送会话消息 */
export const sendConversationMessage = async (
  conversationId: string,
  content: string,
): Promise<{
  conversation_id: string
  user_message: ChatMessage
  assistant_message: ChatMessage
  cache: { hit: boolean; tier: string | null }
}> => {
  // 会话回答和标题生成可能耗时较长，这里放宽超时避免“后端成功但前端误报失败”
  const response = await api.post(`/chat/conversations/${conversationId}/messages`, { content }, { timeout: 120000 })
  return response.data
}




export type ChatStreamEvent =
  | { type: 'user_message'; data: ChatMessage }
  | { type: 'assistant_delta'; delta: string }
  | { type: 'done'; conversation_id: string; assistant_message: ChatMessage; cache: { hit: boolean; tier: string | null } }
  | { type: 'error'; message: string; code?: string }

/** 流式发送会话消息（SSE over fetch） */
export const streamConversationMessage = async (
  conversationId: string,
  content: string,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> => {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Client-Id': getClientId(),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || '发送消息失败')
  }

  if (!response.body) {
    throw new Error('浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)

        const dataLines = rawEvent
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim())

        if (dataLines.length > 0) {
          try {
            const parsed = JSON.parse(dataLines.join('')) as ChatStreamEvent
            onEvent(parsed)
          } catch {
            // ignore malformed chunks
          }
        }

        boundary = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/** 删除对话 */
export const deleteConversation = async (conversationId: string) => {
  const response = await api.delete(`/chat/conversations/${conversationId}`)
  return response.data
}

/** 删除对话中的单条消息 */
export const deleteConversationMessage = async (conversationId: string, turnId: number) => {
  const response = await api.delete(`/chat/conversations/${conversationId}/messages/${turnId}`)
  return response.data
}

/** 获取缓存统计 */
export const getCacheStats = async () => {
  const response = await api.get('/cache/stats')
  return response.data
}

/** 取消分析会话 */
export const cancelAnalysis = async (sessionId: string) => {
  const response = await api.post(`/analysis/${sessionId}/cancel`)
  return response.data
}

// ==================== 项目管理 API ====================

/** 创建项目 */
export const createProject = async (data: {
  name: string
  description?: string
  domain?: string
}) => {
  const response = await api.post('/projects', data)
  return response.data
}

/** 获取项目列表 */
export const getProjects = async () => {
  const response = await api.get('/projects')
  return response.data
}

/** 获取项目详情 */
export const getProject = async (projectId: number) => {
  const response = await api.get(`/projects/${projectId}`)
  return response.data
}

/** 更新项目 */
export const updateProject = async (projectId: number, data: any) => {
  const response = await api.put(`/projects/${projectId}`, data)
  return response.data
}

/** 删除项目 */
export const deleteProject = async (projectId: number) => {
  const response = await api.delete(`/projects/${projectId}`)
  return response.data
}

/** 上传项目文档 */
export const uploadProjectDocument = async (projectId: number, formData: FormData) => {
  const response = await api.post(`/projects/${projectId}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/** 获取项目文档列表 */
export const getProjectDocuments = async (projectId: number) => {
  const response = await api.get(`/projects/${projectId}/documents`)
  return response.data
}

/** 删除项目文档 */
export const deleteProjectDocument = async (projectId: number, docId: number) => {
  const response = await api.delete(`/projects/${projectId}/documents/${docId}`)
  return response.data
}

/** 获取项目对话列表 */
export const getProjectConversations = async (projectId: number) => {
  const response = await api.get(`/projects/${projectId}/conversations`)
  return response.data
}

/** 获取项目对话详情 */
export const getProjectConversation = async (projectId: number, conversationId: number) => {
  const response = await api.get(`/projects/${projectId}/conversations/${conversationId}`)
  return response.data
}

/** 删除项目对话 */
export const deleteProjectConversation = async (projectId: number, conversationId: number) => {
  const response = await api.delete(`/projects/${projectId}/conversations/${conversationId}`)
  return response.data
}

/** 发送项目消息（双通道RAG） */
export const sendProjectMessage = async (projectId: number, data: {
  message: string
  conversation_id?: number
}) => {
  const response = await api.post(`/projects/${projectId}/chat`, data, {
    timeout: 120000
  })
  return response.data
}

// 创建一个便捷的客户端
export const apiClient = {
  get: (path: string, config?: any) => api.get(path, config).then(r => r.data),
  post: (path: string, data?: any, config?: any) => api.post(path, data, config).then(r => r.data),
  put: (path: string, data?: any, config?: any) => api.put(path, data, config).then(r => r.data),
  delete: (path: string, config?: any) => api.delete(path, config).then(r => r.data),
}

// ==================== 科技新闻雷达 API ====================

export interface HotNewsItem {
  id: string
  title: string
  url?: string
  snippet?: string
  created_at?: string
}

export interface NewsDetail {
  news: {
    id: string
    title: string
    url?: string
    snippet?: string
    content?: string
    source?: string
        source_urls?: Array<{
          title: string
          url: string
        }>
    created_at?: string
  }
  graph: {
    nodes: Array<{
      id: string
      name: string
      type: string
    }>
    edges: Array<{
      source: string
      target: string
      type: string
      salience?: number
    }>
  }
}

export interface AnalyzeEntitiesRequest {
  entities: string[]
  news_id?: string
  question?: string
}

export interface AnalyzeEntitiesResponse {
  question: string
  entities: string[]
  news_count: number
  news: any[]
  local_news_count?: number
  web_news_count?: number
  answer: string
}

export interface FollowupRequest {
  news_id: string
  question: string
  entities?: string[]
  analysis_history?: Array<{
    question: string
    answer: string
  }>
}

export interface FollowupResponse {
  question: string
  entities: string[]
  answer: string
  news: any[]
}

export interface NewsHistoryItem {
  id: number
  news_id: string
  news_title: string
  news_url?: string
  news_snippet?: string
  view_count: number
  analysis_count: number
  report_generated: number
  last_viewed_at?: string
  first_viewed_at?: string
  notes?: string
}

export interface NewsHistoryResponse {
  items: NewsHistoryItem[]
  total: number
  offset: number
  limit: number
}

export interface NewsReport {
  news: any
  graph: any
  user_history: {
    view_count: number
    analysis_count: number
    report_count: number
    first_viewed?: string
    last_viewed?: string
    notes?: string
    analysis_runs?: any[]
    followups?: any[]
  }
  entities_summary: {
    total_count: number
    by_type: Record<string, string[]>
    entity_list: any[]
  }
  related_entities: Array<{
    name: string
    type: string
    co_occurrence: number
  }>
  related_searches?: any[]
  report_markdown?: string
  generated_at: string
}

export const getHotNews = async (limit: number = 20): Promise<{ items: HotNewsItem[] }> => {
  const response = await api.get('/radar/hot', { params: { limit } })
  return response.data
}

export const searchNews = async (query: string, limit: number = 20): Promise<{ items: HotNewsItem[] }> => {
  const response = await api.get('/radar/search', { params: { query, limit } })
  return response.data
}

export const getSearchArchives = async (limit: number = 50): Promise<{ items: HotNewsItem[] }> => {
  const response = await api.get('/radar/archives', { params: { limit } })
  return response.data
}

export const getNewsDetail = async (newsId: string): Promise<NewsDetail> => {
  const response = await api.get(`/radar/news/${newsId}`)
  return response.data
}

export const analyzeEntities = async (data: AnalyzeEntitiesRequest): Promise<AnalyzeEntitiesResponse> => {
  const response = await api.post('/radar/analyze-entities', data)
  return response.data
}

export const askRadarFollowup = async (data: FollowupRequest): Promise<FollowupResponse> => {
  const response = await api.post('/radar/followup', data)
  return response.data
}

export const getNewsHistory = async (
  limit: number = 50,
  offset: number = 0
): Promise<NewsHistoryResponse> => {
  const response = await api.get('/radar/history', { params: { limit, offset } })
  return response.data
}

/** 获取当前用户在某条新闻下的按图索骥与追问历史（用于刷新后恢复） */
export const getNewsMyHistory = async (newsId: string): Promise<{
  analysis_runs: Array<{
    ts: string
    entities: string[]
    question: string
    answer: string
    local_news_count: number
    web_news_count: number
  }>
  followups: Array<{ ts: string; question: string; answer: string }>
}> => {
  const response = await api.get(`/radar/news/${newsId}/my-history`)
  return response.data
}

export const generateNewsReport = async (newsId: string): Promise<NewsReport> => {
  const response = await api.get(`/radar/news/${newsId}/report`)
  return response.data
}

export const downloadNewsReportPdf = async (newsId: string): Promise<Blob> => {
  const response = await api.get(`/radar/news/${newsId}/report/pdf`, {
    responseType: 'blob'
  })
  return response.data
}

/** 删除新闻 */
export const deleteNews = async (newsId: string): Promise<{ message: string; news_id: string }> => {
  const response = await api.delete(`/radar/news/${newsId}`)
  return response.data
}

export default api
