# 前端设计完成总结

## 🎨 已完成的页面和组件

### 1. ProjectListPage.vue
**路由**: `/projects`

**功能**:
- 显示用户创建的所有项目的网格列表
- 每个项目卡片展示：项目名称、描述、文档数、对话数、域名分类
- 创建新项目按钮 → 打开 CreateProjectDialog
- 项目卡片右上角菜单：编辑、删除
- 时间显示：最后更新时间（相对时间 "2天前"）
- 空状态：没有项目时显示提示和创建按钮

**样式特性**:
- 响应式网格布局（桌面：3列，平板：2列，手机：1列）
- 卡片 hover 动画（上升+阴影）
- 梯度背景（蓝紫色）
- Tailwind CSS 完整样式

**数据交互**:
```ts
// 加载
loadProjects() → GET /api/projects

// 创建
handleCreateProject() → POST /api/projects

// 删除
deleteProject() → DELETE /api/projects/{id}

// 进入项目
enterProject() → push("/projects/{id}")
```

---

### 2. ProjectDetailPage.vue
**路由**: `/projects/:id`

**布局**: 左侧面板 + 主区域（二栏式）

#### 左侧面板（固定宽350px）:

**1) 项目信息区**
- 返回按钮 ← 回到项目列表
- 项目标题 + 域名badge
- 三个标签页：文档库、对话历史、项目设置

**2) 文档库标签页**
- 文档计数器 (显示 "12")
- 上传按钮 (+ 图标)
- 文档列表：
  - 文档图标
  - 文档名称
  - 元数据：分块数、文件大小
  - 删除按钮（处理中时禁用）
- 空状态："还没有文档，点击上传第一个"
- 上传提示：支持 PDF、Word、TXT

**3) 对话历史标签页**
- 对话计数器
- 对话列表（可点击）：
  - 对话标题（默认 "未命名对话"）
  - 创建时间（相对时间）
  - Active 状态样式（蓝色背景）
- 空状态："开始一个新对话"

**4) 项目设置标签页**
- 项目信息只读：项目名、描述、创建日期
- 危险区域：删除项目按钮 → 确认对话框

#### 主区域（聊天界面）:

**header**:
- 标题："分析对话"
- 副标题：显示文档数、对话数
- "新建对话" 按钮

**消息区**:
- 消息列表（用户/助手分别对齐）
- 用户消息：右对齐，绿色、白色文字
- 助手消息：左对齐，灰色背景
- 消息气泡支持 Markdown 渲染
- 加载状态：spinner + "正在分析中..."
- 空状态：大图标 + 提示文字 "开始分析"

**RAG 信息显示**:
```
参考信息来源
📄 项目文档  4份
📰 最新新闻  2条
```

**输入区**:
- 多行文本框
- 快捷键：Shift+Enter 换行，Enter 发送
- 发送按钮（禁用条件：空内容 / 加载中 / 无文档）
- 输入提示：" 💡 分析基于项目文档和最新信息" 或 "⬆️ 请先上传文档"

---

### 3. CreateProjectDialog.vue
**触发**: ProjectListPage 的 "+ 新建项目" 按钮

**表单字段**:
1. **项目名称** (必填)
   - 输入框
   - placeholder: "如: AI芯片技术现状与前景"

2. **项目描述** (可选)
   - 文本区 (4行)
   - placeholder: "简要描述这个项目的目标和范围..."

3. **领域分类** (必填)
   - 下拉选择：
     - 科技与 IT
     - 金融与经济
     - 医疗与健康
     - 能源与环保
     - 产业发展
     - 其他

**按钮**:
- 取消 (关闭弹窗)
- 创建项目 (禁用条件：name/domain 为空)

**交互**:
- 点击背景关闭
- 点击 X 按钮关闭
- 提交 → emit create + 关闭

---

### 4. ConfirmDialog.vue
**通用确认对话框**

**Props**:
- `title`: 确认标题
- `message`: 确认信息

**使用场景**:
1. 删除项目：标题 "删除项目 '{name}'？"，警告信息
2. 删除文档：标题 "确认删除此文档？"

**样式**:
- 红色表示危险操作
- 确认按钮红色，取消按钮灰色

---

## 📱 样式系统

### 颜色方案
- **主色**: `#667eea` 紫蓝 (Tailwind indigo-500)
- **辅助色**: `#764ba2` 紫 (用于 hover)
- **背景**: 梯度蓝白 `linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)`
- **文本**: `#1a202c` 深灰 (titles), `#4a5568` 中灰 (body), `#718096` 浅灰
- **边框**: `#e2e8f0` 淡灰
- **成功**: `#48bb78` 绿
- **危险**: `#e53e3e` 红

### 动画
- 卡片 hover: `transform: translateY(-4px)` + `box-shadow`
- 弹窗出现: `fadeIn 0.2s` + `slideUp 0.3s`
- Spinner: `spin 0.6s linear infinite`

### 响应式断点
- 桌面: `>= 1024px`
- 平板: `768px - 1023px`
- 手机: `< 768px`

---

## 🔌 API 集成

### 在 services/api.ts 中新增方法

**项目管理**:
```ts
createProject(data) → POST /api/projects
getProjects() → GET /api/projects
getProject(id) → GET /api/projects/{id}
updateProject(id, data) → PUT /api/projects/{id}
deleteProject(id) → DELETE /api/projects/{id}
```

**文档管理**:
```ts
uploadProjectDocument(projectId, formData) → POST /api/projects/{id}/documents
getProjectDocuments(projectId) → GET /api/projects/{id}/documents
deleteProjectDocument(projectId, docId) → DELETE /api/projects/{id}/documents/{docId}
```

