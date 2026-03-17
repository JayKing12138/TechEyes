<template>
  <div class="min-h-screen techeyes-page-shell chat-shell">
    <Header />

    <main class="container mx-auto px-4 md:px-8 pt-24 pb-10">
      <section class="chat-layout">
        <aside class="chat-sidebar techeyes-panel-soft">
          <div class="sidebar-top">
            <h2 class="sidebar-title">智能决策问答</h2>
            <button class="new-btn" @click="handleCreateConversation" :disabled="creatingConversation">
              {{ creatingConversation ? '创建中...' : '新建' }}
            </button>
          </div>

          <div class="conversation-list">
            <div
              v-for="item in conversations"
              :key="item.conversation_id"
              class="conversation-item"
              :class="{ active: activeConversationId === item.conversation_id }"
              role="button"
              tabindex="0"
              @click="selectConversation(item.conversation_id)"
              @keydown.enter="selectConversation(item.conversation_id)"
              @keydown.space.prevent="selectConversation(item.conversation_id)"
            >
              <div class="conversation-content">
                <p class="conversation-title">{{ item.title || '新问答' }}</p>
              </div>
              <button 
                class="delete-btn" 
                @click.stop="handleDeleteConversation(item.conversation_id)"
                title="删除问答"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
              </button>
            </div>
            <p v-if="conversations.length === 0" class="empty-text">暂无会话</p>
          </div>
        </aside>

        <section class="chat-main techeyes-panel">
          <header class="chat-main-head">
            <h1 class="chat-title">AI 智能决策问答</h1>
          </header>

          <div ref="messageRef" class="message-box">
            <article v-for="msg in messages" :key="`${msg.turn_id}-${msg.role}`" class="msg-row" :class="msg.role">
              <div class="msg-badge">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
              <div class="msg-bubble">
                <!-- 用户消息显示纯文本 -->
                <p v-if="msg.role === 'user'">{{ msg.content }}</p>
                <!-- AI消息使用Markdown渲染 -->
                <MarkdownRenderer v-else :content="msg.content" :meta="msg.meta" />
                <p v-if="msg.role === 'assistant' && msg.meta?.cache_hit" class="cache-tip">
                  缓存命中: {{ msg.meta?.cache_hit }}
                </p>
                <div v-if="msg.role === 'assistant' && getMessageSources(msg).length > 0" class="sources-wrap">
                  <p class="sources-title">消息来源</p>
                  <ul class="sources-list">
                    <li v-for="(source, idx) in getMessageSources(msg)" :key="`${msg.turn_id}-src-${idx}`" class="sources-item">
                      <a v-if="source.url" :href="source.url" target="_blank" rel="noopener noreferrer" class="source-link">
                        {{ source.label }}
                      </a>
                      <span v-else>{{ source.label }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </article>

            <div v-if="sending" class="msg-row assistant">
              <div class="msg-badge">AI</div>
              <div class="msg-bubble thinking">正在思考...</div>
            </div>

            <p v-if="messages.length === 0 && !sending" class="empty-text">发送第一条问题，开始智能决策问答。</p>
          </div>

          <div class="chat-input-wrap">
            <textarea
              v-model="draft"
              class="chat-input"
              rows="3"
              placeholder="输入你的决策问题，回车发送（Shift+Enter 换行）"
              @keydown="handleInputKeydown"
            ></textarea>
            <div class="chat-actions">
              <button class="send-btn" :disabled="!canSend" @click="handleSendMessage">
                {{ sending ? '发送中...' : '发送' }}
              </button>
            </div>
          </div>

          <p v-if="errorText" class="error-text">{{ errorText }}</p>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Header from '@/components/Header.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import {
  createConversation,
  deleteConversation,
  getConversationMessages,
  getConversations,
  sendConversationMessage,
} from '@/services/api'  
import type { ChatMessage, ConversationItem } from '@/types'

const route = useRoute()
const router = useRouter()

type MessageSource = {
  label: string
  url?: string
}

const conversations = ref<ConversationItem[]>([])
const activeConversationId = ref<string>('')
const isNewConversation = ref(false)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const creatingConversation = ref(false)
const errorText = ref('')
const messageRef = ref<HTMLElement | null>(null)

