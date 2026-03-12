# 🎉 TechEyes 前端已迁移到 Vue 3！

## 技术栈

- ⚡ **Vue 3** - 渐进式 JavaScript 框架
- 📘 **TypeScript** - 类型安全
- 🎨 **Tailwind CSS** - 原子化 CSS
- 🚀 **Vite** - 极速构建工具
- 📦 **Pinia** - 官方状态管理
- 🧭 **Vue Router** - 官方路由

## 项目结构

```
frontend/
├── src/
│   ├── views/              # 页面组件
│   │   ├── LandingPage.vue       # 首页
│   │   ├── AnalysisPage.vue      # 分析页
│   │   └── ResultPage.vue        # 结果页
│   ├── components/         # 可复用组件
│   │   ├── Header.vue            # 导航栏
│   │   ├── SearchBar.vue         # 搜索框
│   │   ├── TaskFlow.vue          # 任务流程
│   │   ├── TimelineView.vue      # 时间线
│   │   └── ComparisonTable.vue   # 对比表格
│   ├── stores/             # Pinia 状态管理
│   │   └── analysis.ts           # 分析状态
│   ├── services/           # API 服务
│   │   └── api.ts                # 后端接口
│   ├── types/              # TypeScript 类型
│   │   └── index.ts              # 类型定义
│   ├── router/             # 路由配置
│   │   └── index.ts              # 路由表
│   ├── App.vue             # 根组件
│   └── main.ts             # 入口文件
├── package.json            # 依赖配置
├── vite.config.ts          # Vite 配置
├── tsconfig.json           # TypeScript 配置
├── tailwind.config.js      # Tailwind 配置
└── index.html              # HTML 模板
```

## 快速开始

### 1️⃣ 安装依赖

```bash
cd frontend
npm install
```

### 2️⃣ 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### 3️⃣ 生产构建

```bash
npm run build
npm run preview
```

## 主要变更（React → Vue）

| 功能 | React | Vue 3 |
|------|-------|-------|
| 状态管理 | Zustand | Pinia |
| 路由 | React Router | Vue Router |
| 组件语法 | JSX | SFC (Single File Component) |
| 动画 | Framer Motion | Vue Transition / CSS |
| API | Hooks | Composition API |

## 核心功能

### 🏠 首页 (LandingPage.vue)
- 搜索框组件
- 搜索历史
- 特性展示卡片

### 📊 分析页 (AnalysisPage.vue)
- 实时进度条
- 任务流程可视化
- SSE 流式输出

### 📈 结果页 (ResultPage.vue)
- 分析摘要
- 时间线视图
- 对比分析表格
- 未来展望

## API 集成

所有 API 请求通过 `/src/services/api.ts` 统一管理：

- `submitAnalysis()` - 提交分析
- `getAnalysisProgress()` - 获取进度
- `getAnalysisResult()` - 获取结果
- `subscribeToAnalysis()` - 订阅实时更新（SSE）

## 开发建议

1. **组件开发**: 使用 `<script setup>` 简化语法
2. **状态管理**: 通过 Pinia store 管理全局状态
3. **类型安全**: 充分利用 TypeScript 类型推导
4. **样式**: 优先使用 Tailwind 工具类

## 常用命令

```bash
npm run dev         # 开发模式
npm run build       # 生产构建
npm run preview     # 预览构建结果
npm run type-check  # TypeScript 类型检查
```

## 与后端集成

确保后端 FastAPI 服务运行在 `http://localhost:8000`，Vite 会自动代理 `/api` 请求。

---

**注意**: 所有 React 文件已迁移为 Vue 组件，功能完全保留！🎊