**对话**:
```ts
getProjectConversations(projectId) → GET /api/projects/{id}/conversations
getProjectConversation(projectId, convId) → GET /api/projects/{id}/conversations/{convId}
sendProjectMessage(projectId, data) → POST /api/projects/{id}/chat
```

**便捷客户端**:
```ts
apiClient.get(path, config?)
apiClient.post(path, data?, config?)
apiClient.put(path, data?, config?)
apiClient.delete(path, config?)
```

---

## 📍 路由配置

### 更新 src/router/index.ts

```ts
{
  path: '/projects',
  name: 'ProjectList',
  component: () => import('@/views/ProjectListPage.vue'),
  meta: { requiresAuth: true }
}

{
  path: '/projects/:id',
  name: 'ProjectDetail',
  component: () => import('@/views/ProjectDetailPage.vue'),
  props: true,
  meta: { requiresAuth: true }
}
```

---

## 📊 状态管理

### 组件内 ref

**ProjectListPage**:
```ts
projects: Project[]          // 项目列表
loading: boolean             // 加载状态
showCreateDialog: boolean    // 新建对话框显示
showDeleteConfirm: boolean   // 删除确认显示
activeMenu: number | null    // 当前展开的菜单
deleteTarget: Project | null // 待删除项目
```

**ProjectDetailPage**:
```ts
project: Project | null      // 当前项目
documents: Document[]        // 文档列表
conversations: Conversation[]// 对话列表
messages: Message[]          // 当前消息列表
activeTab: string           // 当前标签页 (documents/conversations/settings)
activeConversationId: number | null  // 当前对话
userInput: string           // 输入框内容
loading: boolean            // 消息加载状态
```

---

## 🎯 关键交互流程

### 流程1: 创建项目
```
ProjectListPage
  ↓ 点击 "+ 新建项目"
  ↓ showCreateDialog = true
  ↓ CreateProjectDialog 显示
  ↓ 用户填表 + 点击"创建项目"
  ↓ emit('create', formData)
  ↓ handleCreateProject()
  ↓ POST /api/projects
  ↓ projects.unshift(result)
  ↓ showCreateDialog = false
```

### 流程2: 进入项目查看文档并发送消息
```
ProjectListPage
  ↓ 点击项目卡片"进入项目"
  ↓ router.push("/projects/{id}")
  ↓ ProjectDetailPage mounted
  ↓ loadProject() + loadDocuments() + loadConversations()
  ↓ 点击文档库标签页
  ↓ 显示已上传的文档
  ↓ 点击上传按钮
  ↓ handleFileSelect()
  ↓ POST /api/projects/{id}/documents (formData)
  ↓ documents.push(result)
  ↓ activeTab = 'documents'
  ↓ 输入查询 + 发送
  ↓ sendMessage()
  ↓ POST /api/projects/{id}/chat
  ↓ messages.push(user + assistant)
  ↓ RAG 信息展示
```

### 流程3: 查看对话历史
```
ProjectDetailPage
  ↓ 点击"对话历史"标签页
  ↓ 显示 conversations 列表
  ↓ 点击某个对话
  ↓ selectConversation(id)
  ↓ GET /api/projects/{id}/conversations/{id}
  ↓ messages = responseData
  ↓ 显示完整对话记录
```

### 流程4: 删除项目
```
ProjectListPage
  ↓ 项目卡片右上角菜单 ⋯
  ↓ 点击"删除"
  ↓ deleteProject(project)
  ↓ showDeleteConfirm = true
  ↓ ConfirmDialog 显示
  ↓ 点击"确认删除"
  ↓ DELETE /api/projects/{id}
  ↓ projects.filter(...)
  ↓ showDeleteConfirm = false
```

---

## 🎁 使用感受

### 优势
✅ **项目隔离** - 不同领域数据互不干扰  
✅ **清晰导航** - 项目列表 → 详情 → 对话流畅  
✅ **一致设计** - 统一的组件库和样式  
✅ **移动友好** - 完整的响应式适配  
✅ **实时反馈** - 加载状态、空状态、错误提示  

### 交互细节
- 文档上传支持拖拽
- Shift+Enter 换行，Enter 发送
- 消息自动滚动到最新
- 对话记录自动更新（刷新列表）
- 删除操作需要二次确认

---

## 📋 已完成的文件清单

```
frontend/src/
├── views/
│   ├── ProjectListPage.vue ✅ (新建)
│   └── ProjectDetailPage.vue ✅ (新建)
├── components/
│   └── dialogs/
│       ├── CreateProjectDialog.vue ✅ (新建)
│       └── ConfirmDialog.vue ✅ (新建)
├── services/
│   └── api.ts ✅ (添加项目管理 API)
└── router/
    └── index.ts ✅ (添加路由)
```

---

## ✅ 下一步：后端 Phase 1 实现

现在可以开始实现后端：

1. **数据库模型** (`backend/models/project.py`)
   - Project, ProjectDocument, ProjectDocumentChunk
   - ProjectConversation, ProjectConversationMessage, ProjectMemory

2. **服务层** (`backend/services/project_service.py`)
   - ProjectService: CRUD 操作

3. **API 路由** (`backend/api/projects_routes.py`)
   - 10+ 个 FastAPI 端点

4. **数据库初始化** (`backend/scripts/init_project_tables.py`)
   - 运行脚本创建表

详见: `PHASE1_IMPLEMENTATION.md`

