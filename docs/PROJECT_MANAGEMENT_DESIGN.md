# 项目管理系统设计文档

## 1. 核心概念

用户可以创建多个**独立的分析项目**，每个项目有自己的：
- 文档库（用户上传 + 爬虫预加载）
- 对话历史（与该项目相关的所有查询）
- 记忆系统（项目级的长期记忆）

```
用户
  ├─ 项目1: "AI芯片技术现状"
  │   ├─ 文档库 (10+ PDFs，研究论文)
  │   ├─ 对话记录 (50+ 对话)
  │   └─ 项目记忆 (关键发现、对比结论)
  │
  ├─ 项目2: "云服务成本分析"
  │   ├─ 文档库 (白皮书、技术文档)
  │   ├─ 对话记录 (30+ 对话)
  │   └─ 项目记忆
  │
  └─ 项目3: "软件安全合规治理"
      ├─ 文档库
      ├─ 对话记录
      └─ 项目记忆
```

---

## 2. 用户工作流

### 阶段A: 项目管理
```
[登录] 
  ↓
[项目列表页] ← 显示所有项目 (创建日期、文档数、最后活跃)
  ├─ 按钮: "+ 新建项目"
  ├─ 项目卡片1 ──→ 进入项目
  ├─ 项目卡片2 ──→ 进入项目
  └─ 项目卡片3 ──→ 进入项目
```

### 阶段B: 项目内部
```
[项目详情页]
  ├─ 侧边栏
  │   ├─ 项目名: "AI芯片技术现状"
  │   ├─ 文档库 (显示10个文档)
  │   │   ├─ "市场报告-2024.pdf" (权威度:高)
  │   │   ├─ "技术白皮书.pdf" (权威度:中)
  │   │   └─ "+ 上传新文档"
  │   ├─ ← 返回项目列表 (返回主菜单)
  │   └─ 删除项目 (确认后)
  │
  └─ 主区域
      ├─ 聊天界面 (与该项目相关的对话)
      ├─ 查询时自动使用该项目的文档库
      └─ 历史记录 (该项目过往对话)
```

### 阶段C: 新建项目流程
```
[点击"新建项目"] 
  ↓
[弹窗1: 基本信息]
  ├─ 项目名: "____________" (输入框)
  ├─ 项目描述: "____________" (文本区)
  ├─ 领域分类: [下拉] 
  │   ├─ 技术与IT
  │   ├─ 金融与经济
  │   ├─ 医疗健康
  │   ├─ 能源环保
  │   └─ 自定义...
  └─ [创建] [取消]
       ↓ (创建)
[弹窗2: 初始化文档库]
  ├─ 说明: "你可以上传文档作为知识库基础"
  ├─ 方式1: 拖拽上传 (PDF/DOCX)
  ├─ 方式2: 从官方库导入 (GitHub文档/论文库)
  ├─ 方式3: 跳过，稍后添加
  └─ [完成] ← 进入项目
```

---

## 3. 数据库设计

### 表1: `projects` (项目表)
```sql
CREATE TABLE projects (
    id BIGINT PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,               -- "AI芯片技术现状"
    description TEXT,                         -- 项目介绍
    domain VARCHAR(32),                       -- "technology", "finance", "healthcare"
    doc_count INT DEFAULT 0,                  -- 文档总数
    conversation_count INT DEFAULT 0,         -- 对话总数
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL,                -- 软删除
    
    UNIQUE(user_id, name)                     -- 同一用户内项目名唯一
);
```

### 表2: `project_documents` (项目文档表)
```sql
CREATE TABLE project_documents (
    id BIGINT PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(256) NOT NULL,           -- "市场报告-2024.pdf"
    source_type VARCHAR(32) NOT NULL,         -- "user_pdf", "user_docx", "crawler_github", "crawler_arxiv"
    file_path VARCHAR(512),                   -- 存储位置 "/documents/proj_123/file_abc.pdf"
    file_size_kb INT,                         -- 文件大小（用于存储空间管理）
    chunk_count INT DEFAULT 0,                -- 语义分块数量
    authority_score FLOAT DEFAULT 0.7,        -- 权威度 (0.0-1.0)
    source_url TEXT,                          -- 来源URL（如果是爬虫源）
    upload_user_id INT REFERENCES users(id),  -- 上传者（可能是系统爬虫账号）
    
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,                   -- 处理完成时间
    deleted_at TIMESTAMP NULL,                -- 软删除
    
    INDEX (project_id),
    INDEX (uploaded_at)
);
```

