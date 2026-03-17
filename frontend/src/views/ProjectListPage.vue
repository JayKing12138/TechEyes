<template>
  <div class="min-h-screen techeyes-page-shell project-list-shell">
    <Header />

    <main class="container mx-auto px-4 md:px-8 pt-24 pb-10">
      <!-- 顶部区域 -->
      <div class="project-header">
        <div>
          <h1 class="page-title">我的分析项目</h1>
          <p class="page-subtitle">创建和管理多个领域的深度分析项目</p>
        </div>
        <button class="btn-primary btn-lg" @click="openCreateProjectDialog">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          新建项目
        </button>
      </div>

      <!-- 空状态 -->
      <div v-if="projects.length === 0 && !loading" class="empty-state">
        <svg class="w-16 h-16 mx-auto mb-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 class="text-xl font-semibold text-slate-100 mb-2">还没有项目</h3>
        <p class="text-slate-300 mb-6">开始创建你的第一个分析项目</p>
        <button class="btn-primary" @click="openCreateProjectDialog">创建项目</button>
      </div>

      <!-- 项目网格 -->
      <div v-else class="projects-grid">
        <div v-for="project in projects" :key="project.id" class="project-card techeyes-panel-soft">
          <div class="card-header">
            <h3 class="project-name">{{ project.name }}</h3>
            <div class="card-menu">
              <button class="menu-btn" @click.stop="toggleProjectMenu(project.id)">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                </svg>
              </button>
              <div v-if="activeMenu === project.id" class="dropdown-menu" @click.stop>
                <button @click="editProject(project)">编辑</button>
                <button class="danger" @click="deleteProject(project)">删除</button>
              </div>
            </div>
          </div>

          <p class="project-description">{{ project.description }}</p>

          <div class="project-meta">
            <span class="meta-item">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <span>{{ project.doc_count }} 个文档</span>
            </span>
            <span class="meta-item">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{{ project.conversation_count }} 个对话</span>
            </span>
          </div>

          <div class="project-domain">
            <span class="domain-tag" :class="`domain-${project.domain}`">
              {{ domainLabel(project.domain) }}
            </span>
          </div>

          <div class="card-footer">
            <span class="text-xs text-slate-400">
              {{ formatDate(project.updated_at) }}
            </span>
            <button class="btn-secondary btn-sm" @click="enterProject(project.id)">
              进入项目 →
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 新建项目弹窗 -->
    <CreateProjectDialog 
      v-if="showCreateDialog" 
      @create="handleCreateProject" 
      @close="showCreateDialog = false"
    />

    <EditProjectDialog
      v-if="showEditDialog && editTarget"
      :project="editTarget"
      @update="handleEditProject"
      @close="closeEditDialog"
    />

    <!-- 删除确认弹窗 -->
    <ConfirmDialog
      v-if="showDeleteConfirm"
      :title="`删除项目 '${deleteTarget?.name}'？`"
      message="删除后不可恢复，该项目的所有文档和对话记录也将被删除。"
      @confirm="handleConfirmDelete"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import Header from '@/components/Header.vue'
import CreateProjectDialog from '@/components/dialogs/CreateProjectDialog.vue'
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue'
import EditProjectDialog from '@/components/dialogs/EditProjectDialog.vue'
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

const router = useRouter()

