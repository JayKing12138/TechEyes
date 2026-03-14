FROM continuumio/miniconda3:latest

WORKDIR /app

# 复制 conda 环境配置文件（如果有）
COPY environment.yml* ./

# 创建 conda 环境
RUN conda create -n techeyes python=3.10 -y && \
    conda clean -afy

# 激活环境并安装依赖
COPY requirements.txt .
RUN /bin/bash -c "source activate techeyes && \
    pip install --no-cache-dir -r requirements.txt"

# 复制代码
COPY . .

# 创建必要目录
RUN mkdir -p logs data/storage data/chroma

EXPOSE 8000

# 使用 conda 环境运行应用
CMD ["/bin/bash", "-c", "source activate techeyes && python main.py"]

### 步骤 3：启动前端

```bash
cd frontend
npm install
npm run dev

# 输出示例：
# VITE v5.0.8  ready in 234 ms
# ➜  Local:   http://localhost:5173/
```

### 步骤 4：开始使用

1. 打开 http://localhost:5173
2. 在搜索框输入：`分析低空经济eVTOL的发展，对比大疆和亿航`
3. 观看 AI 实时分析过程
4. 查看最终报告

---

## 🐳 使用 Docker 一键启动

```bash
docker-compose up

# 访问：
# 前端: http://localhost:5173
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

---

## 📁 项目结构一览

```
techeyes/
├── frontend/                    # React 前端（高大上 UI）
│   ├── src/
│   │   ├── pages/              # 3 个主页面
│   │   │   ├── LandingPage.tsx     # 首页（搜索框）
│   │   │   ├── AnalysisPage.tsx    # 分析过程页
│   │   │   └── ResultPage.tsx      # 结果展示页
│   │   ├── components/         # 可视化组件
│   │   │   ├── SearchBar.tsx       # 搜索框
│   │   │   ├── TaskFlow.tsx        # 任务流程可视化
│   │   │   ├── TimelineView.tsx    # 时间轴
│   │   │   ├── ComparisonTable.tsx # 对比表格
│   │   │   └── Header.tsx          # 导航栏
│   │   ├── services/           # API 和状态管理
│   │   │   ├── api.ts             # API 调用
│   │   │   └── store.ts           # 全局状态
│   │   ├── types/              # TypeScript 类型
│   │   └── App.tsx, main.tsx, index.css
│   └── package.json
│
├── backend/                    # FastAPI 后端
│   ├── agents/                # 5 个 Agent
│   │   ├── base.py               # Agent 基类
│   │   ├── orchestrator_agent.py  # 协调者（分解任务）
│   │   ├── researcher_agent.py    # 研究员（搜集信息）
│   │   ├── analyzer_agent.py      # 分析师（数据分析）
│   │   ├── critic_agent.py        # 批评家（质量审查）
│   │   └── synthesizer_agent.py   # 综合者（融合结果）
│   ├── services/
│   │   ├── analysis_service.py    # 核心分析流程
│   │   └── cache_service.py       # 语义缓存
│   ├── api/
│   │   └── routes.py           # FastAPI 路由
│   ├── tools/                  # 自定义工具（扩展点）
│   ├── main.py                 # FastAPI 应用
│   ├── config.py               # 配置文件
│   └── requirements.txt
│
├── README.md                   # 完整文档
├── .env.example               # 环境变量示例
├── docker-compose.yml         # Docker 配置
└── plan.md                    # 原始需求文档
```

---

## 🔧 核心 API 端点

### 提交分析请求
```
POST /api/analyze
Content-Type: application/json

{
  "query": "分析低空经济EVTOL的发展",
  "focus_companies": ["大疆", "亿航"],
  "analysis_depth": "normal",
  "include_future_prediction": true
}

Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "cached": false
}
```

### 获取实时进度（EventSource）
```
GET /api/analysis/{session_id}/stream

实时接收：
data: {"type": "progress", "progress": 30, "status": "analyzing"}
data: {"type": "task_update", "task": {...}}
data: {"type": "completed"}
```

### 获取完整结果
```
GET /api/analysis/{session_id}/result

