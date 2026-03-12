# TechEyes - Multi-Agent AI 科技分析平台

## 🎯 项目简介

TechEyes 是一个基于 **Vue 3 + FastAPI + hello_agents** 的 Multi-Agent AI 系统，专注于科技行业深度分析。采用前后端分离架构，提供实时流式分析、语义缓存、多维度对比等专业功能。

### ✨ 核心特性

- 🤖 **Multi-Agent 协作**: 5 个专业 Agent（Orchestrator、Researcher、Analyzer、Critic、Synthesizer）协同工作
- ⚡ **语义缓存加速**: Redis + 向量相似度，相似查询秒级返回
- 📊 **实时流式输出**: Server-Sent Events (SSE) 实时展示分析进度
- 🎨 **现代化 UI**: Vue 3 + Tailwind CSS，流畅的用户体验
- 🔌 **MCP 协议支持**: 可扩展集成外部工具和数据源
- 🗄️ **PostgreSQL 持久化**: 完整的分析历史记录

---

## 🏗️ 技术架构

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 渐进式框架 |
| TypeScript | 5.3+ | 类型安全 |
| Vite | 5.0+ | 构建工具 |
| Pinia | 2.1+ | 状态管理 |
| Vue Router | 4.2+ | 路由管理 |
| Tailwind CSS | 3.4+ | 原子化样式 |
| Axios | 1.6+ | HTTP 客户端 |

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.104+ | 异步 Web 框架 |
| hello_agents | 0.2.8 | Multi-Agent 框架 |
| PostgreSQL | 16+ | 关系数据库 |
| Redis | 7+ | 缓存系统 |
| SQLAlchemy | 2.0+ | ORM |
| Pydantic | 2.5+ | 数据验证 |

### 外部服务

- **Qwen3.5-Max**: 通义千问大模型（主 LLM）
- **TAVILY API**: 高级网络搜索
- **SERPAPI**: 通用搜索引擎
- **MineRU**: 文档解析服务

---

## 📦 快速开始

### 前置要求

- Node.js 18+
- Python 3.10+
- PostgreSQL 16+
- Redis 7+

### 1️⃣ 环境配置

项目根目录已包含 `.env` 文件，包含所有必要配置：

```bash
# 数据库
DATABASE_URL=postgresql://postgres:1234@localhost:5432/techeyes

# LLM (已配置 Qwen3.5)
LLM_PROVIDER=qwen
LLM_MODEL_ID=qwen3.5-122b-a10b
LLM_API_KEY=sk-c4d40f85a9e24d76a5d0a44255150594

# 搜索工具
TAVILY_API_KEY=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
SERPAPI_API_KEY=a703e9cc2c2935e1e527763356ce53c49e2b8584e97bd2a910a5bb5ddd4bb6a2

# 文档处理
MINERU_API_KEY=eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ...
```

### 2️⃣ 启动数据库

**选项 A - Docker (推荐)**:
```bash
cd /Users/cairongqing/Documents/techeyes
docker-compose up postgres redis -d
```

**选项 B - 本地 PostgreSQL**:
确保 PostgreSQL 运行并创建数据库：
```bash
psql -U postgres
CREATE DATABASE techeyes;
```

### 3️⃣ 启动后端

```bash
cd /Users/cairongqing/Documents/techeyes/backend
pip install -r requirements.txt
python main.py
```

启动成功会看到：
```
🚀 TechEyes Backend 正在启动...
✅ 数据库连接成功
✅ 数据库初始化成功
✅ SERPAPI - 网络搜索
✅ TAVILY - 高级搜索
✅ MineRU - 文档解析
✨ TechEyes Backend 已启动！
```

### 4️⃣ 启动前端

```bash
cd /Users/cairongqing/Documents/techeyes/frontend
npm install
npm run dev
```

访问: **http://localhost:5173**

---

## 📂 项目结构