const projects = ref<Project[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteConfirm = ref(false)
const activeMenu = ref<number | null>(null)
const deleteTarget = ref<Project | null>(null)
const editTarget = ref<Project | null>(null)

// 获取项目列表
const loadProjects = async () => {
  loading.value = true
  try {
    const { projects: data } = await apiClient.get('/projects')
    projects.value = data || []
  } catch (error) {
    console.error('Failed to load projects:', error)
  } finally {
    loading.value = false
  }
}

// 打开新建项目对话框
const openCreateProjectDialog = () => {
  showCreateDialog.value = true
}

// 处理创建项目
const handleCreateProject = async (data: any) => {
  try {
    const result = await apiClient.post('/projects', data)
    projects.value.unshift(result)
    showCreateDialog.value = false
  } catch (error) {
    console.error('Failed to create project:', error)
  }
}

// 进入项目
const enterProject = (projectId: number) => {
  router.push(`/projects/${projectId}`)
}

// 编辑项目
const editProject = (project: Project) => {
  editTarget.value = { ...project }
  showEditDialog.value = true
  activeMenu.value = null
}

// 处理编辑项目
const handleEditProject = async (data: { name: string; description?: string; domain?: string }) => {
  if (!editTarget.value) return

  try {
    const updated = await apiClient.put(`/projects/${editTarget.value.id}`, data)
    projects.value = projects.value.map((p) => (p.id === editTarget.value!.id ? { ...p, ...updated } : p))
    showEditDialog.value = false
    editTarget.value = null
  } catch (error) {
    console.error('Failed to update project:', error)
  }
}

const closeEditDialog = () => {
  showEditDialog.value = false
  editTarget.value = null
}

// 删除项目
const deleteProject = (project: Project) => {
  deleteTarget.value = project
  showDeleteConfirm.value = true
  activeMenu.value = null
}

// 处理确认删除
const handleConfirmDelete = async () => {
  if (!deleteTarget.value) return
  
  try {
    await apiClient.delete(`/projects/${deleteTarget.value.id}`)
    projects.value = projects.value.filter(p => p.id !== deleteTarget.value!.id)
    showDeleteConfirm.value = false
    deleteTarget.value = null
  } catch (error) {
    console.error('Failed to delete project:', error)
  }
}

// 切换菜单
const toggleProjectMenu = (projectId: number) => {
  activeMenu.value = activeMenu.value === projectId ? null : projectId
}

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  if (!target?.closest('.card-menu')) {
    activeMenu.value = null
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  if (days < 30) return `${Math.floor(days / 7)}周前`
  return `${Math.floor(days / 30)}月前`
}

// 域名标签
const domainLabel = (domain: string) => {
  const labels: Record<string, string> = {
    'technology': '科技/IT',
    'finance': '金融经济',
    'healthcare': '医疗健康',
    'energy': '能源环保',
    'industry': '产业发展',
    'other': '其他'
  }
  return labels[domain] || domain
}

onMounted(() => {
  loadProjects()
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped>
.project-list-shell {
  background:
    radial-gradient(1200px 760px at 20% 0%, rgba(34, 211, 238, 0.11), transparent 64%),
    radial-gradient(1000px 680px at 88% 18%, rgba(59, 130, 246, 0.12), transparent 62%),
    linear-gradient(130deg, #050a1b 0%, #091730 48%, #0a1230 100%);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3rem;
  padding: 0;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: #9fb4cf;
  font-size: 0.95rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #0891b2 0%, #2563eb 100%);
  color: white;
  border: 1px solid rgba(125, 211, 252, 0.35);
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(8, 145, 178, 0.32);
}

.btn-lg {
  padding: 0.875rem 2rem;
  font-size: 1rem;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
}

.project-card {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  background: linear-gradient(165deg, rgba(9, 23, 48, 0.9) 0%, rgba(11, 33, 64, 0.82) 100%);
  border-radius: 0.75rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  position: relative;
}

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 34px rgba(2, 6, 23, 0.46);
  border-color: rgba(125, 211, 252, 0.46);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.project-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
  flex: 1;
}

.card-menu {
  position: relative;
}

.menu-btn {
  background: rgba(148, 163, 184, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #cbd5e1;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.menu-btn:hover {
  background: rgba(56, 189, 248, 0.18);
  color: #e2e8f0;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: rgba(6, 17, 38, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 0.5rem;
  min-width: 120px;
  box-shadow: 0 16px 28px rgba(2, 6, 23, 0.42);
  backdrop-filter: blur(10px);
  z-index: 10;
}

.dropdown-menu button {
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  text-align: left;
  color: #dbe7f6;
  cursor: pointer;
  transition: background 0.2s ease;
}

.dropdown-menu button:hover {
  background: rgba(56, 189, 248, 0.15);
}

.dropdown-menu button.danger {
  color: #e53e3e;
}

.project-description {
  color: #a8bfd8;
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0 0 1rem 0;
  flex: 1;
}

.project-meta {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #b8cbe0;
}

.meta-item svg {
  color: #38bdf8;
}

.project-domain {
  margin-bottom: 1rem;
}

.domain-tag {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.domain-technology {
  background: rgba(56, 189, 248, 0.2);
  color: #bae6fd;
}

.domain-finance {
  background: rgba(250, 204, 21, 0.2);
  color: #fde68a;
}

.domain-healthcare {
  background: rgba(34, 197, 94, 0.2);
  color: #bbf7d0;
}

.domain-energy {
  background: rgba(248, 113, 113, 0.2);
  color: #fecaca;
}

.domain-industry {
  background: rgba(244, 114, 182, 0.18);
  color: #fbcfe8;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: rgba(15, 35, 70, 0.48);
  border: 1px solid rgba(148, 163, 184, 0.38);
  color: #93c5fd;
  border-radius: 0.375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: rgba(37, 99, 235, 0.28);
  color: #dbeafe;
  border-color: rgba(125, 211, 252, 0.58);
}

.btn-sm {
  font-size: 0.875rem;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
}

@media (max-width: 768px) {
  .project-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .projects-grid {
    grid-template-columns: 1fr;
  }

  .page-title {
    font-size: 1.5rem;
  }
}
</style>