const canSend = computed(() => Boolean(activeConversationId.value) && Boolean(draft.value.trim()) && !sending.value)

const getMessageSources = (msg: ChatMessage): MessageSource[] => {
  const result: MessageSource[] = []
  const seen = new Set<string>()
  const meta = (msg.meta || {}) as Record<string, any>

  const pushSource = (label: string, url?: string) => {
    const cleanLabel = (label || '').trim()
    if (!cleanLabel) return
    const key = `${cleanLabel}|${url || ''}`
    if (seen.has(key)) return
    seen.add(key)
    result.push({ label: cleanLabel, url })
  }

  const fromMeta = meta.sources || meta.references
  if (Array.isArray(fromMeta)) {
    fromMeta.forEach((item: any) => {
      const url = item?.url || item?.link || undefined
      const label = item?.title || item?.source || item?.name || url || ''
      pushSource(label, url)
    })
  }

  const lines = (msg.content || '').split('\n')
  for (const line of lines) {
    const sourceLine = line.match(/^\s*(?:\[(\d+)\]|来源\s*(\d+)|【\s*来源\s*(\d+)\s*】)\s*[:：\-]\s*(.+)$/i)
    if (sourceLine) {
      pushSource(sourceLine[4])
    }
  }

  const urls = (msg.content || '').match(/https?:\/\/[^\s)\]]+/g) || []
  urls.slice(0, 5).forEach((url) => pushSource(url, url))

  if (meta.cache_hit) {
    pushSource(`缓存来源: ${meta.cache_hit}`)
  }

  return result.slice(0, 6)
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageRef.value) {
    messageRef.value.scrollTop = messageRef.value.scrollHeight
  }
}

const loadConversations = async () => {
  const data = await getConversations(100)
  conversations.value = data.items || []
}

const selectConversation = async (conversationId: string) => {
  activeConversationId.value = conversationId
  const data = await getConversationMessages(conversationId, 200)
  messages.value = data.items || []
  await scrollToBottom()
}

const handleCreateConversation = async () => {
  creatingConversation.value = true
  errorText.value = ''
  try {
    const tempId = Date.now().toString()
    activeConversationId.value = tempId
    isNewConversation.value = true
    messages.value = []
    draft.value = ''
  } catch (error: any) {
    errorText.value = error?.response?.data?.detail || '创建会话失败'
  } finally {
    creatingConversation.value = false
  }
}

const handleSendMessage = async () => {
  if (!canSend.value) return
  sending.value = true
  errorText.value = ''

  const content = draft.value.trim()
  draft.value = ''

  try {
    let conversationId = activeConversationId.value

    if (isNewConversation.value) {
      const created = await createConversation()
      conversationId = created.conversation_id
      activeConversationId.value = conversationId
      isNewConversation.value = false
      await loadConversations()
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: content,
      turn_id: (messages.value.length / 2) + 1,
    }
    messages.value.push(userMessage)
    await scrollToBottom()

    const response = await sendConversationMessage(conversationId, content)

    if (response.user_message) {
      messages.value[messages.value.length - 1] = response.user_message
    }

    messages.value.push(response.assistant_message)
    await loadConversations()
    await scrollToBottom()
  } catch (error: any) {
    errorText.value = error?.response?.data?.detail || '发送消息失败'
    draft.value = content
    messages.value.pop()
  } finally {
    sending.value = false
  }
}

const handleDeleteConversation = async (conversationId: string) => {
  if (!confirm('确认删除这个智能决策问答会话吗？删除后无法恢复。')) return
  
  errorText.value = ''
  try {
    if (isNewConversation.value && activeConversationId.value === conversationId) {
      activeConversationId.value = ''
      messages.value = []
      isNewConversation.value = false
      return
    }

    await deleteConversation(conversationId)
    await loadConversations()
    
    if (activeConversationId.value === conversationId) {
      if (conversations.value.length > 0) {
        await selectConversation(conversations.value[0].conversation_id)
      } else {
        activeConversationId.value = ''
        messages.value = []
        await handleCreateConversation()
      }
    }
  } catch (error: any) {
    errorText.value = error?.response?.data?.detail || '删除会话失败'
  }
}

const handleInputKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSendMessage()
  }
}

