# TechEyes Backend - 快速启动指南

## 🚀 启动后端

```bash
cd backend
./start.sh
```

或者手动启动：
```bash
cd backend
conda activate techeyes
python main.py
```

## 🛑 停止后端

```bash
cd backend
./stop.sh
```

或者手动停止：
```bash
lsof -ti:8000 | xargs kill -9
```

## ℹ️ 注意事项

- **Redis**: 非必需，未启动会自动使用内存缓存
- **PostgreSQL**: 非必需，当前使用内存存储
- **LLM API**: 必需，需在 `.env` 中配置 `LLM_API_KEY`
- **搜索工具**: 可选，配置 `TAVILY_API_KEY` 或 `SERPAPI_API_KEY` 获得更好的搜索结果

## 📋 环境配置

复制 `.env.example` 为 `.env` 并填入你的API密钥：
```bash
cp .env.example .env
# 然后编辑 .env 文件
```

最小配置示例：
```bash
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key_here
LLM_MODEL_ID=gpt-3.5-turbo
```

## 🔍 检查状态

```bash
curl http://localhost:8000/health
```

## 🧪 RAG 自动化评测（项目知识工作台）

支持三类指标：

- 检索阶段：`Hit@K`、`Recall@K`、`MRR@K`、`NDCG@K`
- 生成阶段：`accuracy`、`completeness`、`faithfulness`
- 端到端：`task_success_rate`、`latency(avg/p50/p95)`、`cache_hit_rate`

运行示例：

```bash
cd backend
python scripts/evaluate_project_rag.py \
  --dataset scripts/rag_eval_dataset.sample.jsonl \
  --output logs/rag_eval_report.json \
  --use-llm-judge \
  --invalidate-before-each
```

说明：

- 数据集为 JSONL，每行一个样本，必填字段：`project_id`、`question`
- 推荐提供 `expected_chunk_ids`、`reference_answer`、`required_facts` 以获得完整评测
- `--invalidate-before-each` 可减少缓存对延迟与成功率统计的干扰

## 🐛 常见问题

**Q: 端口8000被占用？**
```bash
./stop.sh
```

**Q: Redis连接失败？**
不影响使用，系统会自动切换到内存缓存。

**Q: 数据库连接失败？**
不影响使用，当前MVP版本不依赖数据库。
