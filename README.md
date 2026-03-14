"""TechEyes 完整项目 - Multi-Agent AI 科技行业分析平台

📚 项目结构
├── frontend/               # React + TypeScript + Tailwind + Framer Motion
│   ├── src/
│   │   ├── pages/         # 三个主页面：LandingPage, AnalysisPage, ResultPage
│   │   ├── components/    # 高大上的 UI 组件
│   │   ├── services/      # API 调用和状态管理
│   │   └── types/         # TypeScript 类型定义
│   └── package.json
│
├── backend/                # FastAPI + hello_agents
│   ├── agents/             # 5 个 Agent 的具体实现
│   │   ├── base.py        # Agent 基类
│   │   ├── orchestrator_agent.py  # 任务分解
│   │   ├── researcher_agent.py    # 信息收集（使用 ReAct + SearchTool）
│   │   ├── analyzer_agent.py      # 数据分析
│   │   ├── critic_agent.py        # 质量审查
│   │   └── synthesizer_agent.py   # 结果融合
│   ├── services/
│   │   ├── analysis_service.py    # 核心分析流程
│   │   └── cache_service.py       # 语义缓存（Redis）
│   ├── tools/              # 自定义工具（后续扩展）
│   ├── api/
│   │   └── routes.py       # FastAPI 路由
│   ├── main.py             # FastAPI 应用入口
│   ├── config.py           # 配置管理
│   └── requirements.txt
│
└── README.md
└── .env.example            # 环境变量示例

---

🚀 快速开始

## 前提：启动基础服务
brew services start redis      # Redis（本地 Homebrew，持久化已配置）
# PostgreSQL 另行启动（见 backend/POSTGRESQL_SETUP.md）

## 前端开发
cd frontend
npm install
npm run dev          # 在 http://localhost:5173 开启开发服务器

## 后端开发
conda activate techeyes
cd backend
pip install -r requirements.txt
python main.py       # 启动 FastAPI 服务器（http://localhost:8000）

---

🎯 核心功能详解

### 1️⃣ 启动页面 (LandingPage)
- 简洁的搜索框（类似 Google）
- 背景动画效果
- 搜索历史
- 功能介绍卡片

### 2️⃣ 分析过程页 (AnalysisPage)
- 实时进度条（0-100%）
- 左侧：任务流程可视化（TaskFlow）
  - 显示每个 Agent 的执行状态
  - 任务对应的 Agent 标签
  - 执行时间统计
- 右侧：实时输出流
  - Agent 输出内容
  - 加载动画

### 3️⃣ 结果页面 (ResultPage)  
- 执行摘要卡片
  - 处理时间
  - 参与 Agent 数
  - 缓存命中情况
- 三个标签页：
  - 📅 历史时间轴（TimelineView）
    - 时间点、事件、关键公司标签
    - 重要性标记
  - ⚖️ 对比分析（ComparisonTable）
    - 多维度对比
    - 评分条形图
    - 分析洞察
  - 🚀 未来展望
    - 发展趋势列表
    - 场景推演（概率、影响）
    - 投资建议

---

🤖 Multi-Agent 协作流程

用户输入: "分析低空经济（eVTOL）的发展，对比大疆和亿航..."

↓

[OrchestratorAgent] 任务分解
  ├─ Task1: 研究低空经济历史（分配给 Researcher）
  ├─ Task2: 分析大疆 vs 亿航（分配给 Analyzer）
  └─ Task3: 预测未来趋势（分配给 Analyzer）

↓ (并行执行)

[ResearcherAgent] 信息收集
  使用 SearchTool（MCP 协议）搜索：
  - "eVTOL 发展历史"
  - "大疆无人机事业部"
  - "亿航智能飞行器"
  ➜ 返回：时间轴事件 + 参考资料

[AnalyzerAgent] 数据分析
  分析维度：
  - 技术路线
  - 融资规模
  - 市场地位
  - 产品竞争力
  ➜ 返回：对比表格 + 评分

↓

[CriticAgent] 质量审查
  检查：
  - 事实准确度（可加入 Reflection 机制自动纠错）
  - 逻辑完整性
  - 数据一致性
  ➜ 返回：问题清单 + 改进建议

↓

[SynthesizerAgent] 结果综合
  融合多个 Agent 的结果为：
  - 执行摘要
  - 时间轴
  - 对比分析
  - 未来展望
  - 数据来源

↓

前端展示结果

---

💡 技术亮点

### 语义缓存（Semantic Cache）
```
如果用户问："eVTOL 市场分析"
再问："低空经济分析"（语义相似）
→ 直接返回缓存结果，节省 API 成本和时间
```

### 自纠错机制（Self-Correction / Reflection）
```
如果 CriticAgent 发现：
  - "某公司已量产" 的信息来自营销号
→ ReflectionAgent 重新验证官方公告
→ 更新结果
```

### Agent 工具集成（MCP Protocol）
```
ResearcherAgent 可以：
- 调用 SearchTool 搜索网络
- 连接数据库查询历史数据
- 调用其他公开 API（需要 MCP 包装）
```

### 流式响应
```
前端实时看到：
  ⚙️ 第1步：任务分解... [完成] ✅
  ⚙️ 第2步：信息搜集... [进行中] ⚙️
  ⚙️ 第3步：数据分析... [待开始] ⏳
```

---

🔧 环境变量配置 (.env)

```bash
# LLM 配置
LLM_PROVIDER=deepseek              # openai / deepseek / qwen / etc.
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxx                 # 你的 API 密钥
LLM_BASE_URL=https://api.deepseek.com

# Redis（缓存）
REDIS_URL=redis://localhost:6379

# 搜索工具
SEARCH_ENGINE=duckduckgo

# 其他
DEBUG=true
API_PORT=8000
```

---

📊 数据流向

用户查询
  ↓
前端发送 POST /api/analyze
  ↓
后端创建 session_id
  ↓
OrchestratorAgent 分解任务
  ↓
三个 Agent 并行执行
  ↓
CriticAgent 审查
  ↓
SynthesizerAgent 融合
  ↓
前端订阅 EventSource /api/analysis/{id}/stream
  ↓
实时显示进度和输出
  ↓
GET /api/analysis/{id}/result 取完整结果
  ↓
ResultPage 展示

---

🎨 设计特色

✨ 深色科技风格
  - 深蓝色背景 (#0f172a)
  - 霓虹色强调（青色、紫色、蓝色）
  - 玻璃态毛玻璃效果 (backdrop-blur)

✨ 动画和交互
  - Framer Motion 的平滑过渡
  - 流式文字输出动画
  - 进度条动画
  - 悬停效果

✨ 信息层级清晰
  - 大号标题 > 小号副标题
  - 颜色突出重要信息
  - 合理的白色空间

---

🛠️ 后续扩展方向

✅ 当前实现：
  - Multi-Agent 协作框架
  - 基础 5 个 Agent
  - 简单的语义缓存
  - 流式响应

📈 可以加入的功能：
  1. Reflection 机制自动纠错（发现错误后重新分析）
  2. Advanced RAG（知识库 + 向量检索）
  3. A2A 协议（Agent 间直接通信）
  4. 可视化调试界面
  5. 多模态支持（图片、PDF 解析）
  6. 分布式部署
  7. 用户认证和个人化历史记录

  ---

  🧩 科技新闻雷达 Skills（新增）

  后端新增了新闻雷达技能层，可将第三模块能力按技能方式复用和编排。

  - 技能清单：`GET /api/radar/skills`
  - 执行单技能：`POST /api/radar/skills/execute`
  - 执行完整流程：`POST /api/radar/skills/workflow`

  已实现技能：

  1. `refresh_hot_news`
  2. `get_hot_news`
  3. `get_news_detail`
  4. `analyze_entities`
  5. `followup`
  6. `generate_report`
  7. `run_full_workflow`

  详细调用示例见：`backend/NEWS_RADAR_SKILLS.md`

---

📝 开发建议

1. 先跑起来看效果
   - 前端：npm run dev
   - 后端：python main.py
   - 搜索框输入查询，看分析过程

2. 调整 Agent 的 Prompt
   - 每个 Agent 的 system_prompt 都可以优化
   - 根据实际输出结果微调

3. 集成真实的搜索工具
   - 目前 SearchTool 用的是 DuckDuckGo
   - 可以替换为 Tavily (专业 AI 搜索)

4. 改进缓存策略
   - 当前是简单的 MD5 匹配
   - 可以用向量相似度做语义缓存

5. 性能优化
   - 用 Redis 缓存中间结果
   - 并行执行多个 Agent
   - 流式响应给前端

---



"""