onMounted(async () => {
  try {
    await loadConversations()
    
    const queryFromLanding = route.query.q as string | undefined
    
    if (queryFromLanding && queryFromLanding.trim()) {
      await handleCreateConversation()
      draft.value = queryFromLanding.trim()
      await handleSendMessage()
      router.replace({ path: '/chat' })
      return
    }
    
    if (conversations.value.length === 0) {
      await handleCreateConversation()
      return
    }
    await selectConversation(conversations.value[0].conversation_id)
  } catch (error: any) {
    errorText.value = error?.response?.data?.detail || '初始化会话失败'
  }
})
</script>

<style scoped>
.chat-shell {
  color: #dbeafe;
}

.chat-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1rem;
}

.chat-sidebar {
  min-height: 72vh;
  padding: 0.95rem;
}

.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.7rem;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: 700;
}

.new-btn {
  border: 1px solid rgba(103, 232, 249, 0.4);
  border-radius: 0.6rem;
  padding: 0.32rem 0.62rem;
  background: rgba(6, 34, 58, 0.8);
  color: #cffafe;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.conversation-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  text-align: left;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.75rem;
  padding: 0.55rem 0.6rem;
  background: rgba(8, 22, 46, 0.72);
  cursor: pointer;
}

.conversation-item.active {
  border-color: rgba(34, 211, 238, 0.6);
  background: rgba(3, 38, 61, 0.88);
}

.conversation-content {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.conversation-title {
  font-weight: 700;
  font-size: 0.92rem;
}

.delete-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.delete-btn svg {
  width: 16px;
  height: 16px;
}

.chat-main {
  min-height: 72vh;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.chat-main-head {
  border-bottom: 1px solid rgba(148, 163, 184, 0.24);
  padding-bottom: 0.8rem;
}

.chat-title {
  font-size: 1.2rem;
  font-weight: 800;
}

.message-box {
  margin-top: 0.85rem;
  flex: 1;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.msg-badge {
  min-width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  border: 1px solid rgba(125, 211, 252, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8, 31, 56, 0.86);
  color: #bae6fd;
  font-size: 0.76rem;
}

.msg-bubble {
  max-width: min(74ch, 90%);
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 0.9rem;
  background: rgba(8, 24, 50, 0.8);
  padding: 0.65rem 0.82rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

.msg-row.user .msg-bubble {
  background: rgba(6, 44, 66, 0.86);
  border-color: rgba(34, 211, 238, 0.36);
}

.cache-tip {
  margin-top: 0.35rem;
  color: #67e8f9;
  font-size: 0.76rem;
}

.sources-wrap {
  margin-top: 0.55rem;
  padding-top: 0.45rem;
  border-top: 1px dashed rgba(148, 163, 184, 0.26);
}

.sources-title {
  color: #a5f3fc;
  font-size: 0.78rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.sources-list {
  margin: 0;
  padding-left: 1.1rem;
}

.sources-item {
  color: #bfdbfe;
  font-size: 0.77rem;
  line-height: 1.45;
  word-break: break-all;
}

.source-link {
  color: #67e8f9;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.source-link:hover {
  color: #22d3ee;
}

.thinking {
  color: #93c5fd;
  font-style: italic;
}

.chat-input-wrap {
  margin-top: 0.9rem;
  border-top: 1px solid rgba(148, 163, 184, 0.24);
  padding-top: 0.85rem;
}

.chat-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 0.75rem;
  background: rgba(6, 18, 40, 0.84);
  color: #e2e8f0;
  padding: 0.65rem 0.75rem;
  resize: vertical;
  min-height: 80px;
}

.chat-actions {
  margin-top: 0.55rem;
  display: flex;
  justify-content: flex-end;
}

.send-btn {
  border: 1px solid rgba(34, 211, 238, 0.48);
  border-radius: 0.72rem;
  padding: 0.5rem 1.1rem;
  background: linear-gradient(120deg, #22d3ee, #3b82f6);
  color: #05213e;
  font-weight: 700;
}

.send-btn:disabled,
.new-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.empty-text {
  color: #94a3b8;
  font-size: 0.84rem;
}

.error-text {
  margin-top: 0.7rem;
  color: #fca5a5;
  font-size: 0.85rem;
}

@media (max-width: 960px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .chat-sidebar,
  .chat-main {
    min-height: auto;
  }
}
</style>

