# TechEyes - Multi-Agent AI 科技行业分析平台

**基于 LangChain 和 FastAPI 的多智能体协作系统，专注于科技行业深度分析和情报挖掘**




## 📋 目录

- [项目概述](#-项目概述)
- [核心功能](#-核心功能)
- [技术架构](#-技术架构)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [配置指南](#-配置指南)

---

## 🎯 项目概述

TechEyes 是一个 Multi-Agent AI 系统，专门用于科技行业的深度分析和情报挖掘。通过多个专业化智能体的协作，系统能够自动分解复杂任务、收集多源信息、进行深度分析，并提供综合性的洞察报告。

### 🌟 核心亮点

- **🤖 Multi-Agent 协作**: 5个专业化Agent协同工作
- **🧠 智能任务编排**: 自动分解复杂查询为可执行子任务
- **🔍 多源信息收集**: 网络搜索 + 数据库查询 + 历史数据
- **📊 深度数据分析**: 技术路线、市场地位、竞争力分析
- **✅ 质量保证机制**: CriticAgent + Reflection 自动纠错
- **⚡ 高性能缓存**: Redis语义缓存，显著降低API成本
- **🎨 现代化UI**: React + Framer Motion，流式实时展示
- **🔧 灵活工具集成**: 支持MCP协议，易于扩展

### 🎯 应用场景

- **🏢 企业战略分析**: 竞争对手分析、市场趋势预测
- **📈 投资研究**: 行业公司深度分析、技术路线评估
- **🔬 政策研究**: 政策影响分析、合规性检查
- **📰 媒体监测**: 新闻热点追踪、舆情分析
- **💼 产品规划**: 技术选型、功能对比分析

---

## 🚀 核心功能

### 1. 🎯 智能启动页面 (LandingPage)

**功能特性:**
- 🔍 **智能搜索框**: 类似Google的现代化搜索界面
  - 实时搜索建议
  - 搜索历史记录
  - 快捷键支持
- 🎨 **背景动画**: 深蓝色科技风格背景
  - 动态粒子效果
  - 平滑过渡动画
- 📋 **功能介绍卡片**: 
  - Multi-Agent协作说明
  - 智能分析能力展示
  - 使用案例演示
- 🎯 **快速开始引导**: 新用户友好的入门流程

**技术实现:**
- React 18+ with Hooks
- Framer Motion动画库
- TailwindCSS样式
- 响应式设计

---

### 2. 📊 分析过程页面 (AnalysisPage)

**功能特性:**
- 📈 **实时进度条**: 0-100%进度可视化
  - 分阶段进度显示
  - 预计剩余时间
  - 动画进度效果
- 🔄 **任务流程可视化** (TaskFlow):
  - 显示每个Agent的执行状态
  - 任务依赖关系图
  - 执行时间统计
  - 错误状态标识
- 📝 **实时输出流**:
  - Agent思考过程展示
  - 中间结果实时更新
  - Markdown格式化输出
  - 代码高亮支持
- ⏱️ **加载动画**: 优雅的加载状态指示

**技术实现:**
- Server-Sent Events (SSE)流式通信
- WebSocket实时连接
- 动态组件渲染
- 状态管理 (Pinia)

---

### 3. 📈 结果页面 (ResultPage)

**功能特性:**
- 📋 **执行摘要卡片**:
  - 总处理时间
  - 参与Agent数量
  - 数据来源统计
  - 缓存命中情况
- 📅 **历史时间轴** (TimelineView):
  - 时间点标记
  - 重要事件高亮
  - 关键公司标签
  - 重要性级别分类
- 📊 **对比分析** (ComparisonTable):
  - 多维度对比表格
  - 评分条形图
  - 分析洞察总结
  - 发展趋势预测
- 🚀 **未来展望**:
  - 发展趋势列表
  - 场景推演 (概率、影响)
  - 投资建议
  - 风险提示

**数据可视化:**
- ECharts图表库
- 响应式图表设计
- 交互式数据探索
- 导出功能支持

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   用户界面层                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ LandingPage │  │ AnalysisPage │  │ ResultPage   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────┐
│                   API网关层                       │
│              ┌────────────────────────┐           │
│              │   FastAPI Router    │           │
│              └────────────────────────┘           │
└─────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────┐
│                 业务逻辑层                         │
│  ┌─────────────────────────────────────────────┐   │
│  │         Multi-Agent 协作系统          │   │
│  │  ┌──────────┐  ┌──────────┐         │   │
│  │  │Orchestrator│  │Researcher │         │   │
│  │  │   Agent   │  │  Agent    │         │   │
│  │  └──────────┘  └──────────┘         │   │
│  │  ┌──────────┐  ┌──────────┐         │   │
│  │  │ Analyzer  │  │  Critic   │         │   │
│  │  │  Agent    │  │  Agent    │         │   │
│  │  └──────────┘  └──────────┘         │   │
│  │  ┌──────────┐                     │   │
│  │  │Synthesizer│                     │   │
│  │  │  Agent    │                     │   │
│  │  └──────────┘                     │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────┐
│                 数据服务层                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Redis    │  │ PostgreSQL│  │  Neo4j   │ │
│  │ Cache    │  │  Database │  │  Graph DB │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────┐
│                 外部服务层                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ LLM API  │  │Search API │  │  Doc API  │ │
│  │(OpenAI)  │  │ (Tavily)  │  │ (MineRU) │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────┘
```

### 技术栈

#### 前端技术
- **框架**: React 18.2+ (Hooks + Concurrent Features)
- **语言**: TypeScript 5.0+
- **构建工具**: Vite 5.0+
- **UI组件**: 
  - TailwindCSS 3.4+ (样式)
  - Framer Motion 10.16+ (动画)
  - ECharts 6.0+ (图表)
- **状态管理**: Pinia 2.1+
- **路由**: React Router 6.20+
- **HTTP客户端**: Axios 1.6+
- **Markdown**: md-editor-v3 4.12+

#### 后端技术
- **框架**: FastAPI 0.104+
- **语言**: Python 3.10+
- **AI框架**: LangChain 0.3+
- **数据库**: 
  - PostgreSQL 15+ (关系型数据)
  - Neo4j 5.0+ (图数据库)
  - Redis 7.0+ (缓存和会话)
- **ORM**: SQLModel 0.0.14+
- **异步**: asyncio + uvloop
- **工具集成**: MCP协议支持

#### AI/ML服务
- **LLM提供商**: OpenAI, Anthropic, DeepSeek, 通义千问
- **搜索服务**: Tavily, DuckDuckGo, SERPAPI
- **文档解析**: MineRU (PDF/Word/Excel)
- **嵌入模型**: text-embedding-ada-002, text-embedding-v4

---

## 📁 项目结构

```
techeyes_langchain/
├── 📂 docs/                          # 项目文档
│   ├── README.md                     # 项目说明文档
│   ├── DATABASE_SETUP.md             # 数据库配置指南
│   ├── REDIS_SETUP.md                # Redis配置指南
│   ├── POSTGRESQL_SETUP.md           # PostgreSQL配置指南
│   ├── NEWS_RADAR_README.md          # 新闻雷达功能说明
│   ├── NEWS_RADAR_SKILLS.md          # 新闻雷达技能文档
│   ├── MULTI_AGENT_RAG_IMPLEMENTATION.md  # Multi-Agent实现文档
│   ├── PROJECT_MANAGEMENT_DESIGN.md  # 项目管理设计文档
│   └── USER_TEST_GUIDE.md           # 用户测试指南
│
├── 🎨 frontend/                      # 前端应用
│   ├── src/
│   │   ├── pages/                   # 页面组件
│   │   │   ├── LandingPage.vue     # 启动页面
│   │   │   ├── AnalysisPage.vue    # 分析过程页面
│   │   │   └── ResultPage.vue      # 结果展示页面
│   │   ├── components/              # 可复用组件
│   │   │   ├── TaskFlow.vue       # 任务流程可视化
│   │   │   ├── TimelineView.vue   # 时间轴视图
│   │   │   ├── ComparisonTable.vue # 对比分析表格
│   │   │   ├── SearchBar.vue      # 搜索框组件
│   │   │   └── MarkdownRenderer.vue # Markdown渲染器
│   │   ├── services/               # API服务
│   │   │   └── api.ts           # API调用封装
│   │   ├── stores/                 # 状态管理
│   │   │   └── analysis.ts      # 分析状态管理
│   │   ├── types/                  # TypeScript类型定义
│   │   │   └── index.ts         # 类型声明
│   │   ├── App.vue                 # 根组件
│   │   ├── main.ts                 # 应用入口
│   │   └── vite.config.ts          # Vite配置
│   ├── package.json                  # 依赖配置
│   ├── tailwind.config.js            # Tailwind配置
│   └── tsconfig.json               # TypeScript配置
│
├── 🚀 backend/                       # 后端服务
│   ├── agents/                      # Agent系统
│   │   ├── base.py                 # Agent基类
│   │   ├── orchestrator_agent.py   # 任务编排Agent
│   │   ├── researcher_agent.py    # 信息收集Agent
│   │   ├── analyzer_agent.py      # 数据分析Agent
│   │   ├── critic_agent.py        # 质量审查Agent
│   │   ├── synthesizer_agent.py   # 结果综合Agent
│   │   └── rag/                    # RAG相关Agent
│   │       ├── planner_agent.py      # RAG规划Agent
│   │       ├── retriever_agent.py   # RAG检索Agent
│   │       ├── reranker_agent.py    # RAG重排Agent
│   │       ├── router_agent.py      # RAG路由Agent
│   │       ├── synthesizer_agent.py # RAG综合Agent
│   │       ├── critic_agent.py      # RAG审查Agent
│   │       └── web_news_agent.py   # 新闻雷达Agent
│   ├── api/                         # API路由
│   │   ├── routes.py               # 主路由
│   │   ├── projects_routes.py     # 项目相关路由
│   │   └── news_radar_routes.py   # 新闻雷达路由
│   ├── services/                    # 业务服务
│   │   ├── analysis_service.py     # 分析服务
│   │   ├── cache_service.py        # 缓存服务
│   │   ├── auth_service.py         # 认证服务
│   │   ├── chat_service.py         # 对话服务
│   │   ├── conversation_store.py   # 对话存储
│   │   ├── document_service.py     # 文档服务
│   │   ├── history_store.py        # 历史存储
│   │   ├── hybrid_retriever.py    # 混合检索器
│   │   ├── memory_service.py       # 记忆服务
│   │   ├── neo4j_client.py        # Neo4j客户端
│   │   ├── news_cache.py          # 新闻缓存
│   │   ├── news_radar_service.py  # 新闻雷达服务
│   │   ├── news_radar_skills.py   # 新闻雷达技能
│   │   ├── news_trend_analyzer.py # 新闻趋势分析
│   │   ├── project_rag_service.py  # 项目RAG服务
│   │   ├── project_service.py      # 项目服务
│   │   └── reranker_service.py    # 重排服务
│   ├── models/                      # 数据模型
│   │   ├── project.py              # 项目模型
│   │   ├── user.py                 # 用户模型
│   │   ├── user_news_history.py    # 用户新闻历史
│   │   └── user_radar_profile.py  # 用户雷达画像
│   ├── tools/                       # 工具集成
│   │   └── search_tools.py       # 搜索工具
│   ├── data/                        # 数据存储
│   │   ├── chroma/                # 向量数据库
│   │   ├── storage/               # 数据库文件
│   │   └── uploads/               # 上传文件
│   ├── logs/                        # 日志文件
│   ├── dev_tools/                   # 开发工具
│   │   ├── check_*.py             # 数据检查脚本
│   │   ├── test_*.py              # 测试脚本
│   │   ├── debug_*.py             # 调试脚本
│   │   └── *_viewer.py            # 查看器工具
│   ├── scripts/                     # 脚本工具
│   │   ├── eval_data/              # 评估数据
│   │   ├── backfill_chroma_from_postgres.py
│   │   ├── evaluate_project_rag.py
│   │   ├── evaluate_project_rag_ragas.py
│   │   ├── evaluate_rag_agents.py
│   │   └── migrate_sqlite_to_postgres.py
│   ├── config.py                    # 配置管理
│   ├── database.py                  # 数据库连接
│   ├── main.py                     # FastAPI应用入口
│   ├── requirements.txt             # Python依赖
│   ├── .env                        # 环境配置
│   ├── .env.example                 # 环境配置示例
│   ├── start.sh                    # 启动脚本
│   └── stop.sh                     # 停止脚本
│
├── 🗄️ infra/                         # 基础设施
│   └── redis/
│       └── redis.conf              # Redis配置文件
│
├── .venv/                          # Python虚拟环境
├── .gitignore                       # Git忽略配置
└── README.md                        # 项目说明文档
```

---

## 🚀 快速开始

### 前提条件

- **Python**: 3.10+
- **Node.js**: 18.0+
- **Redis**: 7.0+ (本地开发)
- **PostgreSQL**: 15+ (可选，用于持久化存储)
- **LLM API Key**: OpenAI/Anthropic/DeepSeek/通义千问

### 1. 环境配置

#### 克隆项目
```bash
git clone https://github.com/yourusername/techeyes_langchain.git
cd techeyes_langchain
```

#### 后端配置

```bash
# 1. 创建Python虚拟环境
python3.10 -m venv .venv
source .venv/bin/activate

# 2. 安装Python依赖
cd backend
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

**必需的环境变量:**
```bash
# LLM配置 (必需)
LLM_PROVIDER=openai              # 或 deepseek, anthropic, qwen
LLM_API_KEY=sk-your-api-key
LLM_MODEL_ID=gpt-4-turbo
LLM_BASE_URL=https://api.openai.com/v1

# 搜索工具 (至少配置一个)
TAVILY_API_KEY=tvly-your-key     # 推荐
SERPAPI_API_KEY=your-serpapi-key

# Redis配置
REDIS_URL=redis://localhost:6379

# 应用配置
DEBUG=true
API_PORT=8000
ENVIRONMENT=development
```

#### 前端配置

```bash
# 1. 安装Node.js依赖
cd frontend
npm install

# 2. 配置环境变量 (如果需要)
cp .env.example .env.local
```

### 2. 启动Redis服务

#### macOS (Homebrew)
```bash
# 安装Redis
brew install redis

# 启动Redis
brew services start redis

# 验证Redis运行
redis-cli ping
# 应该返回 PONG
```

#### Linux (Systemd)
```bash
# 启动Redis服务
sudo systemctl start redis

# 设置开机自启
sudo systemctl enable redis
```

#### Docker方式
```bash
# 使用Docker启动Redis
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### 3. 启动后端服务

#### 方式一：使用启动脚本
```bash
# 使用项目提供的启动脚本
./start.sh
```

#### 方式二：手动启动
```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动后端服务
cd backend
python main.py
```

**启动成功标志:**
```
🚀 TechEyes Backend 正在启动...
================================================================================
📊 测试数据库连接...
✅ 数据库连接成功
✅ 数据库初始化成功

📝 配置信息:
 - 环境: development
 - 调试模式: True
 - LLM 提供商: qwen
 - LLM 模型: qwen1.5-110b-chat
 - API 地址: http://0.0.0.0:8000

🔧 已配置的工具:
 ✅ TAVILY - 高级搜索
 ✅ MineRU - 文档解析

================================================================================
✨ TechEyes Backend 已启动！
📅 定时任务已启动：每1小时刷新一次新闻热榜
```

### 4. 启动前端服务

```bash
# 启动前端开发服务器
cd frontend
npm run dev
```

**前端访问地址:**
- 开发服务器: http://localhost:5173
- API代理: http://localhost:5173/api

### 5. 访问应用

打开浏览器访问: http://localhost:5173

**功能测试建议:**
1. 在启动页面测试搜索功能
2. 输入分析查询，观察Agent协作过程
3. 查看结果页面的数据可视化
4. 检查Redis缓存是否生效
5. 查看后端日志确认服务正常运行

---

## ⚙️ 配置指南

### LLM配置详解

#### OpenAI配置
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-xxxxx
LLM_MODEL_ID=gpt-4-turbo
LLM_BASE_URL=https://api.openai.com/v1
```

#### DeepSeek配置 (推荐)
```bash
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxxxx
LLM_MODEL_ID=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
```

#### 通义千问配置
```bash
LLM_PROVIDER=qwen
LLM_API_KEY=sk-xxxxx
LLM_MODEL_ID=qwen1.5-110b-chat
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 搜索工具配置

#### Tavily配置 (推荐)
```bash
TAVILY_API_KEY=tvly-xxxxx
TAVILY_INCLUDE_RAW_CONTENT=true
```

#### SERPAPI配置
```bash
SERPAPI_API_KEY=your-serpapi-key
```

### 缓存配置

#### Redis配置
```bash
REDIS_URL=redis://localhost:6379
CACHE_TTL=86400              # 缓存24小时
ENABLE_SEMANTIC_CACHE=true   # 启用语义缓存
SEMANTIC_CACHE_THRESHOLD=0.85  # 相似度阈值
```

#### 语义缓存策略
```bash
# 当相似度 >= 0.85 时，直接返回缓存结果
# 显著降低API调用成本和响应时间
# 适用于重复或相似的查询
```

### Agent配置

```bash
# Agent执行配置
MAX_AGENT_STEPS=10              # 最大执行步数
AGENT_TIMEOUT=120               # 单个Agent超时时间(秒)
REFLECTION_ENABLED=true        # 启用自纠错机制

# 记忆配置
MEMORY_WORKING_WINDOW=12         # 记忆工作窗口大小
MEMORY_RETRIEVE_TOPK=5         # 记忆检索数量
MEMORY_ENABLE_LLM_COMPRESSION=true  # 启用LLM记忆压缩
```

### 数据库配置

#### PostgreSQL配置
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/techeyes
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0
```

#### Neo4j配置
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=techeyes
```

### 应用配置

```bash
# 调试配置
DEBUG=true
LOG_LEVEL=INFO

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000

# CORS配置
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# 存储配置
STORAGE_PATH=./data/storage
CHROMA_PATH=./data/chroma
LOG_PATH=./logs
UPLOAD_DIR=./data/uploads
```

### 新闻雷达配置

```bash
# 新闻雷达技能配置
NEWS_RADAR_ENABLED=true
NEWS_REFRESH_INTERVAL=3600      # 新闻刷新间隔(秒)
HOT_NEWS_LIMIT=20              # 热榜新闻数量
```

---

## 📡 API文档

### 核心API端点

#### 1. 分析相关API

##### 创建分析会话
```http
POST /api/analyze
Content-Type: application/json

{
  "query": "分析低空经济(eVTOL)的发展，对比大疆和亿航",
  "user_id": "optional_user_id",
  "options": {
    "enable_cache": true,
    "enable_reflection": true
  }
}
```

**响应:**
```json
{
  "session_id": "uuid-string",
  "status": "created",
  "message": "分析会话已创建"
}
```

##### 获取分析结果
```http
GET /api/analyze/{session_id}/result
```

**响应:**
```json
{
  "session_id": "uuid-string",
  "status": "completed",
  "result": {
    "summary": "执行摘要",
    "timeline": [...],
    "comparison": {...},
    "future_outlook": {...},
    "metadata": {
      "total_time": 45.2,
      "agent_count": 5,
      "cache_hits": 3
    }
  }
}
```

##### 订阅分析进度
```http
GET /api/analyze/{session_id}/stream
```

**SSE流式响应:**
```json
{
  "type": "step",
  "data": {
    "step": 1,
    "agent": "orchestrator",
    "status": "completed",
    "message": "任务分解完成"
  }
}
```

#### 2. 项目管理API

##### 创建项目
```http
POST /api/projects
Content-Type: application/json

{
  "name": "eVTOL竞争分析",
  "description": "分析eVTOL与大疆、亿航的竞争关系",
  "user_id": "user_123"
}
```

##### 获取项目列表
```http
GET /api/projects
```

##### 获取项目详情
```http
GET /api/projects/{project_id}
```

#### 3. 新闻雷达API

##### 获取技能列表
```http
GET /api/radar/skills
```

**响应:**
```json
{
  "skills": [
    {
      "id": "refresh_hot_news",
      "name": "刷新热榜新闻",
      "description": "定期刷新新闻热榜"
    },
    {
      "id": "get_hot_news",
      "name": "获取热榜新闻",
      "description": "获取当前热榜新闻列表"
    }
  ]
}
```

##### 执行单个技能
```http
POST /api/radar/skills/execute
Content-Type: application/json

{
  "skill_id": "get_hot_news",
  "params": {
    "limit": 20
  }
}
```

##### 执行完整工作流
```http
POST /api/radar/skills/workflow
Content-Type: application/json

{
  "workflow": [
    {"skill_id": "refresh_hot_news"},
    {"skill_id": "get_hot_news", "params": {"limit": 20}},
    {"skill_id": "analyze_entities"}
  ]
}
```

#### 4. 健康检查API

##### 健康检查
```http
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "llm": {
    "provider": "qwen",
    "model": "qwen1.5-110b-chat"
  },
  "tools": {
    "tavily": true,
    "serpapi": false,
    "mineru": true
  }
}
```

##### 获取应用配置
```http
GET /config
```

**响应:**
```json
{
  "environment": "development",
  "debug": true,
  "llm_provider": "qwen",
  "llm_model": "qwen1.5-110b-chat",
  "tools": {
    "serpapi": true,
    "tavily": true,
    "mineru": true
  },
  "agent_config": {
    "max_steps": 10,
    "timeout": 120,
    "reflection_enabled": true
  }
}
```

### 错误响应格式

所有API错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-03-17T10:30:00Z"
}
```

**常见错误码:**
- `INVALID_API_KEY`: API密钥无效或过期
- `RATE_LIMIT_EXCEEDED`: 超过速率限制
- `AGENT_TIMEOUT`: Agent执行超时
- `CACHE_ERROR`: 缓存服务错误
- `DATABASE_ERROR`: 数据库连接错误
- `LLM_ERROR`: LLM服务错误

---

## 🛠️ 开发指南

### 后端开发

#### 项目结构说明
```
backend/
├── agents/              # Agent系统核心
├── api/                 # FastAPI路由
├── services/            # 业务逻辑层
├── models/              # 数据模型
├── data/                # 数据存储
├── tools/               # 工具集成
├── dev_tools/           # 开发工具
├── scripts/             # 脚本工具
└── logs/                # 日志文件
```

#### 添加新Agent

1. **创建Agent类**
```python
# 在backend/agents/目录下创建新Agent
from agents.base import BaseAgent

class YourCustomAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)
        self.agent_name = "your_agent"
        self.description = "Agent描述"
    
    async def execute(self, task):
        # 实现Agent执行逻辑
        result = await self._process_task(task)
        return result
```

2. **在Orchestrator中注册**
```python
# 在agents/orchestrator_agent.py中注册新Agent
self.agents = {
    "researcher": ResearcherAgent,
    "analyzer": AnalyzerAgent,
    "critic": CriticAgent,
    "synthesizer": SynthesizerAgent,
    "your_agent": YourCustomAgent  # 添加新Agent
}
```

#### 添加新工具

1. **创建工具函数**
```python
# 在backend/tools/目录下创建新工具
async def your_custom_tool(query: str) -> dict:
    """
    自定义工具函数
    """
    # 实现工具逻辑
    result = {
        "data": "工具返回数据",
        "source": "your_tool",
        "timestamp": datetime.now().isoformat()
    }
    return result
```

2. **在ResearcherAgent中集成**
```python
# 在agents/researcher_agent.py中调用新工具
async def _collect_information(self, tasks):
    for task in tasks:
        if task.tool == "your_tool":
            result = await your_custom_tool(task.query)
            # 处理结果
```

#### 添加新API端点

1. **创建路由函数**
```python
# 在backend/api/目录下创建新路由
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/your-endpoint")
async def your_endpoint(request: Request):
    try:
        # 实现API逻辑
        result = await your_service.process_request(request)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

2. **注册路由**
```python
# 在backend/main.py中注册新路由
from api.your_router import router as your_router

app.include_router(your_router, prefix="/api")
```

### 前端开发

#### 项目结构说明
```
frontend/src/
├── pages/               # 页面组件
├── components/          # 可复用组件
├── services/            # API服务
├── stores/              # 状态管理
├── types/               # TypeScript类型
├── App.vue              # 根组件
└── main.ts              # 应用入口
```

#### 添加新页面

1. **创建页面组件**
```typescript
// 在frontend/src/pages/目录下创建新页面
import React from 'react';
import { useAnalysisStore } from '@/services/api';

const YourNewPage: React.FC = () => {
  const { analyze } = useAnalysisStore();
  
  const handleAnalyze = async () => {
    await analyze({
      query: "你的分析查询",
      options: {}
    });
  };
  
  return (
    <div className="your-page">
      <h1>新页面标题</h1>
      <button onClick={handleAnalyze}>
        开始分析
      </button>
    </div>
  );
};

export default YourNewPage;
```

2. **添加路由**
```typescript
// 在frontend/src/router/index.ts中添加新路由
import YourNewPage from '@/pages/YourNewPage';

const router = createBrowserRouter([
  {
    path: '/your-page',
    element: <YourNewPage />
  },
  // ... 其他路由
]);
```

#### 添加新组件

1. **创建组件文件**
```typescript
// 在frontend/src/components/目录下创建新组件
import React from 'react';

interface YourComponentProps {
  title: string;
  data: any[];
}

const YourComponent: React.FC<YourComponentProps> = ({ title, data }) => {
  return (
    <div className="your-component">
      <h2>{title}</h2>
      <ul>
        {data.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
};

export default YourComponent;
```

#### 状态管理

```typescript
// 使用Pinia创建新的store
import { defineStore } from 'pinia';

export const useYourStore = defineStore('your', () => ({
  state: {
    data: [],
    loading: false,
    error: null
  },
  actions: {
    fetchData: async () => {
      this.loading = true;
      try {
        const response = await api.fetchData();
        this.data = response.data;
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    }
  }
}));
```

### 测试指南

#### 后端测试
```bash
# 运行单元测试
cd backend
pytest tests/

# 运行集成测试
pytest tests/integration/

# 运行特定测试
pytest tests/test_agents.py -v
```

#### 前端测试
```bash
# 运行单元测试
cd frontend
npm test

# 运行E2E测试
npm run test:e2e

# 运行linting
npm run lint
```

### 调试技巧

#### 后端调试
```python
# 在代码中添加调试日志
from loguru import logger

logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")

# 使用Python调试器
import pdb; pdb.set_trace()

# 在需要调试的地方添加断点
pdb.set_trace()
```

#### 前端调试
```typescript
// 使用console.log调试
console.log('调试信息', data);

// 使用React DevTools
// 安装React Developer Tools浏览器扩展

// 使用Vue DevTools (如果使用Vue)
// 安装Vue.js devtools浏览器扩展
```

---

## 🔧 故障排除

### 常见问题

#### 1. Redis连接失败
**问题**: `redis.exceptions.ConnectionError`

**解决方案**:
```bash
# 检查Redis是否运行
redis-cli ping

# 启动Redis服务
brew services start redis  # macOS
sudo systemctl start redis  # Linux

# 检查Redis配置
redis-cli -h
netstat -an | grep 6379
```

#### 2. LLM API调用失败
**问题**: `openai.APIConnectionError` 或认证失败

**解决方案**:
```bash
# 检查API密钥
echo $LLM_API_KEY | head -c 10

# 测试API连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"

# 检查网络连接
ping api.openai.com
```

#### 3. 数据库连接失败
**问题**: `sqlalchemy.exc.DBAPIError`

**解决方案**:
```bash
# 检查PostgreSQL服务
brew services list | grep postgresql

# 测试数据库连接
psql -U postgres -h localhost -p 5432

# 检查数据库配置
cat backend/.env | grep DATABASE_URL
```

#### 4. 前端构建失败
**问题**: `Module not found` 或构建错误

**解决方案**:
```bash
# 清理node_modules和缓存
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force

# 重新安装依赖
npm install

# 清理构建缓存
npm run build
```

#### 5. Agent执行超时
**问题**: Agent执行时间超过配置的超时时间

**解决方案**:
```bash
# 在.env中增加超时时间
AGENT_TIMEOUT=300  # 增加到5分钟

# 或者禁用超时
AGENT_TIMEOUT=0  # 0表示不限制
```

#### 6. 缓存未生效
**问题**: 语义缓存没有命中，每次都调用LLM

**解决方案**:
```bash
# 检查缓存配置
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.85

# 检查Redis连接
redis-cli ping

# 查看缓存日志
tail -f backend/logs/app.log | grep cache
```

### 日志查看

#### 后端日志
```bash
# 查看实时日志
tail -f backend/logs/app.log

# 查看错误日志
grep ERROR backend/logs/app.log

# 查看特定Agent的日志
grep "OrchestratorAgent" backend/logs/app.log
```

#### 前端日志
```bash
# 浏览器开发者工具Console
# 查看网络请求
# 查看错误信息
# 查看性能指标
```

### 性能优化

#### 后端优化
```python
# 启用异步处理
import asyncio

# 使用连接池
from sqlalchemy.pool import QueuePool

# 实现缓存策略
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_function():
    # 缓存函数结果
    pass
```

#### 前端优化
```typescript
// 使用React.memo
const MemoizedComponent = React.memo(({ data }) => {
  return <div>{data}</div>;
});

// 使用useMemo
const expensiveCalculation = useMemo(() => {
  return heavyCalculation(data);
}, [data]);

// 使用useCallback
const handleClick = useCallback(() => {
  // 处理点击事件
}, [dependency]);
```

---