Response:
{
  "summary": "...",
  "timeline": [...],
  "comparisons": [...],
  "futureOutlook": {...},
  "sources": [...]
}
```

---

## 💡 前端界面设计亮点

### 🎨 色彩方案
- **背景色**：深蓝 (#0f172a)
- **强调色**：霓虹青 (#00d9ff) / 紫 (#b700f8) / 蓝 (#00f0ff)
- **文字**：浅灰（#e2e8f0）
- **玻璃态**：`backdrop-blur-xl` + `bg-white/5 border-white/10`

### ✨ 动画库
- Framer Motion：平滑过渡、交互动画
- 原生 CSS：加载旋转、闪烁效果
- 自定义 Tailwind：渐变文本、发光效果

### 📱 响应式设计
- 移动端优先
- md 断点分栏布局
- lg 三栏专业布局

---

## 🤖 Agent 专业领域分配

| Agent | 角色 | 职责 | 工具 |
|-------|------|------|------|
| **Orchestrator** | 协调者 | 分解复杂任务为子任务 | 无 |
| **Researcher** | 研究员 | 搜集历史信息、竞品数据 | SearchTool（MCP） |
| **Analyzer** | 分析师 | 多维度数据对比、评分 | 无 |
| **Critic** | 批评家 | 事实核实、逻辑检查 | 可选：Reflection 纠错 |
| **Synthesizer** | 综合者 | 融合多源数据、生成报告 | 无 |

---

## 📊 数据流示例

```
用户：分析低空经济eVTOL

      前端
        ↓
    POST /api/analyze
        ↓
   获得 session_id
        ↓
   订阅 EventSource
        ↓
  ┌─────────────────────────┐
  │  OrchestratorAgent      │  分解：
  │  分解任务               │  - 历史研究任务
  └─────────────────────────┘  - 现状分析任务
        ↓                       - 趋势预测任务
  ┌──────────┬──────────┬──────────┐
  │Researcher│Analyzer  │Analyzer  │  并行执行
  └──────────┴──────────┴──────────┘
        ↓        ↓         ↓
   历史数据   对比数据   趋势数据
        ↓        ↓         ↓
  ┌─────────────────────────┐
  │  CriticAgent            │  检查错误
  │  质量审查               │
  └─────────────────────────┘
        ↓
  ┌─────────────────────────┐
  │  SynthesizerAgent       │  融合
  │  生成最终报告           │
  └─────────────────────────┘
        ↓
   GET /api/analysis/{id}/result
        ↓
   前端展示报告
```

---

## 🎯 面试亮点

这个项目适合充分展现：

1. **架构设计能力**
   - 前后端分离
   - Multi-Agent 协调模式
   - 服务化设计（CacheService, AnalysisService）

2. **AI/LLM 工程**
   - hello_agents 框架使用
   - Prompt 工程（每个 Agent 的 system_prompt）
   - 工具集成（MCP 协议、Function Calling）

3. **web 开发**
   - React + TypeScript 类型安全
   - Tailwind + Framer Motion 动画
   - 实时 EventSource 流式响应
   - 全局状态管理（Zustand）

4. **工程实践**
   - 清晰的项目结构
   - 配置管理
   - 错误处理和日志
   - Docker 部署

---

## 🔍 下一步改进方向

### 快速赢（最能打动面试官）
- [ ] 接入真实搜索工具（从 DuckDuckGo 改成 Tavily 或 SerpAPI）
- [ ] 添加 Reflection 自纠错机制（发现错误自动重新分析）
- [ ] 向量数据库 RAG（用 ChromaDB 存储分析结果）

### 中等工作量
- [ ] 多模态支持（接收 PDF、Excel 文件分析）
- [ ] 用户认证和历史记录保存
- [ ] 数据导出（PDF、Excel、JSON）

### 高级特性
- [ ] Agent 可视化调试界面
- [ ] A2A 协议（Agent 间直接通信）
- [ ] 分布式部署（Kubernetes）
- [ ] 强化学习微调（用用户反馈训练）

---

## 🐛 常见问题

**Q: 前端无法连接后端？**
A: 检查 `vite.config.ts` 中的代理配置，确保后端运行在 8000 端口。

**Q: API 响应 401 Unauthorized？**
A: 检查 `.env` 中的 `LLM_API_KEY` 是否正确。

**Q: 搜索结果为空？**
A: SearchTool 依赖网络连接，检查是否无法访问网络或需要 VPN。

**Q: 如何改进分析质量？**
A: 优化各个 Agent 的 system_prompt，或接入更强的 LLM（如 GPT-4o）。

---

## 📚 参考资源

- [hello_agents 文档](https://github.com/jjyaoao/hello-agents)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://zh-hans.react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Framer Motion](https://www.framer.com/motion/)

---

## 📞 技术支持

有问题？检查：
1. 日志文件：`backend/logs/app.log`
2. API 文档：http://localhost:8000/docs（Swagger）
3. README.md 中的完整文档

---

**祝你开发顺利！🚀**

这个项目足以在求职/实习时打动面试官。重点展示：
- 完整的工程实现（不是草稿）
- 现代化的前端设计
- 清晰的代码组织
- 明确的 Agent 分工