```
techeyes/
├── backend/                 # FastAPI 后端
│   ├── agents/             # Agent 实现
│   │   ├── base.py              # 基类
│   │   ├── orchestrator_agent.py
│   │   ├── researcher_agent.py
│   │   ├── analyzer_agent.py
│   │   ├── critic_agent.py
│   │   └── synthesizer_agent.py
│   ├── api/
│   │   └── routes.py            # API 路由
│   ├── services/
│   │   ├── analysis_service.py  # 分析服务
│   │   └── cache_service.py     # 缓存服务
│   ├── tools/
│   │   └── search_tools.py      # 搜索工具
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── main.py                 # 应用入口
│   └── requirements.txt        # Python 依赖
│
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── views/              # 页面
│   │   │   ├── LandingPage.vue      # 首页
│   │   │   ├── AnalysisPage.vue     # 分析页
│   │   │   └── ResultPage.vue       # 结果页
│   │   ├── components/         # 组件
│   │   │   ├── Header.vue
│   │   │   ├── SearchBar.vue
│   │   │   ├── TaskFlow.vue
│   │   │   ├── TimelineView.vue
│   │   │   └── ComparisonTable.vue
│   │   ├── stores/             # Pinia 状态
│   │   │   └── analysis.ts
│   │   ├── services/           # API 服务
│   │   │   └── api.ts
│   │   ├── types/              # TypeScript 类型
│   │   │   └── index.ts
│   │   ├── router/             # 路由
│   │   │   └── index.ts
│   │   ├── App.vue             # 根组件
│   │   └── main.ts             # 入口
│   ├── package.json            # 依赖
│   ├── vite.config.ts          # Vite 配置
│   └── tailwind.config.js      # Tailwind 配置
│
├── .env                     # 环境变量
├── docker-compose.yml       # Docker 编排
└── README.md               # 项目文档
```

---

## 🔄 Multi-Agent 工作流程

```
用户查询
    ↓
┌─────────────────────┐
│  Orchestrator Agent │  任务分解、计划制定
└─────────────────────┘
    ↓
┌──────────────────────────────────┐
│  Researcher Agents (并行)        │  信息搜集
│  - 公司历史                       │
│  - 产品信息                       │
│  - 市场数据                       │
└──────────────────────────────────┘
    ↓
┌─────────────────────┐
│  Analyzer Agent     │  多维度分析、对比
└─────────────────────┘
    ↓
┌─────────────────────┐
│  Critic Agent       │  质量检查、事实核验
└─────────────────────┘
    ↓ (反馈循环)
┌─────────────────────┐
│  Synthesizer Agent  │  结果整合、报告生成
└─────────────────────┘
    ↓
结构化分析报告
```

---

## 🌐 API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 提交分析请求 |
| GET | `/api/analysis/{session_id}/progress` | 获取分析进度 |
| GET | `/api/analysis/{session_id}/stream` | 订阅实时更新 (SSE) |
| GET | `/api/analysis/{session_id}/result` | 获取分析结果 |
| POST | `/api/analysis/{session_id}/cancel` | 取消分析 |
| POST | `/api/cache/check` | 检查语义缓存 |
| GET | `/health` | 健康检查 |
| GET | `/config` | 获取配置信息 |

---

## 🎨 功能演示

### 1. 首页搜索
![Landing](https://via.placeholder.com/800x400?text=Landing+Page)
- Google 风格搜索框
- 搜索历史快速访问
- 功能特性展示

### 2. 实时分析
![Analysis](https://via.placeholder.com/800x400?text=Analysis+Page)
- 进度条实时更新
- 任务流程可视化
- 实时日志输出

### 3. 分析结果
![Result](https://via.placeholder.com/800x400?text=Result+Page)
- 时间线视图
- 多维度对比表格
- 未来场景预测

---

## 🛠️ 开发指南

### 前端开发

```bash
cd frontend

# 开发模式
npm run dev

# 类型检查
npm run type-check

# 生产构建
npm run build
npm run preview
```

### 后端开发

```bash
cd backend

# 启动服务
python main.py

# 运行测试
pytest

# 代码格式化
black .
```

### Docker 部署

```bash
# 启动全部服务
docker-compose up

# 仅启动后端 + 数据库
docker-compose up backend postgres redis

# 查看日志
docker-compose logs -f backend
```

---

## 📊 配置说明

### LLM 配置

支持多个 LLM 提供商（通过 hello_agents 自动检测）：

```env
# Qwen (通义千问)
LLM_PROVIDER=qwen
LLM_MODEL_ID=qwen3.5-122b-a10b
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL_ID=gpt-4-turbo

# DeepSeek
LLM_PROVIDER=deepseek
LLM_MODEL_ID=deepseek-chat
```

### 数据库配置

```env
DATABASE_URL=postgresql://用户名:密码@主机:端口/数据库名
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0
```

### Agent 配置

```env
MAX_AGENT_STEPS=10          # 最大推理步数
AGENT_TIMEOUT=120           # 超时时间(秒)
REFLECTION_ENABLED=true     # 启用自我反思
```

---

## 🐛 常见问题

### Q: 数据库连接失败？
**A**: 检查 PostgreSQL 是否运行，确认用户名密码正确。

### Q: 前端请求 404？
**A**: 确保后端运行在 8000 端口，检查 Vite 代理配置。

### Q: Agent 响应慢？
**A**: 检查 LLM API 是否正常，考虑调整 `LLM_TIMEOUT` 参数。

### Q: 缓存不生效？
**A**: 确认 Redis 已启动，检查 `REDIS_URL` 配置。

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Happy Coding! 🚀**