### 表3: `project_document_chunks` (文档片段表)
```sql
CREATE TABLE project_document_chunks (
    id BIGINT PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES project_documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,                 -- 分块顺序
    text_content TEXT NOT NULL,               -- 分块文本（500-token）
    embedding_json JSONB,                     -- 向量嵌入 (1536维)
    token_count INT,                          -- token数量
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX (document_id, chunk_index)
);
```

### 表4: `project_conversations` (项目对话表)
```sql
CREATE TABLE project_conversations (
    id BIGINT PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id),
    title VARCHAR(256),                       -- 对话标题 (自动生成或用户编辑)
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL,
    
    INDEX (project_id, user_id),
    INDEX (created_at DESC)
);
```

### 表5: `project_conversation_messages` (对话消息表)
```sql
CREATE TABLE project_conversation_messages (
    id BIGINT PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES project_conversations(id) ON DELETE CASCADE,
    role VARCHAR(16),                         -- "user" / "assistant" / "system"
    content TEXT NOT NULL,
    
    -- RAG 相关信息
    rag_used BOOLEAN DEFAULT FALSE,           -- 是否使用了RAG
    news_used BOOLEAN DEFAULT FALSE,          -- 是否用新闻通道
    doc_used BOOLEAN DEFAULT FALSE,           -- 是否用文档通道
    doc_ids JSONB,                            -- 使用的文档IDs [1, 2, 5]
    chunk_ids JSONB,                          -- 使用的chunk IDs
    
    search_query TEXT,                        -- 用户搜索/查询词
    search_results_count INT,                 -- 返回结果数
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 表6: `project_memories` (项目级长期记忆)
```sql
CREATE TABLE project_memories (
    id BIGINT PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    conversation_id BIGINT,                   -- 来自哪个对话
    
    memory_type VARCHAR(32),                  -- "user_interest", "assistant_fact", "summary"
    text_content TEXT NOT NULL,
    normalized_text TEXT,                     -- 用于去重
    embedding_json JSONB,                     -- 向量
    
    strength FLOAT DEFAULT 1.0,               -- 强度 (往下衰减)
    hit_count INT DEFAULT 0,                  -- 被检索次数
    last_retrievedat TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. API 设计

### 项目管理 API

#### 4.1 查询项目列表
```
GET /api/projects
Response: {
    projects: [
        {
            id: 1,
            name: "AI芯片技术现状",
            description: "...",
            domain: "technology",
            doc_count: 12,
            conversation_count: 45,
            created_at: "2026-03-01T10:00:00Z",
            updated_at: "2026-03-08T15:30:00Z"
        },
        {...}
    ]
}
```

#### 4.2 创建项目
```
POST /api/projects
Body: {
    name: "AI芯片技术现状",
    description: "分析AI芯片的技术发展趋势和市场前景",
    domain: "technology"
}
Response: {
    id: 1,
    name: "AI芯片技术现状",
    ...
}
```

#### 4.3 获取项目详情
```
GET /api/projects/{project_id}
Response: {
    id: 1,
    name: "AI芯片技术现状",
    description: "...",
    domain: "technology",
    documents: [
        {
            id: 101,
            filename: "市场报告-2024.pdf",
            source_type: "user_pdf",
            chunk_count: 25,
            authority_score: 0.9,
            uploaded_at: "2026-03-02T14:20:00Z"
        },
        {...}
    ],
    stats: {
        total_documents: 12,
        total_chunks: 300,
        total_conversations: 45,
        last_activity: "2026-03-08T15:30:00Z"
    }
}
```

#### 4.4 删除项目
```
DELETE /api/projects/{project_id}
Response: { success: true }
```

---

### 文档管理 API

#### 4.5 上传文档
```
POST /api/projects/{project_id}/documents
Content-Type: multipart/form-data
Body: {
    file: <File>,
    authority_score: 0.85  // 可选，默认0.7
}
Response: {
    id: 101,
    filename: "市场报告-2024.pdf",
    status: "processing"  // 异步处理
}
```

#### 4.6 查询文档列表
```
GET /api/projects/{project_id}/documents
Response: {
    documents: [
        {
            id: 101,
            filename: "市场报告-2024.pdf",
            source_type: "user_pdf",
            chunk_count: 25,
            authority_score: 0.9,
            uploaded_at: "2026-03-02T14:20:00Z",
            status: "completed"
        },
        {...}
    ]
}
```

#### 4.7 删除文档
```
DELETE /api/projects/{project_id}/documents/{doc_id}
Response: { success: true }
```

---

### 对话 API

#### 4.8 发送消息（项目级）
```
POST /api/projects/{project_id}/chat
Body: {
    message: "AI芯片最新的技术进展有哪些？",
    conversation_id: 5  // 可选，新对话不提供
}
Response: {
    conversation_id: 5,
    message_id: 201,
    response: "根据最新文档...",
    rag_info: {
        used: true,
        news_count: 2,
        doc_count: 4,
        documents: [
            { id: 101, filename: "...", chunks: [1, 5, 8] }
        ],
        conflicts: []  // 冲突信息
    },
    memory_info: {
        captured: true,
        count: 3
    }
}
```

#### 4.9 查询对话历史
```
GET /api/projects/{project_id}/conversations
Response: {
    conversations: [
        {
            id: 5,
            title: "AI芯片技术进展",
            message_count: 8,
            created_at: "2026-03-08T10:00:00Z",
            updated_at: "2026-03-08T15:30:00Z"
        },
        {...}
    ]
}
```

#### 4.10 获取对话详情（完整记录）
```
GET /api/projects/{project_id}/conversations/{conversation_id}
Response: {
    id: 5,
    title: "AI芯片技术进展",
    messages: [
        { role: "user", content: "...", created_at: "..." },
        { role: "assistant", content: "...", rag_info: {...} },
        ...
    ]
}
```

---

## 5. 前端页面设计

### 5.1 项目列表页 (新增)
```
[Header: TechEyes 项目分析平台]
[右上: 用户菜单]

[左侧导航]
├─ 项目列表 (当前页)
├─ 设置
└─ 帮助

[主区域]
├─ [+ 新建项目] (按钮)
│
├─ 项目卡片1
│  ├─ 📊 项目名: "AI芯片技术现状"
│  ├─ 文档数: 12 | 对话数: 45
│  ├─ 最后活跃: 2小时前
│  └─ [进入] [删除]
│
├─ 项目卡片2
│  └─ ...
│
└─ 项目卡片3
   └─ ...
```

### 5.2 项目详情页 (新增)
```
[Header]

[左侧边栏 - 项目面板]
├─ 📂 当前项目
│  └─ "AI芯片技术现状"
│
├─ 📄 知识库 (12 文档)
│  ├─ [展开/收起]
│  ├─ 市场报告-2024.pdf (权威度: ⭐⭐⭐)
│  ├─ 技术白皮书.pdf (权威度: ⭐⭐)
│  └─ [+ 上传文档]
│
├─ 💬 对话历史 (45 条)
│  ├─ [展开/收起]
│  ├─ "AI芯片最新进展" (2h ago)
│  ├─ "成本对比分析" (1d ago)
│  └─ [查看全部]
│
└─ [← 返回项目列表]

[主区域 - 聊天界面]
├─ 聊天历史
├─ 输入框: "在此输入查询..."
└─ [发送]
```

### 5.3 文档上传页面 (新增/嵌入)
```
[项目设置 - 文档管理]

[上传区域]
├─ 拖拽上传或点击选择
├─ 支持: PDF, DOCX, TXT
├─ 本次: ______ (进度条)
└─ [处理中...]

[已上传文档列表]
├─ 市场报告-2024.pdf
│  ├─ 大小: 12MB | 页数: 45 | 分块: 25
│  ├─ 权威度: [滑块] 0.85
│  └─ [删除]
│
└─ ...

[导入官方文档库]
├─ GitHub 官方库 (可选)
├─ ArXiv 论文库 (可选)
└─ [导入]
```

---

## 6. 实现步骤

### Phase 1: 数据库 + 基础 API (2 天)
- [ ] 创建 6 个数据库表
- [ ] 创建 SQLAlchemy 模型（models/project.py）
- [ ] 实现项目管理 API（创建、查询、删除）
- [ ] 实现文档上传 API（基础版，还不处理向量）
- [ ] 数据库迁移脚本

### Phase 2: 文档处理 + 向量化 (3 天)
- [ ] 集成 PDF/DOCX 解析器（pypdf, python-docx）
- [ ] 实现语义分块算法 (500-token chunks with 50% overlap)
- [ ] 集成 Embedding API (OpenAI, 或本地模型)
- [ ] 异步处理队列（Celery 或 BackgroundTasks）
- [ ] 存储 chunks + embeddings

### Phase 3: 双通道 RAG 集成 (2 天)
- [ ] 创建 project_search_service.py
- [ ] 实现项目文档搜索（向量相似度）
- [ ] 集成新闻搜索通道（Tavily API）
- [ ] 融合+重排逻辑（项目文档优先）
- [ ] 在 chat_service 中调用（project_id 参数）

### Phase 4: 前端 - 项目管理页面 (2 天)
- [ ] 创建 ProjectListPage.vue
- [ ] 创建 ProjectDetailPage.vue
- [ ] 新建项目弹窗
- [ ] 项目删除确认
- [ ] 路由：/projects, /projects/:id

### Phase 5: 前端 - 文档上传 + 聊天集成 (2 天)
- [ ] 文档上传组件
- [ ] 文档列表管理
- [ ] 修改 ChatPage.vue（支持 project_id）
- [ ] 显示 RAG 来源信息
- [ ] 对话历史与项目关联

### Phase 6: 优化 + 上线 (1 天)
- [ ] 性能优化（索引、缓存）
- [ ] 错误处理和日志
- [ ] UI 细节打磨
- [ ] 文档更新

---

## 7. 技术选型

| 层 | 技术 | 备注 |
|----|------|------|
| **文档解析** | pypdf, python-docx | 标准库 |
| **分块算法** | LangChain RecursiveCharacterTextSplitter | 经过验证 |
| **Embedding** | OpenAI API / 本地模型 (BAAI/bge) | 可配置 |
| **向量DB** | Milvus / Chroma / Pinecone | 推荐 Milvus (自托管) |
| **异步任务** | FastAPI BackgroundTasks / Celery | 视规模 |
| **前端路由** | Vue Router | 支持多页面 |
| **状态管理** | Pinia / Vuex | 项目级状态 |

---

## 8. 用户体验流程示例

```
[用户登录]
  ↓
[项目列表] ← 空，显示"还没有项目"
  ↓
[点击"新建项目"]
  ↓
[输入基本信息]
  name: "大模型应用现状"
  domain: "AI/LLM"
  ↓
[进入项目]
  ↓
[上传初始文档]
  - 拖拽上传 3 个 PDF (自动处理成 chunks + embeddings)
  - 或导入 GitHub 官方文档库
  ↓
[开始对话]
  user: "与 GPT-4o 相比，Qwen 的优势和劣势是什么？"
  ↓
  [后台流程]
  1. 搜索项目文档库 (向量相似度)
  2. 搜索最新新闻 (Tavily)
  3. 融合+重排
  4. 注入 LLM
  ↓
  assistant: "根据项目中的文档和最新新闻，..."
  ↓
  [捕获对话记忆 → 项目级长期记忆]
  ↓
[对话历史自动保存到该项目]
  ↓
[用户可随时]
  - 上传更多文档
  - 切换其他项目
  - 查看该项目的所有对话历史
```

---

## 9. 核心价值

✅ **多领域并行分析** - 不同项目互不污染  
✅ **知识库积累** - 项目文档持久化，可复用  
✅ **对话可追溯** - 知道引用来自哪个文档  
✅ **企业级灵活性** - 支持团队/部门级项目管理 (未来)  

这个系统既展示了 **工程化 RAG**，也适合做成 **SaaS 产品**。
